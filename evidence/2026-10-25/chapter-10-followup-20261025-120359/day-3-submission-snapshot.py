"""Copy into your day submission and implement the relevant functions yourself.

The checker tests observable behavior, not conceptual mastery or capstone readiness.
See PRACTICE_LABS.md and DAILY_STUDY_PLAN.md for requirements and questions.
"""


def calculate_rmse(actual, predicted):
    """Return RMSE for equal-length, nonempty 1D numeric inputs.

    Use Python/NumPy arithmetic; do not call a metric library.
    Raise ValueError on unequal lengths or empty inputs.
    """
    raise NotImplementedError("Day1: implement RMSE from its definition")


def make_history_features(frame):
    """Return a zone/hour-sorted copy with lag_1 and rolling_mean_3.

    Input columns: zone, hour (pandas datetime), count; one row/zone/hour.
    Group within zone; exclude the current target. Rolling min_periods=1.
    Preserve rows/columns; missing initial history remains NaN. Never mutate input.
    """
    raise NotImplementedError("Day1: implement past-only grouped history")


def choose_validation_winner(candidate_metrics):
    """Return name with lowest val_rmse, alphabetical tie-break.

    Input: {name: {val_rmse: finite number, test_rmse: optional number}}.
    Ignore test_rmse completely. Raise ValueError for an empty mapping.
    """
    raise NotImplementedError("Day2: choose using validation only")


def release_allowed(demand_rmse, fare_rmse, demand_baseline_passed, fare_baseline_passed, deploy_permission):
    """Return Boolean for chapter12's five conditions at default thresholds.

    Demand <=50, fare <=5, both baseline Booleans true, permission string 'true'.
    This is a policy exercise; no actual deployment is performed.
    """
    # Release is allowed only when every quality, baseline, and authorization
    # gate passes. Use identity checks so values like 1 do not count as True.
    return (
        demand_rmse <= 50
        and fare_rmse <= 5
        and demand_baseline_passed is True
        and fare_baseline_passed is True
        and deploy_permission == "true"
    )


def reconcile_kpi(predicted_pickups, average_fare=18.0):
    """Return raw_total, displayed_pickups and displayed_revenue.

    Sum unrounded finite nonnegative forecasts. displayed_pickups=round(raw_total).
    displayed_revenue=round(raw_total*average_fare), not rounded pickups*fare.
    """
    raise NotImplementedError("Day4: reconcile from raw values")
