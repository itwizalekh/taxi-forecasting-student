from src.release_gate import release_allowed


def test_release_allowed_at_inclusive_quality_thresholds() -> None:
    assert release_allowed(50, 5, True, True, "true") is True


def test_release_denied_when_demand_rmse_exceeds_threshold() -> None:
    assert release_allowed(50.01, 5, True, True, "true") is False


def test_release_denied_when_fare_rmse_exceeds_threshold() -> None:
    assert release_allowed(50, 5.01, True, True, "true") is False


def test_release_denied_when_demand_baseline_fails() -> None:
    assert release_allowed(50, 5, False, True, "true") is False


def test_release_denied_when_fare_baseline_fails() -> None:
    assert release_allowed(50, 5, True, False, "true") is False


def test_release_denied_when_permission_is_false() -> None:
    assert release_allowed(50, 5, True, True, "false") is False


def test_portal_typo_is_not_deploy_authorization() -> None:
    assert release_allowed(50, 5, True, True, "2") is False
