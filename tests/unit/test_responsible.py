"""Tests for responsible-AI (fairness, explainability, model cards)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.tree import DecisionTreeRegressor

from src.models import common
from src.responsible import fairness
from src.responsible.explain import explain_instance, global_importance
from src.responsible.model_card import render_model_card


# --- Fairness --------------------------------------------------------------
def test_time_of_day_bucket():
    assert fairness.time_of_day_bucket(3) == "overnight"
    assert fairness.time_of_day_bucket(9) == "morning"
    assert fairness.time_of_day_bucket(15) == "afternoon"
    assert fairness.time_of_day_bucket(21) == "evening"
    assert fairness.time_of_day_bucket(24) == "overnight"


def test_add_borough_maps_and_fills_unknown():
    lookup = pd.DataFrame(
        {
            "LocationID": [1, 2],
            "Borough": ["Manhattan", "Queens"],
            "Zone": ["A", "B"],
            "service_zone": ["Yellow Zone", "Airports"],
        }
    )
    df = pd.DataFrame({"PULocationID": [1, 2, 999]})
    out = fairness.add_borough(df, lookup)
    assert out["borough"].tolist() == ["Manhattan", "Queens", "Unknown"]
    assert out["service_zone"].tolist() == ["Yellow Zone", "Airports", "Unknown"]


def test_disparity_ratio():
    assert fairness.disparity_ratio([2.0, 4.0]) == pytest.approx(2.0)
    assert fairness.disparity_ratio([3.0]) == 1.0  # single group -> parity
    assert fairness.disparity_ratio([]) == 1.0


def test_subgroup_metrics_flags_disparity():
    rng = np.random.default_rng(0)
    n = 200
    # Group A: accurate; Group B: large error -> should be flagged.
    df = pd.DataFrame({"borough": ["A"] * n + ["B"] * n})
    y_true = np.concatenate([rng.normal(10, 1, n), rng.normal(10, 1, n)])
    y_pred = np.concatenate([y_true[:n] + rng.normal(0, 0.2, n), y_true[n:] + 8.0])

    report = fairness.subgroup_metrics(df, y_true, y_pred, "borough", min_size=10)
    assert report.dimension == "borough"
    assert {s.group for s in report.subgroups} == {"A", "B"}
    assert report.worst_group == "B"
    assert report.best_group == "A"
    assert report.disparity > 1.5
    assert report.flagged


def test_subgroup_metrics_skips_small_groups():
    df = pd.DataFrame({"g": ["A"] * 50 + ["B"] * 5})
    y_true = np.ones(55)
    y_pred = np.ones(55)
    report = fairness.subgroup_metrics(df, y_true, y_pred, "g", min_size=30)
    assert [s.group for s in report.subgroups] == ["A"]


# --- Explainability --------------------------------------------------------
@pytest.fixture()
def fare_model(clean_trips_df):
    from src.features.fare_features import build_fare_features

    feats = build_fare_features(clean_trips_df)
    X, y = common.split_to_xy(feats, "fare")
    model = DecisionTreeRegressor(max_depth=4, random_state=0).fit(X, y)
    return model, X


def test_explain_instance_is_additive(fare_model):
    model, X = fare_model
    row = X.iloc[[0]]
    exp = explain_instance(model, row)
    # SHAP additivity: base + sum(contributions) == model prediction.
    assert exp.prediction == pytest.approx(float(model.predict(row)[0]), rel=1e-4)
    assert set(exp.contributions) == set(X.columns)
    top = exp.top(3)
    assert len(top) == 3


def test_global_importance_ranks_features(fare_model):
    model, X = fare_model
    imp = global_importance(model, X.head(100))
    assert list(imp.columns) == ["feature", "importance"]
    assert (imp["importance"] >= 0).all()
    # Sorted descending.
    assert imp["importance"].is_monotonic_decreasing


# --- Model card ------------------------------------------------------------
def test_render_model_card_contains_sections():
    report = fairness.FairnessReport(
        dimension="borough",
        subgroups=[
            fairness.SubgroupMetric("borough", "Manhattan", 100, 2.0, 1.5, 10.0),
            fairness.SubgroupMetric("borough", "Bronx", 80, 4.0, 3.0, 25.0),
        ],
    )
    card = render_model_card(
        name="taxi-fare-predictor",
        problem="fare",
        algorithm="XGBoost",
        target="fare_amount",
        metrics={"rmse": 3.4, "r2": 0.95},
        fairness=[report],
        top_features=[("trip_distance", 2.1), ("PULocationID", 1.3)],
        version="2",
    )
    assert "# Model Card — taxi-fare-predictor" in card
    assert "## Intended use" in card
    assert "## Evaluation — subgroup fairness" in card
    assert "Disparity ratio" in card
    assert "## Ethical considerations" in card
    assert "trip_distance" in card


def test_single_group_is_not_reported_as_parity():
    report = fairness.FairnessReport(
        dimension="holiday",
        subgroups=[fairness.SubgroupMetric("holiday", "non-holiday", 100, 2, 1, 10)],
    )
    payload = report.to_dict()
    assert payload["status"] == "insufficient_comparison"
    assert payload["disparity_ratio"] is None
    assert not payload["flagged"]
    card = render_model_card(
        name="test", problem="demand", algorithm="tree", target="count",
        metrics={}, fairness=[report],
    )
    assert "Insufficient comparison" in card
    assert "— ok" not in card


def test_card_preserves_model_identity_and_valid_shap_heading():
    card = render_model_card(
        name="test", problem="fare", algorithm="tree", target="fare",
        metrics={}, version="7", run_id="run-7", model_reference="models:/test/7",
        evaluation_notes=["Canonical test split; strict retraining not performed."],
        top_features=[("distance", 1.2)],
    )
    assert "Registry version:** 7" in card
    assert "`run-7`" in card
    assert "`models:/test/7`" in card
    assert "strict retraining not performed" in card
    assert "| Feature | Mean absolute SHAP value |" in card


def test_resolve_latest_loads_numeric_version(monkeypatch):
    from types import SimpleNamespace

    from scripts.responsible import run_analysis
    from src.config import Config

    versions = [SimpleNamespace(version="2", run_id="run2"),
                SimpleNamespace(version="10", run_id="run10")]

    class Client:
        def search_model_versions(self, query):
            return versions

        def get_run(self, run_id):
            assert run_id == "run10"
            return SimpleNamespace(data=SimpleNamespace(params={"n_trials": "1"}))

    config = Config({"serving": {"model_stage": "latest"}})
    monkeypatch.setattr(run_analysis, "configure_mlflow", lambda config: None)
    monkeypatch.setattr(run_analysis.mlflow, "MlflowClient", Client)

    def load(problem, pinned):
        assert pinned.serving["model_stage"] == "10"
        return "loaded"

    monkeypatch.setattr(run_analysis.registry, "load_model", load)
    model, metadata = run_analysis.resolve_model("demand", config)
    assert model == "loaded"
    assert metadata["model_uri"] == "models:/taxi-demand-forecaster/10"
    assert metadata["run_id"] == "run10"
    assert config.serving["model_stage"] == "latest"
