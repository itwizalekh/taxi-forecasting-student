# Next evaluation: train a demand candidate with whole-hour splits

For hourly demand, a strict split keeps every zone at the same hour in one
partition, with `max(train time) < min(validation time)` and
`max(validation time) < min(test time)`. The hour-aligned timestamp is the split
key; merely displaying timestamps with `:00` does not make a split strict.
There is no requirement to leave an empty hour between adjacent partitions.

The preflight on 25 October 2026 passed on `data/features/strict-hourly-v1/`:

| Split | Complete hours | Rows | First target hour | Last target hour |
|---|---:|---:|---|---|
| Train | 460 | 116,380 | Jan 8 00:00 | Jan 27 03:00 |
| Validation | 58 | 14,674 | Jan 27 04:00 | Jan 29 13:00 |
| Test | 58 | 14,674 | Jan 29 14:00 | Jan 31 23:00 |

Dates are January 2024 as stored, without timezone conversion. Every included
hour has 253 zones. No hours or keys overlap; the complete grid is contiguous.
The old canonical row slices divided the Jan 27 04:00 and Jan 29 14:00 hours.
Earlier actual counts may legitimately supply historical lag context across a
boundary when available at prediction time; that is different from scoring the
same target hour across partitions.

## Step 1 — Check your existing files

Run from `C:\Data\BITS\labs\taxi-forecasting-student`:

```powershell
.\.venv\Scripts\python.exe -m scripts.train_strict_demand --mode check --output artifacts/strict-demand/preflight-your-run
```

Expected result: the table above, 20 feature names, split SHA256 hashes, and
`Preflight passed. No model trained or registered.` The runner rejects shared
timestamps, duplicate zone/hour keys, missing keys, inconsistent schemas or zone
sets, incomplete hourly grids and gaps. It does not audit publication latency or
independently rebuild the feature values; the earlier demand audit covers lag
construction on these January files.

All output paths must be new. A failed check must be resolved before training.
The command does not change canonical data or configuration.

## Step 2 — Run one-trial smoke training

```powershell
.\.venv\Scripts\python.exe -m scripts.train_strict_demand --mode smoke --output artifacts/strict-demand/smoke-your-run
```

This reads only the separate strict-hour files, trains both configured estimators
with one trial each, and logs them under experiment `taxi-demand-strict-hourly`.
It writes `preflight.json`, `training_summary.json` and model-card/SHAP outputs
under that output folder. It does not register a candidate.

Inspect `training_summary.json`: training/validation/test counts must match the
table; the winner must be selected by validation RMSE. A smoke pass demonstrates
execution, not a tuned or improved model. The January test has already been
examined, so any displayed test metrics are diagnostic.

## Step 3 — Fix a tuning budget, then train and register

Use the existing configured default budget of 25 trials per estimator if it fits
your local runtime. Choose the budget before inspecting candidate test results.

```powershell
.\.venv\Scripts\python.exe -m scripts.train_strict_demand --mode train --n-trials 25 --register --output artifacts/strict-demand/candidate-your-run
```

The candidate registry name is **`taxi-demand-forecaster-strict-hourly`**.
The original **`taxi-demand-forecaster` version 1** and its `latest` selector stay
separate. The printed candidate version is authoritative; do not assume it is 1
if you have registered candidates before. The runner operates on a copied Config;
it does not change `config/config.yaml`, the API's configuration, or canonical
feature Parquet files. Never change the API's model name merely to run this lab.

On registration, the runner also evaluates that exact numeric candidate against
the strict data and generates:

```text
candidate-your-run/
  preflight.json
  training_summary.json
  model_artifacts/demand/...
  responsible/model_cards/demand.md
  responsible/artifacts/demand_fairness.json
  responsible/artifacts/demand_shap_summary.png
```

Those responsible outputs are attached to the winning source run under
`strict-evaluation/responsible/`. Check that the candidate name, numeric version,
training run, strict input hashes and `strict_timestamp_separation: true` agree.
The existing default `run_analysis` command still uses the original configuration;
do not substitute its outputs for this candidate's reports.

The runner is preflight-tested and its dispatch is covered with mocked training.
Real smoke and tuned training are the hands-on next actions; they were not run
when these instructions were prepared.

## Step 4 — Assess the candidate before claiming improvement

- Compare old and candidate predictions on the SAME zone/hour evaluation rows.
  Separately report results from their native protocols, whose row counts differ.
- Keep January results labelled diagnostic. Do not repeatedly tune against them.
- The strict test still has only 58 hours and no weekend or holiday coverage.
- Continue with fixed-origin recursive backtesting at 1/3/6/12/24 hours. At each
  origin, truncate actual history strictly before the origin and prove that
  perturbing future actuals cannot affect predictions. Match serving clipping
  and integer-history rounding; compare persistence and weekly baselines.
- Freeze the model and protocol before evaluating a later full month containing
  both day types and holidays under the repository's holiday definition. Count
  distinct holiday dates as well as rows. If results prompt tuning, reserve a
  further untouched period for final evaluation.

Strict time splitting closes the shared-hour boundary gap. It does not close
multi-hour backtesting, data-arrival latency, holiday coverage or seasonal
generalization gaps by itself.
