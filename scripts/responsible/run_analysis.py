"""Generate the responsible-AI artifacts.

For each problem (demand, fare) this:

1. loads the registered model and the held-out **test** split;
2. computes overall regression metrics;
3. slices performance by **borough**, **time-of-day**, **weekend/holiday** and
   **airport** zones, flagging any subgroup disparity;
4. computes SHAP global feature importance (+ a summary plot); and
5. writes a Markdown **model card** (docs/model_cards/) plus a fairness JSON and
   SHAP plot (artifacts/responsible/, gitignored).

Run locally after training::

    python -m scripts.responsible.run_analysis
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import mlflow
import pandas as pd

from src.config import Config, get_config
from src.data.ingestion import load_zone_lookup
from src.models.common import PROBLEMS, registry_model_name, split_to_xy
from src.responsible import fairness
from src.responsible.explain import global_importance, save_summary_plot
from src.responsible.model_card import render_model_card
from src.serving import registry
from src.utils.mlflow_utils import configure_mlflow

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("responsible-analysis")

SHAP_SAMPLE = 2000
CARDS_DIR = Path("docs/model_cards")
ARTIFACTS_DIR = Path("artifacts/responsible")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_model(problem: str, config: Config):
    """Resolve mutable registry selectors once, then load the numeric version."""
    configure_mlflow(config)
    name = registry_model_name(problem, config)
    selector = str(config.serving.get("model_stage", "latest"))
    client = mlflow.MlflowClient()
    if selector.isdigit():
        selected = client.get_model_version(name, selector)
    else:
        versions = client.search_model_versions(f"name='{name}'")
        if selector.lower() != "latest":
            versions = [v for v in versions if v.current_stage.lower() == selector.lower()]
        if not versions:
            raise ValueError(f"No registered model matches {name}/{selector}")
        selected = max(versions, key=lambda v: int(v.version))
    pinned = Config(copy.deepcopy(config.raw))
    pinned.raw.setdefault("serving", {})["model_stage"] = str(selected.version)
    model = registry.load_model(problem, pinned)
    run = client.get_run(selected.run_id)
    return model, {
        "registry_name": name,
        "requested_selector": selector,
        "registry_version": str(selected.version),
        "model_uri": f"models:/{name}/{selected.version}",
        "run_id": selected.run_id,
        "training_params": dict(run.data.params),
    }


def _load_test_frame(config: Config, problem: str) -> pd.DataFrame:
    prefix = PROBLEMS[problem]["file_prefix"]
    path = config.features_dir / f"{prefix}_test.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Missing test split: {path}. Run the pipeline first.")
    return pd.read_parquet(path)


def _build_slices(df: pd.DataFrame, zone_lookup: pd.DataFrame) -> pd.DataFrame:
    """Attach the subgroup label columns used for fairness slicing."""
    slices = fairness.add_borough(df, zone_lookup, location_col="PULocationID")
    slices["time_of_day"] = slices["hour"].apply(fairness.time_of_day_bucket)
    slices["day_type"] = slices["is_weekend"].map({1: "weekend", 0: "weekday"})
    slices["holiday"] = slices["is_holiday"].map({1: "holiday", 0: "non-holiday"})
    slices["airport"] = (slices["service_zone"] == "Airports").map(
        {True: "airport", False: "non-airport"}
    )
    return slices


def analyse_problem(problem: str, config: Config, zone_lookup: pd.DataFrame) -> dict:
    logger.info("Analysing %s", problem)
    model, provenance = resolve_model(problem, config)
    df = _load_test_frame(config, problem)
    X, y = split_to_xy(df, problem)
    y_pred = model.predict(X)

    from src.models.common import regression_metrics

    metrics = regression_metrics(y.to_numpy(), y_pred)
    prefix = PROBLEMS[problem]["file_prefix"]
    time_col = "pickup_hour" if problem == "demand" else "tpep_pickup_datetime"
    split_frames = {
        split: pd.read_parquet(config.features_dir / f"{prefix}_{split}.parquet", columns=[time_col])
        for split in ("train", "val", "test")
    }
    periods = {
        split: {"rows": len(frame), "start": str(frame[time_col].min()),
                "end": str(frame[time_col].max())}
        for split, frame in split_frames.items()
    }
    strict = all(
        split_frames[a][time_col].max() < split_frames[b][time_col].min()
        for a, b in (("train", "val"), ("val", "test"))
    )
    notes = [
        f"Configured data period: {config.data.get('tlc_year')}-{int(config.data.get('tlc_month')):02d}.",
        f"Test period: {periods['test']['start']} to {periods['test']['end']}; "
        f"{len(df):,} rows. Stored timestamps are used without timezone conversion.",
        f"Strict timestamp separation across train/validation/test: {strict}.",
        "SHA256 hashes of evaluated splits and the zone lookup are recorded in the fairness JSON; "
        "these identify current evaluation inputs, not proof of original training-data identity.",
        f"Training trials per estimator recorded by MLflow: {provenance['training_params'].get('n_trials', 'unknown')}.",
        "SHAP uses up to 2,000 test rows, sampled with random_state=42; it is explanatory, not causal.",
        "Raw RMSE disparity depends on target scale and sample coverage; flags warrant investigation, "
        "not a demographic-discrimination conclusion. Groups smaller than 30 rows are omitted. "
        "MAPE excludes near-zero targets and can be large for small nonzero targets.",
    ]
    if problem == "demand":
        notes += [
            "Demand evaluation uses historical lag features and supports a rolling one-step interpretation; "
            "later test rows use earlier actual counts. Fixed-origin multi-hour accuracy is not established.",
            ("The registered model is evaluated on configured splits with strictly separated timestamps; "
             "this does not establish fixed-origin multi-hour accuracy."
             if strict else
             "The registered model is evaluated on configured splits with shared boundary timestamps; "
             "the separate strict-hour audit does not alter this run. Strict-split retraining is required."),
        ]
    provenance.update({
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "split_periods": periods,
        "strict_timestamp_separation": strict,
        "input_sha256": {
            f"{prefix}_{split}.parquet": file_sha256(config.features_dir / f"{prefix}_{split}.parquet")
            for split in ("train", "val", "test")
        },
    })
    provenance["input_sha256"]["taxi_zone_lookup.csv"] = file_sha256(config.raw_dir / "taxi_zone_lookup.csv")

    slices = _build_slices(df, zone_lookup)
    dimensions = ["borough", "time_of_day", "day_type", "holiday", "airport"]
    reports = [
        fairness.subgroup_metrics(slices, y.to_numpy(), y_pred, dim) for dim in dimensions
    ]

    # SHAP on a bounded sample for speed.
    sample = X.sample(min(SHAP_SAMPLE, len(X)), random_state=42)
    importance = global_importance(model, sample)
    top_features = list(importance.head(10).itertuples(index=False, name=None))

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        save_summary_plot(model, sample, ARTIFACTS_DIR / f"{problem}_shap_summary.png")
    except Exception as exc:  # pragma: no cover - plotting is best-effort
        logger.warning("SHAP summary plot skipped for %s: %s", problem, exc)

    fairness_json = {
        "problem": problem,
        "metrics": metrics,
        "provenance": provenance,
        "evaluation_notes": notes,
        "dimensions": [r.to_dict() for r in reports],
    }
    (ARTIFACTS_DIR / f"{problem}_fairness.json").write_text(
        json.dumps(fairness_json, indent=2), encoding="utf-8"
    )

    card = render_model_card(
        name=registry_model_name(problem, config),
        problem=problem,
        algorithm=type(model).__name__,
        target=PROBLEMS[problem]["target"],
        metrics=metrics,
        fairness=reports,
        top_features=top_features,
        version=provenance["registry_version"],
        run_id=provenance["run_id"],
        model_reference=provenance["model_uri"],
        evaluation_notes=notes,
        intended_use=("Historical hourly pickup-count forecasting for fleet-planning research."
                      if problem == "demand" else
                      "Historical trip fare_amount estimation; excludes the full passenger bill. "
                      "Observed trip distance and duration do not establish pre-trip accuracy."),
    )
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    (CARDS_DIR / f"{problem}.md").write_text(card, encoding="utf-8")
    logger.info(
        "%s: wrote model card + fairness JSON (%d flagged dimensions)",
        problem,
        sum(r.flagged for r in reports),
    )
    return fairness_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate responsible-AI artifacts.")
    parser.add_argument("--problem", choices=list(PROBLEMS), default=None, help="Limit to one problem.")
    args = parser.parse_args(argv)

    config = get_config()
    zone_lookup = load_zone_lookup(config.raw_dir / "taxi_zone_lookup.csv")

    problems = [args.problem] if args.problem else list(PROBLEMS)
    for problem in problems:
        analyse_problem(problem, config, zone_lookup)
    logger.info("Responsible-AI analysis complete. Cards in %s", CARDS_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
