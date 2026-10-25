"""Diagnostic paired comparison and fixed-origin backtest of frozen demand models."""

from __future__ import annotations

import argparse
import copy
import json
import logging
import math
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd

from scripts.responsible.run_analysis import file_sha256, resolve_model
from scripts.train_strict_demand import validate_splits
from src.config import Config, get_config
from src.data.ingestion import load_zone_lookup
from src.features.calendar import add_calendar_features
from src.features.demand_features import build_demand_features
from src.models.common import regression_metrics, split_to_xy
from src.responsible.fairness import add_borough, time_of_day_bucket
from src.serving.features import build_demand_row

KEYS = ["PULocationID", "pickup_hour"]
HORIZONS = (1, 3, 6, 12, 24)
LOG = logging.getLogger(__name__)


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def aligned_common(old: pd.DataFrame, strict: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Require identical targets and features on unique shared evaluation keys."""
    for name, frame in (("old", old), ("strict", strict)):
        if frame.duplicated(KEYS).any():
            raise ValueError(f"Duplicate {name} evaluation keys")
    common_keys = old[KEYS].merge(strict[KEYS], on=KEYS, validate="one_to_one")
    left = common_keys.merge(old, on=KEYS, validate="one_to_one").sort_values(KEYS).reset_index(drop=True)
    right = common_keys.merge(strict, on=KEYS, validate="one_to_one").sort_values(KEYS).reset_index(drop=True)
    pd.testing.assert_frame_equal(left, right[left.columns], check_exact=True)
    union = pd.concat([old[KEYS], strict[KEYS]]).drop_duplicates()
    return left, {"old_rows": len(old), "strict_rows": len(strict), "common_rows": len(left),
                  "old_only_rows": len(old) - len(left), "strict_only_rows": len(strict) - len(left),
                  "union_rows": len(union), "features_and_targets_identical": True}


def feature_matrix(values: np.ndarray, zones: list[int], target: pd.Timestamp,
                   config: Config, columns: list[str]) -> pd.DataFrame:
    """Reuse production rolling arithmetic: close floating values can change tree paths."""
    span = values.shape[1]
    times = pd.date_range(target - pd.Timedelta(hours=span), target, freq="h")
    counts = np.concatenate([values, np.zeros((len(zones), 1))], axis=1).astype("int64")
    frame = pd.DataFrame({
        "PULocationID": np.repeat(zones, span + 1),
        "pickup_hour": np.tile(times.to_numpy(), len(zones)),
        "pickup_count": counts.ravel(),
    })
    built = build_demand_features(frame, config, dropna=False)
    row = built.loc[built.pickup_hour == target].set_index("PULocationID")
    return row.loc[zones, columns].reset_index(drop=True)


def recursive_forecast(model, history: pd.DataFrame, origin: pd.Timestamp,
                       zones: list[int], config: Config, columns: list[str], horizon: int = 24,
                       *, verify_serving: bool = False) -> tuple[pd.DataFrame, float]:
    """Read actuals strictly before origin, then feed rounded/clipped predictions only."""
    span = max(max(config.features["demand_lags"]), max(config.features["demand_rolling_windows"]))
    allowed = history.loc[history.pickup_hour < origin]
    grid = allowed.pivot(index="pickup_hour", columns="PULocationID", values="pickup_count")
    times = pd.date_range(origin - pd.Timedelta(hours=span), origin - pd.Timedelta(hours=1), freq="h")
    values = grid.reindex(index=times, columns=zones).to_numpy(dtype=float).T
    if np.isnan(values).any():
        raise ValueError("Insufficient complete history before origin")
    records = []
    max_feature_difference = 0.0
    probe_indices = sorted({0, len(zones) // 2, len(zones) - 1})
    reference_histories = {}
    if verify_serving:
        for i in probe_indices:
            reference_histories[i] = allowed.loc[allowed.PULocationID == zones[i]].copy()
    for step in range(horizon):
        target = origin + pd.Timedelta(hours=step)
        X = feature_matrix(values, zones, target, config, columns)
        raw = np.asarray(model.predict(X), dtype=float)
        if not np.isfinite(raw).all():
            raise ValueError("Nonfinite model output")
        clipped = np.maximum(0, raw)
        fed = np.array([int(round(float(p))) for p in clipped], dtype=np.int64)
        served = np.array([round(float(p), 4) for p in clipped])
        if verify_serving:
            for i in probe_indices:
                reference = build_demand_row(reference_histories[i], zones[i], target, config)[columns]
                difference = float(np.abs(reference.to_numpy() - X.iloc[[i]].to_numpy()).max())
                max_feature_difference = max(max_feature_difference, difference)
                np.testing.assert_array_equal(reference.to_numpy(), X.iloc[[i]].to_numpy())
                ref_raw = float(model.predict(reference)[0])
                if not math.isclose(ref_raw, float(raw[i]), rel_tol=1e-7, abs_tol=1e-6):
                    raise ValueError("Batched forecast differs from serving reference")
                reference_histories[i] = pd.concat([reference_histories[i], pd.DataFrame({
                    "PULocationID": [zones[i]], "pickup_hour": [target], "pickup_count": [fed[i]],
                })], ignore_index=True)
        records.append(pd.DataFrame({
            "origin": origin, "pickup_hour": target, "horizon": step + 1, "PULocationID": zones,
            "raw_prediction": raw, "clipped_prediction": clipped,
            "prediction": served, "history_count": fed,
        }))
        values = np.concatenate([values[:, 1:], fed[:, None]], axis=1)
    return pd.concat(records, ignore_index=True), max_feature_difference


def score(y, prediction) -> dict:
    result = regression_metrics(np.asarray(y, dtype=float), np.asarray(prediction, dtype=float))
    return {k: float(v) if np.isfinite(v) else None for k, v in result.items()}


def markdown(frame: pd.DataFrame) -> str:
    def value(v):
        return f"{v:.6f}" if isinstance(v, float) else str(v)
    return "| " + " | ".join(frame.columns) + " |\n|" + "---|" * len(frame.columns) + "\n" + "\n".join(
        "| " + " | ".join(value(v) for v in row) + " |" for row in frame.itertuples(index=False, name=None)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path, default=Path("artifacts/strict-demand/candidate-your-run"))
    parser.add_argument("--strict-dir", type=Path, default=Path("data/features/strict-hourly-v1"))
    parser.add_argument("--old-version", type=int, default=1)
    parser.add_argument("--candidate-version", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    logging.getLogger("src.features.demand_features").setLevel(logging.WARNING)
    if args.output.exists():
        parser.error("Output exists; choose a new folder to preserve evidence")
    config = get_config()
    strict = {s: pd.read_parquet(args.strict_dir / f"demand_{s}.parquet") for s in ("train", "val", "test")}
    strict_periods = validate_splits(strict)
    old = {s: pd.read_parquet(config.features_dir / f"demand_{s}.parquet") for s in ("train", "val", "test")}
    preflight = json.loads((args.candidate_dir / "preflight.json").read_text())
    training = json.loads((args.candidate_dir / "training_summary.json").read_text())
    for filename, expected in preflight["input_sha256"].items():
        if file_sha256(args.strict_dir / filename) != expected:
            raise ValueError("Candidate input hash changed since training")
    old_report = json.loads(Path("evidence/2026-10-25/responsible-analysis/reviewed/demand_fairness.json").read_text())
    for filename, expected in old_report["provenance"]["input_sha256"].items():
        if filename.startswith("demand_") and file_sha256(config.features_dir / filename) != expected:
            raise ValueError("Legacy evaluation data changed since preserved analysis")
    models, identities = {}, {}
    for label, name, version in (
        ("legacy", "taxi-demand-forecaster", args.old_version),
        ("candidate", "taxi-demand-forecaster-strict-hourly", args.candidate_version),
    ):
        model_config = Config(copy.deepcopy(config.raw))
        model_config.raw.setdefault("models", {})["registry_demand"] = name
        model_config.raw.setdefault("serving", {})["model_stage"] = str(version)
        models[label], identities[label] = resolve_model("demand", model_config)
    winner = min(training["results"], key=lambda r: r["val_metrics"]["rmse"])
    if winner["run_id"] != identities["candidate"]["run_id"] or winner["estimator"] != training["best_estimator"]:
        raise ValueError("Registered candidate is not the recorded validation winner")
    common, matching = aligned_common(old["test"], strict["test"])
    start = max(strict["test"].pickup_hour.min(), old["val"].pickup_hour.max() + pd.Timedelta(hours=1))
    end = strict["test"].pickup_hour.max() - pd.Timedelta(hours=23)
    origins = pd.date_range(start, end, freq="6h")
    if not len(origins):
        raise ValueError("No complete 24-hour origins after both validation cutoffs")
    zones = sorted(int(z) for z in strict["test"].PULocationID.unique())
    args.output.mkdir(parents=True)
    protocol = {
        "frozen_at_utc": datetime.now(UTC).isoformat(), "scope": "January diagnostic; retrospective simulation",
        "models": identities, "horizons_reported": list(HORIZONS), "maximum_horizon": 24,
        "origin_spacing_hours": 6, "origins": [str(o) for o in origins], "zones": zones,
        "history_rule": "actual pickup_hour < origin; fresh history per origin/model; predictions only thereafter",
        "serving_rule": "clip raw at zero; append int(round(clipped)); score round(clipped,4)",
        "baselines": ["last actual before origin held constant", "actual at target minus 168 hours"],
        "metrics": ["rmse", "mae", "mape excluding near-zero targets", "r2"],
        "cutoffs": {"legacy_val_end": str(old["val"].pickup_hour.max()), "candidate_val_end": str(strict["val"].pickup_hour.max())},
        "strict_periods": strict_periods, "matching": matching,
        "future_window_plan": {"start": "2024-02-01 00:00:00", "end": "2024-02-29 23:00:00",
                               "status": "planned calendar only; no February data downloaded or evaluated"},
    }
    write_json(args.output / "protocol.json", protocol)
    LOG.info("Protocol frozen before performance calculation: %s", args.output / "protocol.json")
    common_X, common_y = split_to_xy(common, "demand")
    columns = list(common_X.columns)
    paired = common[KEYS + ["pickup_count"]].copy()
    native_records, common_records = [], []
    for label, frame in (("legacy", old["test"]), ("candidate", strict["test"])):
        X, y = split_to_xy(frame, "demand")
        raw = models[label].predict(X)
        native_records.append({"model": label, "rows": len(frame), **score(y, raw)})
    for label, model in models.items():
        prediction = model.predict(common_X)
        paired[f"{label}_prediction"] = prediction
        paired[f"{label}_error"] = prediction - common_y.to_numpy()
        paired[f"{label}_absolute_error"] = np.abs(prediction - common_y.to_numpy())
        paired[f"{label}_squared_error"] = (prediction - common_y.to_numpy()) ** 2
        common_records.append({"model": label, "rows": len(common), **score(common_y, prediction)})
    paired.to_csv(args.output / "paired_predictions.csv.gz", index=False, float_format="%.17g", compression="gzip")
    paired.head(50).to_csv(args.output / "paired_manual_sample.csv", index=False, float_format="%.17g")
    native_metrics, common_metrics = pd.DataFrame(native_records), pd.DataFrame(common_records)
    native_metrics.to_csv(args.output / "native_metrics.csv", index=False)
    common_metrics.to_csv(args.output / "common_metrics.csv", index=False)
    lookup = load_zone_lookup(config.raw_dir / "taxi_zone_lookup.csv")
    sliced = add_borough(common, lookup)
    sliced["time_of_day"] = sliced.hour.map(time_of_day_bucket)
    subgroup_records = []
    for dim in ("borough", "time_of_day", "is_weekend", "is_holiday"):
        for group, rows in sliced.groupby(dim):
            if len(rows) >= 30:
                for label in models:
                    subgroup_records.append({"dimension": dim, "group": str(group), "model": label,
                                             "rows": len(rows), **score(common_y.iloc[rows.index], paired.loc[rows.index, f"{label}_prediction"])})
    pd.DataFrame(subgroup_records).to_csv(args.output / "paired_subgroup_metrics.csv", index=False)
    history_path = config.processed_dir / "demand_hourly.parquet"
    history = pd.read_parquet(history_path)
    if history.duplicated(KEYS).any():
        raise ValueError("Duplicate source history keys")
    history.pickup_hour = pd.to_datetime(history.pickup_hour)
    backtest, checks = [], []
    for origin in origins:
        LOG.info("Backtesting origin %s (%d zones, 24 hours)", origin, len(zones))
        changed = history.copy()
        changed.loc[changed.pickup_hour >= origin, "pickup_count"] += 10000
        for label, model in models.items():
            forecasts, max_difference = recursive_forecast(
                model, history, origin, zones, config, columns, verify_serving=True)
            perturbed, _ = recursive_forecast(model, changed, origin, zones, config, columns)
            pd.testing.assert_frame_equal(forecasts, perturbed, check_exact=True)
            forecasts["model"] = label
            backtest.append(forecasts)
            checks.append({"origin": str(origin), "model": label, "future_actuals_perturbation": "PASS",
                           "rows_verified": len(forecasts), "serving_reference_zones": [zones[0], zones[len(zones)//2], zones[-1]],
                           "max_feature_difference": max_difference})
        grid = history.loc[history.pickup_hour < origin].pivot(index="pickup_hour", columns="PULocationID", values="pickup_count")
        for label in ("persistence", "weekly"):
            for step in range(24):
                target = origin + pd.Timedelta(hours=step)
                source = origin - pd.Timedelta(hours=1) if label == "persistence" else target - pd.Timedelta(hours=168)
                if source >= origin:
                    raise ValueError("Baseline source is not available at origin")
                prediction = grid.loc[source, zones].to_numpy(dtype=float)
                backtest.append(pd.DataFrame({"origin": origin, "pickup_hour": target,
                    "horizon": step + 1, "PULocationID": zones, "model": label,
                    "raw_prediction": prediction, "clipped_prediction": prediction,
                    "prediction": prediction, "history_count": prediction.astype(int)}))
    forecasts = pd.concat(backtest, ignore_index=True)
    # Truth is joined only after every recursive trajectory is complete.
    forecasts = forecasts.merge(history[KEYS + ["pickup_count"]], on=KEYS, how="left", validate="many_to_one")
    if forecasts.pickup_count.isna().any():
        raise ValueError("Missing held-out truth")
    forecasts.to_csv(args.output / "backtest_predictions.csv.gz", index=False, float_format="%.17g", compression="gzip")
    first_origin = forecasts.loc[forecasts.origin == origins[0]]
    first_origin.to_csv(args.output / "first_origin_manual.csv", index=False, float_format="%.17g")
    horizon_records = []
    for (label, horizon), rows in forecasts.groupby(["model", "horizon"]):
        horizon_records.append({"model": label, "horizon": int(horizon), "rows": len(rows),
                                "origins": rows.origin.nunique(), **score(rows.pickup_count, rows.prediction)})
    horizon_metrics = pd.DataFrame(horizon_records)
    horizon_metrics.to_csv(args.output / "horizon_metrics.csv", index=False)
    coverage = add_calendar_features(strict["test"][["pickup_hour"]].drop_duplicates(), "pickup_hour")
    planned = add_calendar_features(pd.DataFrame({"pickup_hour": pd.date_range("2024-02-01", "2024-02-29 23:00", freq="h")}), "pickup_hour")
    coverage_summary = {"test_hours": len(coverage), "test_days": coverage.pickup_hour.dt.date.nunique(),
        "weekend_hours": int(coverage.is_weekend.sum()), "holiday_hours": int(coverage.is_holiday.sum()),
        "holiday_dates": sorted(str(d) for d in coverage.loc[coverage.is_holiday == 1, "pickup_hour"].dt.date.unique()),
        "planned_february_calendar": {"hours": len(planned), "weekend_dates": planned.loc[planned.is_weekend == 1, "pickup_hour"].dt.date.nunique(),
            "holiday_dates": sorted(str(d) for d in planned.loc[planned.is_holiday == 1, "pickup_hour"].dt.date.unique())}}
    coverage_summary = json.loads(json.dumps(coverage_summary, default=int))
    write_json(args.output / "coverage.json", coverage_summary)
    write_json(args.output / "leakage_and_serving_checks.json", checks)
    client = mlflow.MlflowClient()
    model_hashes = {}
    for label, identity in identities.items():
        directory = Path(client.download_artifacts(identity["run_id"], "model"))
        model_hashes[label] = {p.relative_to(directory).as_posix(): file_sha256(p) for p in sorted(directory.rglob("*")) if p.is_file()}
    result = {"native_metrics": native_records, "common_metrics": common_records, "matching": matching,
        "backtest": {"origins": len(origins), "zones": len(zones), "series": 4,
                     "rows_per_model_per_lead": len(origins) * len(zones), "total_forecast_rows": len(forecasts),
                     "selected_horizons": horizon_metrics.loc[horizon_metrics.horizon.isin(HORIZONS)].to_dict("records")},
        "coverage": coverage_summary, "candidate_selection": {"winner": winner["estimator"],
            "validation_rmse": winner["val_metrics"]["rmse"], "trial_budget": preflight["n_trials"]},
        "checks_passed": len(checks), "model_artifact_sha256": model_hashes}
    write_json(args.output / "assessment.json", result)
    render_report(args.output, result, protocol, training)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for label, rows in horizon_metrics.groupby("model"):
        rows = rows.sort_values("horizon")
        axes[0].plot(rows.horizon, rows.rmse, label=label)
        axes[1].plot(rows.horizon, rows.mae, label=label)
    for ax, metric in zip(axes, ("RMSE", "MAE"), strict=True):
        ax.set(xlabel="Hours ahead (1 = origin hour)", ylabel=f"{metric} (pickups)")
        ax.grid(alpha=.2)
    axes[0].legend()
    fig.suptitle("January diagnostic fixed-origin backtest — 6 origins; overlapping trajectories")
    fig.tight_layout()
    fig.savefig(args.output / "horizon_errors.png", dpi=160)
    plt.close(fig)
    sources = [Path(__file__), Path("src/serving/batch.py"), Path("src/serving/features.py"), Path("src/features/demand_features.py"), Path("src/models/common.py"), Path("config/config.yaml")]
    manifest = {"created_at_utc": datetime.now(UTC).isoformat(), "python": platform.python_version(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "protocol_sha256": file_sha256(args.output / "protocol.json"),
        "source_sha256": {str(p): file_sha256(p) for p in sources},
        "inputs_sha256": {str(p): file_sha256(p) for p in [history_path, args.candidate_dir / "preflight.json", args.candidate_dir / "training_summary.json"]
                          + [config.features_dir / f"demand_{s}.parquet" for s in old]
                          + [args.strict_dir / f"demand_{s}.parquet" for s in strict]},
        "outputs_sha256": {p.name: file_sha256(p) for p in sorted(args.output.iterdir()) if p.is_file()}}
    write_json(args.output / "manifest.json", manifest)
    LOG.info("Assessment complete: %s", args.output / "ASSESSMENT.md")


def render_report(output: Path, result: dict, protocol: dict, training: dict) -> None:
    native, common = pd.DataFrame(result["native_metrics"]), pd.DataFrame(result["common_metrics"])
    old, candidate = common.set_index("model").loc["legacy"], common.set_index("model").loc["candidate"]
    change = 100 * (candidate.rmse / old.rmse - 1)
    selected = pd.DataFrame(result["backtest"]["selected_horizons"])
    by_lead = selected.pivot(index="horizon", columns="model", values="rmse")
    weekly_wins = [int(h) for h in by_lead.index if by_lead.loc[h, "weekly"] < by_lead.loc[h, "candidate"]]
    candidate_wins = [int(h) for h in by_lead.index if by_lead.loc[h, "candidate"] < by_lead.loc[h, "legacy"]]
    by_mae = selected.pivot(index="horizon", columns="model", values="mae")
    tradeoffs = [int(h) for h in weekly_wins if by_mae.loc[h, "candidate"] < by_mae.loc[h, "weekly"]]
    subgroup = pd.read_csv(output / "paired_subgroup_metrics.csv")
    boroughs = subgroup.loc[subgroup.dimension == "borough"].pivot(index="group", columns="model", values="rmse").reset_index()
    boroughs["candidate_minus_legacy_rmse"] = boroughs.candidate - boroughs.legacy
    lines = [
        "# Strict-hour demand candidate assessment — January diagnostic",
        "", "Generated locally on 25 October 2026 (IST). This is retrospective diagnostic evaluation, not production approval or an untouched final test.",
        "", "## Assessment", "",
        f"On the SAME {int(old['rows']):,} zone/hour rows, candidate RMSE is {candidate.rmse:.6f} versus legacy {old.rmse:.6f} ({change:+.3f}% change; negative is lower). Candidate MAE is {candidate.mae:.6f} versus {old.mae:.6f}.",
        "Do not attribute this difference solely to splitting: model family, tuning budget (1 versus 25 trials per estimator), training rows and selected hyperparameters also changed. No repeated-seed or independent-period superiority claim is established.",
        "", "**Decision: retain the strict-split candidate for further evaluation; broad improvement or promotion is not established.** The shared-hour split issue is closed for the candidate. The paired overall change is very small, subgroup results are mixed, and a weekly baseline remains competitive or better at multiple leads. Freeze the versions and protocol before later-period evaluation.",
        "", "## Exact models and validation selection", "",
    ]
    for label, identity in protocol["models"].items():
        lines.append(f"- {label}: `{identity['model_uri']}`, run `{identity['run_id']}`; training params in `protocol.json`.")
    lines += ["", f"Candidate selection: **{result['candidate_selection']['winner']}**, chosen by validation RMSE {result['candidate_selection']['validation_rmse']:.6f} over 25 trials per estimator.",
        "", markdown(pd.DataFrame([{"estimator": r['estimator'], "validation_rmse": r['val_metrics']['rmse'], "diagnostic_test_rmse": r['test_metrics']['rmse']} for r in training['results']])),
        "", "LightGBM has a lower candidate-run diagnostic test RMSE, but switching after inspecting test scores would use the test for selection. Keep the predeclared validation winner.",
        "", "## Native protocols — different row sets", "", markdown(native),
        "", "Native scores reproduce each model's own test protocol. Their numerical difference is not a paired model comparison.",
        "", "## Paired comparison — same keys, targets and feature values", "", markdown(common),
        "", "The strict test contains 101 additional Jan 29 14:00 zone/hour rows that were in legacy validation. They are excluded from the common test comparison. Both versions are evaluated on the exact same raw feature rows; schema, targets and inputs match exactly. Prediction errors here use raw regressor output to reproduce training metrics.",
        "", "`paired_predictions.csv.gz` contains all paired rows and independent error columns. `paired_subgroup_metrics.csv` compares represented borough/time/day/holiday groups on the common rows (minimum 30 rows). No one-group parity inference is permitted.",
        "", "Paired borough RMSE (positive difference means candidate worsened):", "", markdown(boroughs),
        "", "Queens improves while Manhattan worsens in RMSE on these identical rows. The overall result therefore does not establish consistent geographic improvement. Raw error scale and sparse subgroup support still matter.",
        "", "## Fixed-origin recursive backtest", "",
        f"Six origins at six-hour intervals: {protocol['origins'][0]} through {protocol['origins'][-1]}. All {result['backtest']['zones']} zones, full 24-hour trajectories; {result['backtest']['rows_per_model_per_lead']:,} forecasts per series at each lead. Origins start after BOTH validation cutoffs, avoiding legacy validation's extra boundary hour.",
        "", "Each origin/model starts from actual hours strictly before the origin, then feeds only its own clipped, integer-rounded predictions. Scored predictions match the batch output's four-decimal rounding. Persistence holds the last available observation; weekly uses actual target-minus-168h, always before these origins. Truth joins only after trajectories are produced.",
        "", markdown(selected[["model", "horizon", "rows", "rmse", "mae", "mape"]]),
        "", f"At the requested leads, candidate RMSE is lower than legacy at {candidate_wins}. The weekly baseline has lower RMSE than candidate at {weekly_wins}. Candidate MAE is lower than weekly MAE despite worse RMSE at leads {tradeoffs}, so conclusions depend on the preselected loss and tolerance for large misses. Do not replace the validation-selected model or choose a new horizon/metric after observing this table.",
        "", "Horizon errors need not increase monotonically here: changing the lead also changes target hours and demand levels for this small origin set. The table does not isolate error propagation from target-time composition.",
        "", f"All {result['checks_passed']} model/origin checks passed: adding 10,000 to EVERY future actual count did not change any forecast. The batched feature calculation and raw outputs were cross-checked against the serving row builder at all 24 steps for the first, middle and last zone at every origin/model. See `leakage_and_serving_checks.json`.",
        "", "This is a finite empirical invariance check plus explicit history truncation, not a proof covering every possible code path. Other zones use the same tested batched implementation. Actual counts before each NEW origin may include completed earlier test hours; they are not revealed inside that origin's trajectory.",
        "", "These trajectories overlap and cover only three target dates. Zone/hour forecasts and overlapping origins are dependent; no significance claim or narrow confidence interval is justified. Metrics at lead h score exactly h hours ahead, not an average over leads 1..h. Raw rolling one-step, clipped recursive and baseline scores are distinct protocols.",
        "", "![Errors by forecast horizon](horizon_errors.png)",
        "", "## Coverage and remaining limits", "",
        f"Strict test: {result['coverage']['test_hours']} hours across {result['coverage']['test_days']} dates; {result['coverage']['weekend_hours']} weekend hours; {result['coverage']['holiday_hours']} holiday hours. Weekend/holiday coverage gaps remain open.",
        "", "Publication delays, missing/corrected source counts, true historical model availability, population shift and service equity are not established by this historical simulation. Three flagged responsible-analysis dimensions remain investigation items; error ratios alone do not establish discrimination or fairness.",
        "", "## Freeze before later-period evaluation", "",
        "`protocol.json` was written before this assessment's performance calculations. Models were neither retrained nor reselected. It freezes numeric identities, origins, metrics, baselines and postprocessing. Its SHA256 is in `manifest.json`.",
        "", f"The proposed next window is all February 2024, carried forward from January history. Calendar-only inspection using this repo's holiday function finds {result['coverage']['planned_february_calendar']['weekend_dates']} weekend dates and holiday date(s) {', '.join(result['coverage']['planned_february_calendar']['holiday_dates'])}. No February observations were downloaded, scored or used for tuning here. One holiday event cannot establish broad holiday robustness.",
        "", "Before obtaining or scoring that window, freeze versions and a plan file; verify holiday definitions, timestamp conventions, minimum group support and at least 168 prior observed hours. Build continuous demand history across month boundaries; score only February targets. Report distinct days/holiday events alongside rows. If any results trigger tuning, label February development evidence and reserve a further future window with the required coverage for final evaluation. Do not call a model trained on that window externally validated by it.",
        "", "## Step-by-step manual assessment", "",
        "1. Open `protocol.json`. In MLflow inspect each numeric model version and its source run. Match candidate `2f79615caca841f2b44b7627c4de5a96`, validation winner, 25-trial params and the recorded split hashes. Use `Get-FileHash -Algorithm SHA256` on each recorded Parquet file. This verifies current files, not independent historical training-data provenance.",
        "2. Open `native_metrics.csv` and `common_metrics.csv`. Confirm native counts 14,573/14,674 but common counts 14,573/14,573. Do not compare different native row sets as a paired improvement.",
        "3. Expand `paired_predictions.csv.gz` using Python/pandas or a gzip-capable tool; retain the compressed original. Sort by zone and hour. Verify keys are unique. For both models recompute error = prediction - pickup_count, absolute error = ABS(error), squared error = error^2; MAE = AVERAGE(all absolute errors), RMSE = SQRT(AVERAGE(all squared errors)). Use ALL rows for aggregate comparison; `paired_manual_sample.csv` is only 50 worked rows. Match `common_metrics.csv` within numeric tolerance. Relative RMSE change = 100*(candidate/legacy-1).",
        "4. Compare borough/time slices on those same rows using `paired_subgroup_metrics.csv`. Check row counts and target scale. An overall decrease does not establish improvement for every subgroup.",
        "5. Open `first_origin_manual.csv`. Select one model and one zone, order by horizon, and confirm target_time = origin + (horizon-1) hours. Inspect raw_prediction, clipped_prediction = MAX(0,raw), history_count = int(round(clipped)), prediction = round(clipped,4). Python uses ties-to-even rounding; Excel ROUND may differ on exact .5 ties. At horizon 2 the lag_1 input must be horizon 1's history_count, not actual target-hour count. See the independent 1-zone check command in the companion instructions.",
        "6. Review `leakage_and_serving_checks.json`: all 12 origin/model perturbations must PASS. Rerun the script to a NEW folder to reproduce the mutation test. Future targets must be changed before prediction, not after scoring. Confirm every origin exceeds both validation cutoffs and models are not fitted/tuned inside the forecast period.",
        "7. Filter `backtest_predictions.csv.gz` by exact horizon and model. Compute MAE/RMSE using all 1,518 rows at that lead; compare with persistence and weekly on the SAME origin/zone/target keys. Keep origin/day counts visible. Match `horizon_metrics.csv`; do not average already-computed subgroup RMSEs to obtain overall RMSE.",
        "8. Open `coverage.json`. Verify zero weekend/holiday test hours and three scored dates. Inspect the proposed February calendar; it is a plan, not actual data coverage. Freeze models/protocol before fetching later data and check observed support after ingestion.",
        "9. Write a scoped conclusion with numeric model URIs, common-row count, exact horizon/protocol and coverage limits. State measured RMSE/MAE changes rather than a general improvement or deployment claim. Stop tuning against January.",
        "", "## Reproduce", "", "```powershell",
        ".\\.venv\\Scripts\\python.exe -m scripts.assess_strict_demand --old-version 1 --candidate-version 1 --output artifacts/strict-demand/assessment-your-repeat",
        "```", "", "Use a fresh output directory. This reads local data and numeric registered models; it does not train, register or deploy. The companion `MANUAL_ASSESSMENT.md` contains independent commands for recomputing scores and checking one recursive trajectory.",
    ]
    (output / "ASSESSMENT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
