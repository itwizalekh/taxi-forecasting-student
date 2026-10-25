# Hands-on: reconcile a prediction, scope its card, and plan stronger evaluation

Run from `C:\Data\BITS\labs\taxi-forecasting-student` with the existing virtual
environment. This exercise reuses registered models and data; it does not retrain.

## 1. Understand the current split limits

The evaluated models are local versions `taxi-demand-forecaster/1` and
`taxi-fare-predictor/1`, both trained with one tuning trial per estimator.
Their evaluation inputs are identified in the preserved
[reviewed reports](../evidence/2026-10-25/responsible-analysis/README.md).

### Demand

| Boundary | Earlier split rows at that hour | Later split rows at that hour |
|---|---:|---:|
| 2024-01-27 04:00, train/validation | 202 | 51 |
| 2024-01-29 14:00, validation/test | 101 | 152 |

The old splitter divides a sorted table by row count, so some zones at the same
hour fall on different sides. The target rows are not duplicates, and this alone
does not prove same-hour target leakage; it fails a strict temporal holdout
contract. The complete-hour splitter exists but was not used to train version 1.

Demand's test period is January 29 at 14:00 through January 31 at 23:00, only
14,573 rows over 58 distinct hours. The first hour is partial. There are no
weekend or holiday rows. Lag/rolling features for later test hours use earlier
actual counts. This is rolling one-step evidence assuming completed counts are
available promptly; it does not measure a 24-hour forecast made at one origin.
The first 168 hours are warm-up history, rather than scored examples.

### Fare

Fare's boundaries are strictly ordered in this particular dataset: training ends
January 26 at 06:29:51; validation starts 06:29:55 and ends January 28 at 22:20:01;
test starts 22:20:03 and ends January 31 at 23:59:55. The generic row splitter does
not guarantee this separation for future data with tied timestamps.
The test contains 272,735 trips but only 3,150 weekend trips and no holiday trips.
Large trip counts across a few days do not establish coverage across seasons.
Observed distance and duration support historical trip estimation; actual duration
is not available for a genuine pre-trip prediction. This is an input-availability
limit, separate from split ordering.

The January test sets have already been inspected repeatedly. Treat them as
diagnostic benchmarks; reserve a later untouched period for a final comparison.
Do not infer an unbiased future-deployment score from high R² alone.

## 2. Generate one full contribution vector yourself

Use the already reviewed fare version 1. This command uses row position 0 in the
hashed canonical fare test file, not an invented example. Choose a fresh output
directory each time; existing output directories are rejected.

```powershell
.\.venv\Scripts\python.exe -m scripts.responsible.reconcile_prediction --problem fare --version 1 --row 0 --analysis-dir evidence/2026-10-25/responsible-analysis/reviewed --output artifacts/learner-shap/fare-v1-row0-your-run
```

Inspect `full_contributions.csv` in that output directory. It contains ALL 14
features, their actual model-input values, signed contributions and a running
total in feature-column order. The JSON keeps full numeric precision, row keys,
test-file hash, model URI, run ID, target and tolerance. The waterfall displays
all features but sorts them by impact; it is not the CSV's cumulative order.

Worked result verified on the current local files:

```text
TreeExplainer baseline     = 18.528296985013366
Sum of all 14 contributions= 44.491981826519606
Baseline + sum             = 63.020278811532975
Independent model.predict = 63.020278811533146
Raw minus reconstructed   =  0.00000000000017053025658242404
```

The agreement is within relative/absolute tolerances of `1e-8`. It is measured
against a separate call to `model.predict(row)`. The existing explanation helper's
`prediction` field is itself constructed as baseline plus contributions, so
comparing only with that field would not be an independent check.

Your hands-on checks:

1. Count 14 contribution rows, including month with a zero contribution.
2. Add every signed contribution, then add the baseline. Do not add absolute values.
3. Compare with `raw_prediction`, using full precision rather than plot labels.
4. Check that `trip_distance=15.69` contributes about `+32.118917` dollars and
   `DOLocationID=145` contributes about `-1.148945` dollars in this row.
5. Compare the actual fare separately: additivity explains the model output,
   not why its prediction equals or differs from the observed target.
6. Repeat with `--row 1` and a new output directory. The model identity should
   remain the same; the contribution vector should correspond to the new row.

For demand, repeat using `--problem demand --version 1` and a distinct output.
The reconciliation target is the raw regressor value in pickup-count units.
Online demand inference clips negative outputs to zero; recursive history also
rounds predicted counts to integers. Those are separate downstream operations.

## 3. Distinguish color, sign and global importance

Use the preserved global `fare_shap_summary.png` alongside the new `waterfall.png`.

| View or property | Meaning | What it does not mean |
|---|---|---|
| Beeswarm red/pink vs blue | High vs low input feature value, within that feature | Positive vs negative contribution; good vs bad |
| Beeswarm left vs right of zero | Negative vs positive signed contribution | Low vs high raw input value |
| Waterfall red vs blue | Positive vs negative contribution to this prediction | The beeswarm's high/low input-value color scale |
| Global vertical order / mean absolute SHAP | Average magnitude across the analyzed sample | Contribution direction, causality or this row's ranking |
| One row's signed vector | Decomposition of one output relative to the explainer baseline | A causal intervention or a general accuracy measurement |

The global sample is at most 2,000 test rows with random seed 42. Its mean absolute
SHAP values are nonnegative and do not sum to any one trip's prediction. Numeric
zone IDs are category codes: 145 is not geographically “larger” than 132. Color
on those IDs should not be interpreted as a meaningful geographic gradient.
Correlated distance and duration may share attribution. The TreeExplainer baseline
is not asserted to be the mean of the selected test sample.

Reference: [SHAP beeswarm documentation](https://shap.readthedocs.io/en/stable/example_notebooks/api_examples/plots/beeswarm.html)
and [waterfall documentation](https://shap.readthedocs.io/en/stable/example_notebooks/api_examples/plots/waterfall.html).

## 4. Attach a scoped card to the specific model

The exercise checks the reviewed report's numeric URI and run ID against the
selected registry version, checks the test-file hash, then copies the reviewed
population card and appends a clearly separated single-row reconciliation scope.
It keeps the population metrics and the one-row attribution claims distinct.

To generate a new exercise and attach its evidence to your local MLflow registry:

```powershell
.\.venv\Scripts\python.exe -m scripts.responsible.reconcile_prediction --problem fare --version 1 --row 0 --analysis-dir evidence/2026-10-25/responsible-analysis/reviewed --output artifacts/learner-shap/fare-v1-row0-attached-your-run --attach-card
```

This logs the evidence under a unique `scoped-explanations/fare-v1/` path in the
version's source training run, and adds `scoped_card_uri` plus `scoped_card_sha256`
tags to that exact model version. Repeating attachment creates a new artifact
path and updates the version's pointer; it does not replace the trained model.
The generated `attachment.json` records the precise artifact URI.

Open the local MLflow UI if it is not already running:

```powershell
.\.venv\Scripts\python.exe -m mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000
```

At `http://127.0.0.1:5000`, open Models, `taxi-fare-predictor`, version 1. Confirm
the source run is `431fcbd5c9784409994a95ea11453a87` and inspect the version tags.
Open the source run's artifacts at the tagged path and inspect the scoped card,
full vector, JSON and waterfall. Registry layout labels may vary by MLflow release.
This attachment is local; it does not assert any deployed endpoint uses this model.

A demonstration was already run in `artifacts/learner-shap/fare-v1-row0-demonstration/`.
Its card was retrieved through the tagged URI and its SHA256 verified. Your command
creates separate evidence; it does not overwrite the demonstration.

## 5. Plan the remaining evaluation work

### A. Strict-split demand retraining

1. Freeze version 1 and its existing evidence as the legacy benchmark.
2. Verify all three files in `data/features/strict-hourly-v1/`, including unique
   zone/hour keys, complete hourly grids and strict boundaries. Expected row
   counts are 116,380 / 14,674 / 14,674, with 460 / 58 / 58 whole hours.
3. Load that directory through a separate Config or process-local
   `DATA_FEATURES_DIR` override. Merely running the default training command
   still reads canonical files. Keep fare on its own directory/config.
4. Use a distinct model registry name, such as `taxi-demand-forecaster-strict-hourly`,
   and a distinct artifacts directory. That prevents a new `latest` from changing
   the serving model unintentionally. Set these on a copied Config passed to
   `train_problem`; the current training CLI has no registry-name option.
5. Run one-trial/no-registration smoke training first. Then freeze the tuning
   budget and seed, select by validation only, and train/register the candidate.
   Do not tune repeatedly against the January test score.
6. Compare the old and candidate models on the same evaluation rows for an
   apples-to-apples model comparison. Separately retain each split protocol's
   native metrics; different row sets are not a pure model improvement comparison.
7. Save numeric model URI, source run, parameters, all split hashes, cutoffs,
   feature schema and package versions. Generate responsible reports from the
   same candidate Config and strict directory, rather than default `latest`.

Done when strict assertions pass and a new model/card/report set all identify
the same candidate and data. Improved RMSE is not required to close the split
protocol gap. Timestamp separation does not by itself prove publication latency
or fixed-origin validity.

### B. Fixed-origin multi-hour backtesting

1. Start with a frozen strict-split candidate. Specify forecast origins and
   horizons of 1, 3, 6, 12 and 24 hours before looking at results.
2. At each origin, make a fresh history copy containing only observations strictly
   before that origin. Require the model's fitting/tuning cutoff to precede it.
3. Forecast the next hours recursively using prior predictions. Match production's
   clipping and integer-history rounding policy, and record both raw and served
   outputs. Do not feed the future actuals into later lag/rolling features.
4. Test this contract: perturb every actual count at/after the origin; predictions
   from that origin must not change. Reset history independently at each origin.
5. Join truth only after predictions are complete. Record zone, origin, target
   time, horizon, prediction, actual and exact model identity for every forecast.
6. Score MAE/RMSE by horizon and operational subgroup. Include persistence and
   previous-week same-hour baselines using only information available at origin.
   Keep rolling one-step results separately named.
7. Use comparable horizon coverage and report origin/day counts. Overlapping
   origins are dependent; 58 test hours do not support strong uncertainty claims.
   Use a longer later period for the final backtest and block uncertainty by day
   or origin rather than treating each zone-hour as independent.

Done when the no-future-actuals test passes and the horizon-level comparison is
reproducible. Merely calling the existing batch forecaster without history
truncation and truth alignment is not a validated backtest.

### C. Weekend and holiday coverage

1. Freeze model versions, metrics, subgroup definitions and minimum support before
   obtaining the next evaluation data. Select a future-to-training full-month
   window containing both day types and at least one holiday under this repo's
   `holidays.UnitedStates` definition. February 2024 is a candidate to verify.
2. Keep that window outside all fitting/tuning. For demand, carry January's final
   168 observed hours into feature warm-up, but score only target hours in the
   new window. Do not split each month independently or discard its first week.
3. First run a coverage census: days, hours, zones, trips and holiday dates for
   every subgroup. Check timestamp/timezone conventions and missingness before
   scoring. A missing group remains “insufficient comparison.”
4. Evaluate both frozen model families on that window, with both demand protocols
   explicitly separated. Include weekdays/weekends and holidays/non-holidays.
5. Report row counts AND distinct days/holiday events. Thousands of zone rows on
   one holiday are not thousands of independent holidays. Multiple later holiday
   events are needed before claiming robust holiday generalization.
6. If these results lead to tuning or feature changes, that period becomes
   development evidence. Reserve a later, untouched period for the revised model's
   final evaluation. Predefine new windows with the required calendar coverage.

Done when the report shows actual support for both sides of each intended
comparison, without having trained on the evaluated future period. Broad
seasonal/holiday robustness remains a wider data-collection goal.

Suggested order: strict-split candidate → backtest correctness on January →
freeze protocols → later-period coverage census → untouched later evaluation.
For runnable preflight, smoke-training and isolated candidate-registration commands,
continue with [the strict-demand training walkthrough](STRICT_DEMAND_NEXT_STEPS.md).
No new training, downloads, registrations or deployment changes are performed by
this plan. The only model-registry change in the worked exercise is the scoped
card attachment to the existing version 1.
