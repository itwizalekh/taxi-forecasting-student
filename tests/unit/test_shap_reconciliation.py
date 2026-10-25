"""The learner exercise must check model.predict independently of SHAP's sum."""

import pandas as pd
import pytest
from sklearn.tree import DecisionTreeRegressor

from scripts.responsible import reconcile_prediction


@pytest.fixture()
def fare_model():
    X = pd.DataFrame({"distance": [1., 2., 3., 4.], "duration": [5., 8., 12., 16.]})
    model = DecisionTreeRegressor(random_state=42).fit(X, [8., 12., 16., 20.])
    return model, X


def test_full_vector_matches_independent_prediction(fare_model):
    model, X = fare_model
    result = reconcile_prediction.reconcile(model, X.iloc[[0]])
    assert result["raw_prediction"] == pytest.approx(float(model.predict(X.iloc[[0]])[0]))
    assert list(result["contributions"]) == list(X.columns)
    assert result["residual"] == pytest.approx(0, abs=1e-8)


def test_wrong_explanation_fails_even_when_its_own_sum_is_consistent(fare_model, monkeypatch):
    model, X = fare_model
    original = reconcile_prediction.explain_instance

    def wrong(model, row):
        explanation = original(model, row)
        explanation.base_value += 10
        explanation.prediction += 10
        return explanation

    monkeypatch.setattr(reconcile_prediction, "explain_instance", wrong)
    with pytest.raises(ValueError, match="reconciliation failed"):
        reconcile_prediction.reconcile(model, X.iloc[[0]])
