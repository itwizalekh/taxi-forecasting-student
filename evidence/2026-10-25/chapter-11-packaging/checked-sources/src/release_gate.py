"""Policy helper for deciding whether model release prerequisites are met.

This evaluates configured quality, baseline, and authorization conditions. It
does not build, deploy, or otherwise release a model.
"""


def release_allowed(
    demand_rmse: float,
    fare_rmse: float,
    demand_baseline_passed: bool,
    fare_baseline_passed: bool,
    deploy_permission: str,
) -> bool:
    """Return whether all five default release conditions pass.

    Demand RMSE must be at most 50, fare RMSE at most 5, both baseline
    comparisons must be exactly ``True``, and permission must be ``"true"``.
    """
    return (
        demand_rmse <= 50
        and fare_rmse <= 5
        and demand_baseline_passed is True
        and fare_baseline_passed is True
        and deploy_permission == "true"
    )
