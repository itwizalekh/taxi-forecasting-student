"""Assessment comparisons must use identical rows and origin-safe production semantics."""

import numpy as np
import pandas as pd
import pytest

from scripts.assess_strict_demand import aligned_common, feature_matrix, recursive_forecast
from src.config import get_config
from src.features.demand_features import build_demand_features, feature_columns
from src.serving.batch import forecast_demand
from src.serving.features import build_demand_row
from src.serving.service import ModelService


class LagModel:
    def predict(self, X):
        return X.lag_1.to_numpy() + .6


class NegativeModel:
    def predict(self, X):
        return np.full(len(X), -2.3)


def history_frame():
    hours = pd.date_range("2024-01-01", periods=200, freq="h")
    return pd.DataFrame([(z, t, i % 7 + z) for z in (1, 2) for i, t in enumerate(hours)],
                        columns=["PULocationID", "pickup_hour", "pickup_count"])


def test_common_rows_are_exact_and_duplicate_keys_fail():
    frame = history_frame().iloc[:10].copy()
    common, counts = aligned_common(frame.iloc[2:], frame)
    assert len(common) == 8
    assert counts["strict_only_rows"] == 2
    wrong = frame.copy()
    wrong.loc[3, "pickup_count"] += 1
    with pytest.raises(AssertionError):
        aligned_common(frame.iloc[2:], wrong)
    with pytest.raises(ValueError, match="Duplicate"):
        aligned_common(pd.concat([frame, frame.iloc[:1]]), frame)


def test_future_mutation_invariant_and_matches_production_batch():
    history = history_frame()
    origin = pd.Timestamp("2024-01-08 12:00")
    config = get_config()
    columns = feature_columns(build_demand_features(history, config))
    model = LagModel()
    result, _ = recursive_forecast(model, history, origin, [1, 2], config, columns,
                                   horizon=4, verify_serving=True)
    mutated = history.copy()
    mutated.loc[mutated.pickup_hour >= origin, "pickup_count"] += 10000
    repeat, _ = recursive_forecast(model, mutated, origin, [1, 2], config, columns, horizon=4)
    pd.testing.assert_frame_equal(result, repeat)
    prior = history.loc[history.pickup_hour < origin]
    service = ModelService(model, None, prior, config)
    production = forecast_demand(service, horizon_hours=4, start_hour=origin, zones=[1, 2], config=config)
    actual = result.sort_values(["PULocationID", "pickup_hour"])
    expected = production.sort_values(["PULocationID", "pickup_hour"])
    np.testing.assert_array_equal(actual.prediction, expected.predicted_pickups)


def test_negative_predictions_are_clipped_and_history_receives_zero():
    history = history_frame()
    config = get_config()
    columns = feature_columns(build_demand_features(history, config))
    result, _ = recursive_forecast(NegativeModel(), history, pd.Timestamp("2024-01-08 12:00"),
                                   [1, 2], config, columns, horizon=2)
    assert (result.raw_prediction == -2.3).all()
    assert (result.prediction == 0).all()
    assert (result.history_count == 0).all()


def test_feature_matrix_matches_production_exactly_including_rolling_std():
    history = history_frame()
    config = get_config()
    origin = pd.Timestamp("2024-01-08 12:00")
    columns = feature_columns(build_demand_features(history, config))
    times = pd.date_range(origin - pd.Timedelta(hours=168), origin - pd.Timedelta(hours=1), freq="h")
    grid = history.pivot(index="pickup_hour", columns="PULocationID", values="pickup_count")
    batch = feature_matrix(grid.loc[times, [1, 2]].to_numpy().T, [1, 2], origin, config, columns)
    for i, zone in enumerate([1, 2]):
        expected = build_demand_row(history.loc[history.pickup_hour < origin], zone, origin, config)
        np.testing.assert_array_equal(batch.iloc[[i]].to_numpy(), expected[columns].to_numpy())
