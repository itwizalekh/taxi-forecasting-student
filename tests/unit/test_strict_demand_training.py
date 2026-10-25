"""Candidate training must reject temporal overlap and isolate existing serving config."""

import pandas as pd
import pytest

from scripts.train_strict_demand import CANDIDATE_NAME, candidate_config, validate_splits
from src.config import Config


def make_parts():
    hours = pd.date_range("2024-01-01", periods=10, freq="h")
    frame = pd.DataFrame([(z, t, 1) for t in hours for z in (1, 2)],
                         columns=["PULocationID", "pickup_hour", "pickup_count"])
    return {"train": frame.iloc[:16].copy(), "val": frame.iloc[16:18].copy(),
            "test": frame.iloc[18:].copy()}


def test_whole_hours_pass():
    summary = validate_splits(make_parts())
    assert [summary[s]["hours"] for s in ("train", "val", "test")] == [8, 1, 1]


def test_shared_boundary_rejected():
    parts = make_parts()
    parts["val"]["pickup_hour"] = parts["train"].pickup_hour.max()
    with pytest.raises(ValueError, match="overlap"):
        validate_splits(parts)


def test_incomplete_grid_rejected():
    parts = make_parts()
    parts["train"] = parts["train"].iloc[1:]
    with pytest.raises(ValueError, match="incomplete"):
        validate_splits(parts)


def test_candidate_does_not_mutate_base_config(tmp_path):
    base = Config({"data": {"features_dir": "data/features"},
                   "models": {"registry_demand": "taxi-demand-forecaster"},
                   "serving": {"model_stage": "latest"}})
    candidate = candidate_config(base, tmp_path / "strict", tmp_path / "output")
    assert candidate.models["registry_demand"] == CANDIDATE_NAME
    assert base.models["registry_demand"] == "taxi-demand-forecaster"
    assert base.data["features_dir"] == "data/features"
    assert base.serving == candidate.serving == {"model_stage": "latest"}


def test_smoke_dispatch_never_registers(tmp_path, monkeypatch):
    import sys

    from scripts import train_strict_demand

    strict_dir = tmp_path / "strict"
    strict_dir.mkdir()
    for split, frame in make_parts().items():
        frame.to_parquet(strict_dir / f"demand_{split}.parquet", index=False)
    monkeypatch.setattr(train_strict_demand, "get_config", lambda: Config({}))
    output = tmp_path / "smoke-output"

    def train(problem, config, *, n_trials, register):
        assert problem == "demand"
        assert n_trials == 1
        assert register is False
        assert config.models["registry_demand"] == CANDIDATE_NAME
        assert config.features_dir == strict_dir.resolve()
        return {"registered": None}

    monkeypatch.setattr(train_strict_demand, "train_problem", train)
    monkeypatch.setattr(sys, "argv", ["train_strict_demand", "--mode", "smoke",
                        "--features-dir", str(strict_dir), "--output", str(output)])
    train_strict_demand.main()
    assert (output / "preflight.json").exists()
    assert (output / "training_summary.json").exists()
