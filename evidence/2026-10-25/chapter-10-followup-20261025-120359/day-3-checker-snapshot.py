"""Small objective checks for a learner's functions. No mastery grade is inferred."""
from __future__ import annotations
import argparse
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--day", type=int, choices=[1, 2, 3, 4], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("learner_submission", args.submission.resolve())
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    outcomes = []

    def check(name, action):
        try:
            action()
            outcomes.append({"case": name, "status": "passed"})
        except Exception as exc:
            outcomes.append({"case": name, "status": "failed", "error": f"{type(exc).__name__}: {exc}"})

    def equals(value, expected):
        assert value == expected, f"Expected {expected!r}; got {value!r}"

    def rejects(action):
        try:
            action()
        except ValueError:
            return
        raise AssertionError("Expected ValueError")

    if args.day == 1:
        check("RMSE known values", lambda: equals(math.isclose(module.calculate_rmse([2, 4, 6], [3, 4, 5]), math.sqrt(2/3)), True))
        check("RMSE perfect predictions", lambda: equals(module.calculate_rmse([2, 4], [2, 4]), 0))
        check("RMSE rejects empty input", lambda: rejects(lambda: module.calculate_rmse([], [])))
        check("RMSE rejects unequal lengths", lambda: rejects(lambda: module.calculate_rmse([1], [1, 2])))
        hours = pd.date_range("2024-01-01", periods=4, freq="h")
        frame = pd.DataFrame({"zone": [1]*4+[2]*4, "hour": list(hours)*2, "count": [1, 2, 4, 8, 100, 200, 400, 800]}).sample(frac=1, random_state=7)
        original = frame.copy(deep=True)
        def history_case():
            built = module.make_history_features(frame)
            assert frame.equals(original), "Input was mutated"
            assert len(built) == 8
            for zone, last_lag, rolling in [(1, 4, 7/3), (2, 400, 700/3)]:
                rows = built[built.zone==zone].sort_values("hour")
                assert pd.isna(rows.iloc[0].lag_1)
                assert rows.iloc[-1].lag_1 == last_lag
                assert math.isclose(rows.iloc[-1].rolling_mean_3, rolling)
        check("Grouped past-only lags/rolling, ordering and no mutation", history_case)
        def mutation_case():
            before = module.make_history_features(frame)
            changed = frame.copy()
            changed.loc[(changed.zone==1)&(changed.hour==hours[-1]), "count"] = 9999
            after = module.make_history_features(changed)
            for table in [before, after]:
                assert not table.duplicated(["zone", "hour"]).any()
            b = before[(before.zone==1)&(before.hour==hours[-1])].iloc[0]
            a = after[(after.zone==1)&(after.hour==hours[-1])].iloc[0]
            assert a.lag_1 == b.lag_1 and a.rolling_mean_3 == b.rolling_mean_3
        check("Current target mutation does not change own features", mutation_case)
    elif args.day == 2:
        check("Validation beats attractive test score", lambda: equals(module.choose_validation_winner({"A": {"val_rmse": 4, "test_rmse": 100}, "B": {"val_rmse": 5, "test_rmse": 1}}), "A"))
        check("Tie has declared deterministic rule", lambda: equals(module.choose_validation_winner({"B": {"val_rmse": 3}, "A": {"val_rmse": 3}}), "A"))
        check("Reject empty comparison", lambda: rejects(lambda: module.choose_validation_winner({})))
    elif args.day == 3:
        for title, values, expected in [
            ("All conditions and boundaries pass", (50, 5, True, True, "true"), True),
            ("Demand quality fails", (51, 4, True, True, "true"), False),
            ("Fare quality fails", (49, 6, True, True, "true"), False),
            ("Demand baseline fails", (49, 4, False, True, "true"), False),
            ("Fare baseline fails", (49, 4, True, False, "true"), False),
            ("False authorization", (49, 4, True, True, "false"), False),
            ("Portal typo is not authorization", (49, 4, True, True, "2"), False)]:
            check(title, lambda values=values, expected=expected: equals(module.release_allowed(*values), expected))
    else:
        def kpi_case():
            result = module.reconcile_kpi([1000.1, 653.0667])
            assert math.isclose(result["raw_total"], 1653.1667)
            assert result["displayed_pickups"] == 1653
            assert result["displayed_revenue"] == 29757
        check("Round only at display, use raw sum for revenue", kpi_case)
        check("Empty forecast totals zero", lambda: equals(module.reconcile_kpi([]), {"raw_total": 0, "displayed_pickups": 0, "displayed_revenue": 0}))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = {"day": args.day, "scope": "Objective function checks only; written reasoning and actual capstone evidence require review",
              "submission": str(args.submission.resolve()), "cases": outcomes,
              "all_passed": all(row["status"]=="passed" for row in outcomes), "mastery_status": "unreviewed", "capstone_readiness": "unverified"}
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["all_passed"] else 1)


if __name__ == "__main__":
    main()
