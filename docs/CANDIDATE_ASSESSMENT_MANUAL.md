# Manual reference: assess the strict-hour demand candidate

This guide accompanies the actual January diagnostic results in
`evidence/2026-10-25/candidate-assessment/`. Read `ASSESSMENT.md` there first.
All commands below run from `C:\Data\BITS\labs\taxi-forecasting-student`.
Use a new output directory whenever repeating an assessment or replay.

## 1. Verify which candidate was selected

Open the candidate's original `artifacts/strict-demand/candidate-your-run/training_summary.json`.
Check:

- Candidate registry: `taxi-demand-forecaster-strict-hourly`, numeric version 1.
- Winning algorithm: XGBoost.
- Source run: `2f79615caca841f2b44b7627c4de5a96`.
- Validation RMSE: 8.130270; test RMSE on its own strict rows: 8.684194.
- LightGBM validation RMSE is 8.314129, while its test RMSE is 8.551785.

The validation comparison selects XGBoost. Choosing LightGBM because its test
score looks better would turn the test into a selection set. Do not do that.
The original model is `taxi-demand-forecaster/1`, source run
`771eb4d4470f4da9ab8467568f9a8f34`, trained with one trial per estimator.
The candidate used 25 trials per estimator. A performance difference cannot be
attributed solely to the new split because model family and tuning budget changed.

In the MLflow UI, open each registered model, numeric version and source run;
match these IDs and training parameters against the report's `protocol.json`.

## 2. Verify strict boundaries and file identity

The complete-hour train/validation/test counts are 116,380 / 14,674 / 14,674.
Their periods end/start at Jan 27 03:00/04:00 and Jan 29 13:00/14:00 respectively.
There are no shared target timestamps. Past actual counts may still supply lag
context across boundaries when they would be available at prediction time.

```powershell
Get-FileHash data/features/strict-hourly-v1/demand_train.parquet -Algorithm SHA256
Get-FileHash data/features/strict-hourly-v1/demand_val.parquet -Algorithm SHA256
Get-FileHash data/features/strict-hourly-v1/demand_test.parquet -Algorithm SHA256
```

Compare hashes with `inputs/candidate-preflight.json` and `manifest.json` in the
assessment evidence. Hexadecimal hashes are case-insensitive. These identify the
files verified now; they do not independently certify historical training data.
The saved candidate preflight was created before its training run.

## 3. Distinguish native scores from paired scores

Open `native_metrics.csv`: legacy uses 14,573 rows, candidate 14,674 rows.
Then open `common_metrics.csv`: BOTH use exactly 14,573 shared zone/hour rows.
The report verifies targets and all feature values agree exactly on those keys.

The strict-only 101 rows at Jan 29 14:00 were part of legacy validation, so they
cannot be treated as clean legacy test rows. They are excluded from the paired
comparison. Both models' full native results remain separately recorded.

Expected common-row result:

| Metric | Legacy | Candidate |
|---|---:|---:|
| RMSE | 8.7022295711 | 8.6991519725 |
| MAE | 2.5349826043 | 2.5246417024 |

Relative RMSE change is `100 * (candidate / legacy - 1)`, about **-0.0354%**.
This is a small measured diagnostic decrease; it is not a significant or broad
improvement claim. The January test has already been inspected repeatedly.

## 4. Recompute the paired errors yourself

The full evidence is `paired_predictions.csv.gz`. Keep that compressed original.
For a spreadsheet-friendly copy:

```powershell
.\.venv\Scripts\python.exe -c "import pandas as pd; pd.read_csv('evidence/2026-10-25/candidate-assessment/paired_predictions.csv.gz').to_csv('artifacts/strict-demand/manual-expanded-paired.csv', index=False)"
```

Open the expanded CSV in your spreadsheet viewer. Its columns are:

| Column | Field |
|---|---|
| A | PULocationID |
| B | pickup_hour |
| C | pickup_count (actual) |
| D | legacy_prediction |
| E / F / G | legacy_error / absolute_error / squared_error |
| H | candidate_prediction |
| I / J / K | candidate_error / absolute_error / squared_error |

In a separate workbook or sheet, check row 2 using `=D2-C2`, `=ABS(E2)`, `=E2^2`
for legacy and `=H2-C2`, `=ABS(I2)`, `=I2^2` for candidate. Extend down through
row 14,574 (one header plus 14,573 observations). Verify:

```text
Legacy MAE     = AVERAGE(F2:F14574)
Legacy RMSE    = SQRT(AVERAGE(G2:G14574))
Candidate MAE  = AVERAGE(J2:J14574)
Candidate RMSE = SQRT(AVERAGE(K2:K14574))
```

Match `common_metrics.csv` within floating-point tolerance. Do not average
subgroup RMSEs to obtain overall RMSE. Do not use the first-50-row sample to
reproduce the full-table aggregate.

Alternatively, independently recompute all common-row and horizon RMSE/MAE,
then replay one candidate trajectory through the serving row builder:

```powershell
.\.venv\Scripts\python.exe -m scripts.manual_check_demand_assessment --assessment evidence/2026-10-25/candidate-assessment --model candidate --zone 132 --output artifacts/strict-demand/manual-candidate-your-run
```

Expected: PASS, matching aggregate scores and all 24 replayed predictions. This
checker calculates errors directly with NumPy rather than calling the report's
score helper. It also checks duplicate keys and future-actual perturbation.

## 5. Assess subgroup tradeoffs on common rows

Open `paired_subgroup_metrics.csv`. Filter to `dimension=borough`; compare
legacy and candidate with the same group and row count. Queens RMSE improves
from about 6.4665 to 5.8801, but Manhattan RMSE worsens from 15.5512 to 15.7818.
Some smaller borough groups worsen too. Overall similarity can mask different
geographic error patterns. Larger raw counts also change absolute RMSE scale.

No test weekend or holiday group is present. A lone weekday/non-holiday group
does not establish parity. Geographic slices do not measure demographic fairness.

## 6. Inspect a single recursive forecast end to end

The independent checker creates `one_zone_feature_trace.csv` for zone 132 at the
first origin, Jan 29 2024 at 15:00. Inspect its 24 rows in horizon order:

1. Horizon 1 targets 15:00; horizon 2 targets 16:00; horizon 24 targets the next
   day at 14:00. A lead of 1 means the first unobserved hour, labelled by its start.
2. At the origin, actual history ends at 14:00; no 15:00 or later actual is allowed.
3. Check `clipped_prediction = MAX(0, raw_prediction)`.
4. Check `history_count = int(round(clipped_prediction))`, using Python's
   ties-to-even rounding. Excel ROUND can differ at exact .5 ties.
5. Check `prediction = round(clipped_prediction, 4)`, matching batch presentation.
6. From the second row onward, `input_lag_1` must equal the PREVIOUS row's
   `history_count`, not the previous target's actual observed pickup count.
7. Inspect lag_24, lag_168 and rolling inputs. Each must come only from actuals
   before the origin or earlier predictions in this trajectory.
8. Read `backtest_predictions.csv.gz` or `first_origin_manual.csv` to compare the
   same model/zone/origin trajectory with actual targets. Actuals join for scoring
   after prediction generation; they do not feed the recursive inputs.

Run the independent checker with `--model legacy` and a different output folder
to perform the same replay for the original model.

## 7. Check that future actuals cannot affect forecasts

Open `leakage_and_serving_checks.json`. All **12** entries should say PASS:
six origins multiplied by two fitted models. At each origin the assessment adds
10,000 to all source target counts at or after the origin, reruns the forecast,
and requires identical predictions for all 253 zones and all 24 leads.

The batched features and raw predictions were separately checked against the
serving row builder at every step for three probe zones per origin/model. The
independent zone-132 replay checks an additional full trajectory. These are
finite tests plus explicit origin truncation, not a proof of all possible paths.

Both validation cutoffs precede every origin. The first origin is Jan 29 15:00,
not 14:00, because the legacy validation still included some 14:00 zone targets.
At a later origin, actuals observed since an earlier origin can be used; inside
one origin's 24-hour forecast, they cannot.

For a full repeat to a new directory:

```powershell
.\.venv\Scripts\python.exe -m scripts.assess_strict_demand --old-version 1 --candidate-version 1 --output artifacts/strict-demand/assessment-your-repeat
```

## 8. Compare each forecast lead against both baselines

Filter `horizon_metrics.csv` to horizons 1, 3, 6, 12 and 24. Each model/baseline at
each exact lead has 1,518 forecasts = six origins times 253 zones. Compare using
the SAME origin, target hour and zone keys.

- Persistence repeats the last actual available before origin at every lead.
- Weekly baseline uses the actual count at target-minus-168-hours, which is
  before origin for every evaluated lead.
- Candidate RMSE is lower than legacy at all five requested leads.
- Weekly RMSE is lower than candidate at 3/6/12/24 hours. At 12/24 hours candidate
  MAE is lower than weekly MAE, showing a large-error versus typical-error tradeoff.

Inspect `horizon_errors.png`. Error need not grow monotonically because the
target hours and demand levels change with the lead. Overlapping origins and
zones are dependent; six origins over three target dates are not sufficient for
confident generalization or narrow uncertainty estimates.

## 9. Freeze the later-period protocol before observing results

`protocol.json` freezes this assessment's numeric model identities, forecast
origins, leads, metrics, baselines and postprocessing before its calculations.
For later evaluation, create a separate plan BEFORE fetching/scoring the period.
Specify model URIs/run IDs, target dates, forecast origins, history cutoff and
arrival-delay assumption, score units, primary metric, subgroup support rules,
baseline definitions, and what evidence would justify any model promotion.

The proposed full February 2024 calendar has 696 hours, eight weekend dates and
one US-holiday date under this repository's holiday function: February 19.
That is synthetic calendar coverage, not evidence of available/complete trip data.
No February observations were downloaded, scored or used for tuning here.

After ingestion, inspect actual distinct dates, zone coverage and missingness.
Carry January's final 168 actual hours into continuous history; score only
February targets. Do not rebuild each month separately and discard the new
month's first week. Report distinct holiday events alongside row counts: one
holiday with thousands of zones/hours is still one holiday event.

If February results prompt tuning, February becomes development evidence.
Reserve a later untouched window with the required calendar coverage for final
evaluation of the revised model. Do not keep selecting models against January.

## 10. Record the bounded assessment

The current supported conclusion is: strict timestamp separation is established
for the candidate; same-row January RMSE/MAE are slightly lower; six-origin
recursive evaluation favors the candidate over legacy at requested leads, but
does not consistently beat the weekly baseline. Weekend/holiday and broader
seasonal validation remain open. Retain the candidate for further evaluation;
general improvement, causal benefit, equity and deployment readiness are not
established.

Validation performed for the supplied assessment: **141 tests passed**, **95.01%**
coverage of `src`, one existing multipart pending-deprecation warning; changed
assessment Python files pass Ruff. Existing unrelated learner-script lint issues
remain outside this assessment.

An earlier NumPy approximation of rolling statistics was rejected after an
independent legacy-model replay diverged. Tree thresholds can react to tiny
floating-point differences. The preserved final assessment reuses the production
feature builder, requires exact feature equality in its serving-reference probes,
and includes independent complete zone-132 replays for both model versions.
Earlier approximate results are not part of the final evidence or conclusions.
