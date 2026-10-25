"""Check or train an isolated demand candidate on whole-hour chronological splits."""

from __future__ import annotations

import argparse
import copy
import json
import logging
from pathlib import Path

import mlflow
import pandas as pd

from scripts.responsible import run_analysis
from src.config import Config, get_config
from src.data.ingestion import load_zone_lookup
from src.models.train import train_problem

CANDIDATE_NAME = "taxi-demand-forecaster-strict-hourly"
KEYS = ["PULocationID", "pickup_hour"]


def validate_splits(parts: dict[str, pd.DataFrame]) -> dict:
    """Require matching schema and a complete, unique zone/hour grid in every period."""
    schema = None
    zones = None
    summary = {}
    for name in ("train", "val", "test"):
        frame = parts[name]
        if frame.empty or frame[KEYS].isna().any().any():
            raise ValueError(f"{name}: empty split or missing keys")
        if frame.duplicated(KEYS).any():
            raise ValueError(f"{name}: duplicate zone/hour keys")
        if not frame.pickup_hour.eq(frame.pickup_hour.dt.floor("h")).all():
            raise ValueError(f"{name}: timestamps must be aligned to the hour")
        if schema is not None and list(frame.columns) != schema:
            raise ValueError("Split feature schemas differ")
        schema = list(frame.columns)
        current_zones = set(frame.PULocationID)
        if zones is not None and current_zones != zones:
            raise ValueError("Zone coverage differs between periods")
        zones = current_zones
        hours = pd.DatetimeIndex(frame.pickup_hour.unique()).sort_values()
        expected = pd.date_range(hours.min(), hours.max(), freq="h")
        if not hours.equals(expected) or len(frame) != len(hours) * len(zones):
            raise ValueError(f"{name}: incomplete hourly grid")
        summary[name] = {
            "rows": len(frame), "hours": len(hours), "zones": len(zones),
            "start": str(hours.min()), "end": str(hours.max()),
        }
    for earlier, later in (("train", "val"), ("val", "test")):
        end = parts[earlier].pickup_hour.max()
        start = parts[later].pickup_hour.min()
        if end >= start:
            raise ValueError("Split periods overlap; strict timestamp separation failed")
        if start - end != pd.Timedelta(hours=1):
            raise ValueError("Split periods have an hourly gap")
    return summary


def candidate_config(config: Config, features_dir: Path, output: Path) -> Config:
    """Copy settings so canonical data, serving selectors and registry names stay isolated."""
    result = Config(copy.deepcopy(config.raw))
    result.raw.setdefault("data", {})["features_dir"] = str(features_dir.resolve())
    result.raw.setdefault("models", {}).update({
        "registry_demand": CANDIDATE_NAME,
        "artifacts_dir": str((output / "model_artifacts").resolve()),
    })
    result.raw.setdefault("mlflow", {})["experiment_demand"] = "taxi-demand-strict-hourly"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["check", "smoke", "train"], default="check")
    parser.add_argument("--features-dir", type=Path, default=Path("data/features/strict-hourly-v1"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--n-trials", type=int, help="Explicit budget required for train mode")
    parser.add_argument("--register", action="store_true", help="Only supported in train mode")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; choose a fresh directory")
    if args.register and args.mode != "train":
        parser.error("Registration requires --mode train")
    if args.mode == "train" and (args.n_trials is None or args.n_trials < 1):
        parser.error("Train mode requires a positive --n-trials budget")
    if args.mode != "train" and args.n_trials is not None:
        parser.error("Only train mode accepts --n-trials; smoke always uses 1")
    base = get_config()
    if args.features_dir.resolve() == base.features_dir.resolve():
        parser.error("Select a separate strict-split directory, not the canonical features directory")
    parts = {s: pd.read_parquet(args.features_dir / f"demand_{s}.parquet")
             for s in ("train", "val", "test")}
    periods = validate_splits(parts)
    config = candidate_config(base, args.features_dir, args.output)
    metadata = {
        "mode": args.mode, "candidate_registry_name": CANDIDATE_NAME,
        "split_periods": periods,
        "input_sha256": {f"demand_{s}.parquet": run_analysis.file_sha256(
            args.features_dir / f"demand_{s}.parquet") for s in parts},
        "feature_columns": [c for c in parts["train"].columns
                            if c not in {"pickup_hour", "PULocationID", "pickup_count"}],
        "seed": config.models.get("random_state", 42),
        "n_trials": 1 if args.mode == "smoke" else args.n_trials,
        "selection_metric": config.models.get("selection_metric", "rmse"),
        "evaluation_scope": "January diagnostic rolling one-step benchmark; not an untouched final test or fixed-origin backtest.",
    }
    args.output.mkdir(parents=True)
    (args.output / "preflight.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    if args.mode == "check":
        print("Preflight passed. No model trained or registered.")
        return
    trials = 1 if args.mode == "smoke" else args.n_trials
    summary = train_problem("demand", config, n_trials=trials, register=args.register)
    (args.output / "training_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.register:
        version = str(summary["registered"]["version"])
        config.raw.setdefault("serving", {})["model_stage"] = version
        run_analysis.CARDS_DIR = args.output / "responsible" / "model_cards"
        run_analysis.ARTIFACTS_DIR = args.output / "responsible" / "artifacts"
        run_analysis.analyse_problem("demand", config, load_zone_lookup(config.raw_dir / "taxi_zone_lookup.csv"))
        winner = next(r for r in summary["results"] if r["estimator"] == summary["best_estimator"])
        client = mlflow.MlflowClient()
        client.log_artifact(winner["run_id"], str(args.output / "preflight.json"), "strict-evaluation")
        client.log_artifact(winner["run_id"], str(args.output / "training_summary.json"), "strict-evaluation")
        client.log_artifacts(winner["run_id"], str(args.output / "responsible"), "strict-evaluation/responsible")
        print(f"Candidate: models:/{CANDIDATE_NAME}/{version}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
