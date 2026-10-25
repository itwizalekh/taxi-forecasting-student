"""Independently recompute assessment scores and replay one serving-style trajectory."""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.responsible.run_analysis import resolve_model
from src.config import Config, get_config
from src.serving.features import build_demand_row


def independent_scores(actual, prediction) -> dict:
    actual = np.asarray(actual, dtype=float)
    prediction = np.asarray(prediction, dtype=float)
    error = prediction - actual
    return {"rmse": float(np.sqrt(np.mean(error ** 2))), "mae": float(np.mean(np.abs(error)))}


def replay(model, history, zone, origin, config) -> pd.DataFrame:
    running = history.loc[(history.pickup_hour < origin) & (history.PULocationID == zone)].copy()
    records = []
    for step in range(24):
        target = origin + pd.Timedelta(hours=step)
        X = build_demand_row(running, zone, target, config)
        raw = float(model.predict(X)[0])
        clipped = max(0.0, raw)
        fed = int(round(clipped))
        records.append({"origin": origin, "pickup_hour": target, "horizon": step + 1,
            "PULocationID": zone, "raw_prediction": raw, "clipped_prediction": clipped,
            "prediction": round(clipped, 4), "history_count": fed,
            **{f"input_{c}": X[c].iloc[0] for c in X.columns}})
        running = pd.concat([running, pd.DataFrame({"PULocationID": [zone],
            "pickup_hour": [target], "pickup_count": [fed]})], ignore_index=True)
    return pd.DataFrame(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assessment", type=Path, required=True)
    parser.add_argument("--model", choices=["legacy", "candidate"], default="candidate")
    parser.add_argument("--zone", type=int, default=132)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output directory")
    protocol = json.loads((args.assessment / "protocol.json").read_text())
    paired = pd.read_csv(args.assessment / "paired_predictions.csv.gz")
    if paired.duplicated(["PULocationID", "pickup_hour"]).any():
        raise ValueError("Paired evaluation keys are not unique")
    stored = pd.read_csv(args.assessment / "common_metrics.csv").set_index("model")
    recomputed = []
    for label in ("legacy", "candidate"):
        metrics = independent_scores(paired.pickup_count, paired[f"{label}_prediction"])
        for metric, value in metrics.items():
            if not math.isclose(value, stored.loc[label, metric], rel_tol=1e-10, abs_tol=1e-10):
                raise ValueError(f"Paired aggregate mismatch: {label}/{metric}")
        recomputed.append({"model": label, "rows": len(paired), **metrics})
    backtest = pd.read_csv(args.assessment / "backtest_predictions.csv.gz",
                           parse_dates=["origin", "pickup_hour"])
    if backtest.duplicated(["model", "origin", "PULocationID", "horizon"]).any():
        raise ValueError("Duplicate backtest keys")
    stored_horizons = pd.read_csv(args.assessment / "horizon_metrics.csv").set_index(["model", "horizon"])
    recomputed_horizons = []
    for (label, horizon), group in backtest.groupby(["model", "horizon"]):
        metrics = independent_scores(group.pickup_count, group.prediction)
        for metric, value in metrics.items():
            if not math.isclose(value, stored_horizons.loc[(label, horizon), metric], rel_tol=1e-10, abs_tol=1e-10):
                raise ValueError(f"Horizon aggregate mismatch: {label}/{horizon}/{metric}")
        recomputed_horizons.append({"model": label, "horizon": horizon, "rows": len(group), **metrics})
    identity = protocol["models"][args.model]
    config = Config(copy.deepcopy(get_config().raw))
    config.raw.setdefault("models", {})["registry_demand"] = identity["registry_name"]
    config.raw.setdefault("serving", {})["model_stage"] = identity["registry_version"]
    model, resolved = resolve_model("demand", config)
    if resolved["run_id"] != identity["run_id"]:
        raise ValueError("Model identity changed")
    if args.zone not in protocol["zones"]:
        parser.error("Zone is outside the assessed population")
    origin = pd.Timestamp(protocol["origins"][0])
    history = pd.read_parquet(config.processed_dir / "demand_hourly.parquet")
    result = replay(model, history, args.zone, origin, config)
    changed = history.copy()
    changed.loc[changed.pickup_hour >= origin, "pickup_count"] += 10000
    perturbed = replay(model, changed, args.zone, origin, config)
    pd.testing.assert_frame_equal(result, perturbed, check_exact=True)
    expected = backtest.loc[(backtest.model == args.model) & (backtest.PULocationID == args.zone)
                            & (backtest.origin == origin)].sort_values("horizon")
    np.testing.assert_allclose(result.raw_prediction, expected.raw_prediction, rtol=1e-7, atol=1e-6)
    np.testing.assert_array_equal(result.prediction, expected.prediction)
    np.testing.assert_array_equal(result.input_lag_1.iloc[1:].to_numpy(), result.history_count.iloc[:-1].to_numpy())
    args.output.mkdir(parents=True)
    pd.DataFrame(recomputed).to_csv(args.output / "recomputed_common_metrics.csv", index=False)
    pd.DataFrame(recomputed_horizons).to_csv(args.output / "recomputed_horizon_metrics.csv", index=False)
    result.to_csv(args.output / "one_zone_feature_trace.csv", index=False, float_format="%.17g")
    print(pd.DataFrame(recomputed).to_string(index=False))
    print(f"PASS: all paired/horizon RMSE and MAE independently recomputed; {args.model}, zone {args.zone}, origin {origin} matches serving row replay at all 24 leads; future mutation invariant.")
    print(f"Manual-check evidence: {args.output}")


if __name__ == "__main__":
    main()
