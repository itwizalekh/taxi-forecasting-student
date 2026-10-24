"""Audit actual demand boundaries and features; export opt-in whole-hour splits.

Run: python -m scripts.audit_demand_time --output evidence/2026-10-24/demand-time-audit
Outputs must be new directories. Existing canonical splits are never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import get_config
from src.data.splits import timestamp_group_split
from src.features.demand_features import build_demand_features, feature_columns

TIME, ZONE, TARGET = "pickup_hour", "PULocationID", "pickup_count"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(parts: dict[str, pd.DataFrame]) -> dict:
    return {name: {"rows": len(df), "hours": df[TIME].nunique(),
                   "first": str(df[TIME].min()), "last": str(df[TIME].max())}
            for name, df in parts.items()}


def boundary_rows(parts: dict[str, pd.DataFrame]) -> pd.DataFrame:
    pieces = []
    for left, right in [("train", "val"), ("val", "test")]:
        for name, stamp in [(left, parts[left][TIME].max()),
                            (right, parts[right][TIME].min())]:
            piece = parts[name].loc[parts[name][TIME].eq(stamp)].copy()
            piece.insert(0, "split", name)
            piece.insert(0, "boundary", f"{left}/{right}")
            pieces.append(piece)
    return pd.concat(pieces, ignore_index=True).sort_values(["boundary", TIME, ZONE])


def run(output: Path, strict_dir: Path) -> None:
    cfg = get_config()
    for folder in [output, strict_dir]:
        if folder.exists():
            raise FileExistsError(f"Choose a new output directory: {folder}")
    raw_path = cfg.processed_dir / "demand_hourly.parquet"
    features_path = cfg.features_dir / "demand_features.parquet"
    paths = {s: cfg.features_dir / f"demand_{s}.parquet" for s in ["train", "val", "test"]}
    originals = {s: pd.read_parquet(p) for s, p in paths.items()}
    raw = pd.read_parquet(raw_path).sort_values([ZONE, TIME]).reset_index(drop=True)
    features = pd.read_parquet(features_path).sort_values([ZONE, TIME]).reset_index(drop=True)
    assert not raw.duplicated([ZONE, TIME]).any()
    assert not features.duplicated([ZONE, TIME]).any()
    assert raw.groupby(ZONE)[TIME].diff().dropna().eq(pd.Timedelta(hours=1)).all()
    pd.testing.assert_frame_equal(
        pd.concat(originals.values()).sort_values([ZONE, TIME]).reset_index(drop=True), features)

    lags = cfg.features["demand_lags"]
    windows = cfg.features["demand_rolling_windows"]
    max_errors = {f"lag_{lag}": 0.0 for lag in lags}
    max_errors.update({f"rolling_{stat}_{w}": 0.0 for w in windows for stat in ["mean", "std"]})
    examples = []
    # Independent reconstruction: direct past array slices, not groupby.shift/rolling.
    for zone, history in raw.groupby(ZONE):
        history = history.reset_index(drop=True)
        current = features.loc[features[ZONE].eq(zone)]
        positions = pd.Index(history[TIME]).get_indexer(current[TIME])
        assert (positions >= max(lags)).all()
        counts = history[TARGET].to_numpy(dtype=float)
        np.testing.assert_array_equal(current[TARGET], counts[positions])
        for lag in lags:
            expected = counts[positions - lag]
            actual = current[f"lag_{lag}"].to_numpy()
            np.testing.assert_allclose(actual, expected, rtol=0, atol=0)
            max_errors[f"lag_{lag}"] = max(max_errors[f"lag_{lag}"], float(np.max(abs(actual - expected))))
        for window in windows:
            slices = np.lib.stride_tricks.sliding_window_view(counts, window)[positions - window]
            for stat, expected in [("mean", slices.mean(axis=1)),
                                   ("std", slices.std(axis=1, ddof=1))]:
                col = f"rolling_{stat}_{window}"
                actual = current[col].to_numpy()
                np.testing.assert_allclose(actual, expected, rtol=1e-9, atol=1e-7)
                max_errors[col] = max(max_errors[col], float(np.max(abs(actual - expected))))

    # Pick a busy zone for a readable actual three-hour example at the old boundary.
    origin = originals["val"][TIME].min()
    zone = int(raw.groupby(ZONE)[TARGET].sum().idxmax())
    hist = raw.loc[raw[ZONE].eq(zone)].set_index(TIME)[TARGET]
    row = features.loc[features[ZONE].eq(zone) & features[TIME].eq(origin)].iloc[0]
    for offset in [3, 2, 1]:
        stamp = origin - pd.Timedelta(hours=offset)
        examples.append({"zone": zone, "hour": str(stamp), "count": int(hist.loc[stamp])})
    # Mutate present/future targets in this zone; predictors through origin and
    # every predictor in other zones must be unchanged. Later own-zone inputs react.
    altered = raw.copy()
    changed = altered[ZONE].eq(zone) & altered[TIME].ge(origin)
    altered.loc[changed, TARGET] += 10000
    rebuilt = build_demand_features(altered, cfg).sort_values([ZONE, TIME]).reset_index(drop=True)
    original_rebuilt = build_demand_features(raw, cfg).sort_values([ZONE, TIME]).reset_index(drop=True)
    pd.testing.assert_frame_equal(features, original_rebuilt)
    predictors = feature_columns(features)
    protected = features[ZONE].ne(zone) | features[TIME].le(origin)
    pd.testing.assert_frame_equal(features.loc[protected, predictors], rebuilt.loc[protected, predictors])
    later = features[ZONE].eq(zone) & features[TIME].gt(origin)
    assert not features.loc[later, predictors].equals(rebuilt.loc[later, predictors])

    strict = dict(zip(["train", "val", "test"], timestamp_group_split(features, TIME), strict=True))
    assert strict["train"][TIME].max() < strict["val"][TIME].min()
    assert strict["val"][TIME].max() < strict["test"][TIME].min()
    combined = pd.concat(strict.values()).sort_values([ZONE, TIME]).reset_index(drop=True)
    pd.testing.assert_frame_equal(combined, features)
    assert combined.groupby(TIME).size().eq(raw[ZONE].nunique()).all()
    output.mkdir(parents=True)
    strict_dir.mkdir(parents=True)
    boundary_rows(originals).to_csv(output / "original-boundary-rows.csv", index=False)
    boundary_rows(strict).to_csv(output / "strict-boundary-rows.csv", index=False)
    for split, frame in strict.items():
        frame.to_parquet(strict_dir / f"demand_{split}.parquet", index=False)
    try:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        status = subprocess.check_output(["git", "status", "--short"], text=True).strip()
    except subprocess.CalledProcessError:
        head, status = "unavailable", "unavailable"
    hashed = [raw_path, features_path, *paths.values(), Path(__file__),
              Path("src/data/splits.py"), Path("src/features/demand_features.py"),
              Path("config/config.yaml")]
    report = {
        "audit_time_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "git_head": head, "working_tree_status": status,
        "original": summarize(originals), "strict": summarize(strict),
        "strict_directory": str(strict_dir.resolve()),
        "original_boundary_counts": boundary_rows(originals).groupby(["boundary", "split"]).size().to_dict(),
        "feature_rows_verified": len(features), "zones_verified": raw[ZONE].nunique(),
        "features_checked": max_errors,
        "causality_probe": {"zone": zone, "origin": str(origin),
                            "prior_three_hours": examples,
                            "stored_lag_1": float(row["lag_1"]),
                            "stored_rolling_mean_3": float(row["rolling_mean_3"]),
                            "stored_rolling_std_3": float(row["rolling_std_3"]),
                            "current_future_mutation": "+10000 to targets at/after origin in chosen zone",
                            "predictors_through_origin_unchanged": True,
                            "other_zones_predictors_unchanged": True,
                            "later_own_zone_predictors_changed": True},
        "checks": "PASS: unique/dense keys, original union, all history features, perturbation, strict separation and exact row conservation",
        "input_and_code_sha256": {str(p): digest(p) for p in hashed},
        "strict_output_sha256": {str(p): digest(p) for p in strict_dir.glob("*.parquet")},
        "limitations": ["Historical targets in later validation/test hours support rolling one-step evaluation, not fixed-origin multi-hour forecasting.",
                        "Publication/ingestion delay is not measured by timestamp ordering.",
                        "No training or accuracy evaluation performed. Legacy pipeline still uses row splits."]}
    # JSON object keys must be strings, including the grouped boundary tuples.
    report["original_boundary_counts"] = {
        f"{boundary}:{split}": int(n)
        for (boundary, split), n in report["original_boundary_counts"].items()}
    text = json.dumps(report, indent=2, default=lambda value: value.item())
    (output / "audit.json").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--strict-dir", type=Path, default=Path("data/features/strict-hourly-v1"))
    args = parser.parse_args()
    run(args.output, args.strict_dir)
