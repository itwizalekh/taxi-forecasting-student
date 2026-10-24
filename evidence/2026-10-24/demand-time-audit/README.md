# Demand time-boundary and past-only feature audit

Executed 24 October 2026 against the actual locally generated January 2024 demand files. This is an author-assisted audit, not independent learner code or a model-accuracy result. Machine-readable evidence is in [audit.json](audit.json). The recorded Git HEAD is the starting commit; source changes were uncommitted during execution and their exact SHA256 hashes are recorded.

## Step 1 — Inspect the existing boundaries

Read the three canonical `data/features/demand_{train,val,test}.parquet` files. Find each split's minimum and maximum `pickup_hour`, then inspect all rows at each adjacent boundary. [Original boundary rows](original-boundary-rows.csv) contain the actual zone IDs, target counts and feature values, with split and boundary labels.

| Original boundary | Earlier split rows at that hour | Later split rows at that hour |
|---|---:|---:|
| Jan 27, 04:00, train/validation | 202 | 51 |
| Jan 29, 14:00, validation/test | 101 | 152 |

Each total is 253 zones. Distinct zone/hour keys were unique; the issue was a shared timestamp, not duplicated target rows. Original row slicing sorts chronologically but divides tied timestamps.

## Step 2 — Split unique timestamps instead of rows

The additive `src.data.splits.timestamp_group_split` helper sorts distinct timestamps and applies 80%/10%/remaining proportions to their count. It rejects missing times, invalid fractions and insufficient periods. Every row is then assigned by timestamp ranges. The original `time_based_split` helper and default pipeline behavior are unchanged.

There are 576 eligible hours after warm-up. Thus:

```text
Training hours = floor(576 × 0.8) = 460
Train + validation hours = floor(576 × 0.9) = 518
Validation hours = 518 − 460 = 58
Test hours = 576 − 518 = 58
```

| New split | Hours | Rows | First hour | Last hour |
|---|---:|---:|---|---|
| Train | 460 | 116,380 | Jan 8, 00:00 | Jan 27, 03:00 |
| Validation | 58 | 14,674 | Jan 27, 04:00 | Jan 29, 13:00 |
| Test | 58 | 14,674 | Jan 29, 14:00 | Jan 31, 23:00 |

All dates are January 2024, using stored timestamps without timezone conversion. Strict assertions passed:

```python
assert train.pickup_hour.max() < val.pickup_hour.min()
assert val.pickup_hour.max() < test.pickup_hour.min()
```

All 145,728 feature rows are preserved exactly, and every hour has 253 rows in precisely one split. No rows were discarded to obtain separation. Fractions are approximate due to whole-hour rounding; unequal zone coverage would also make row fractions differ from time fractions.

New Parquet files are in `data/features/strict-hourly-v1/`, which remains Git-ignored. The original feature and split files were not overwritten. [Strict boundary rows](strict-boundary-rows.csv) show the last complete earlier hour and first complete later hour at each boundary.

**Important:** Existing training commands still read canonical files in `data/features/`; they do not automatically use these new splits. Select this separate directory through a deliberate training configuration change before claiming a model was evaluated using strict splits. Such training was not performed here.

## Step 3 — Reconstruct all lag and rolling features independently

First verify unique zone/hour keys and exactly one-hour increments within each zone. This is necessary because a lag of one row represents one hour only when the series is hourly and complete.

For each zone and feature-ready target at position `i`, independently compare:

```python
lag_k = counts[i-k]
rolling_mean_w = mean(counts[i-w:i])
rolling_std_w = std(counts[i-w:i], ddof=1)
```

Python's upper slice endpoint is excluded: `counts[i-w:i]` ends at `i-1`, so it does not include the target at `i`. The reconstruction uses NumPy array windows rather than reusing the production `groupby.shift/rolling` calculation.

Checked all five lags (1, 2, 3, 24, 168) and rolling means/stds for 3, 24 and 168 hours across **145,728 rows and 253 zones**. All lags and means matched exactly. Maximum standard-deviation discrepancy was about `2.88e-10`, within the `1e-7` absolute / `1e-9` relative tolerances. The std uses sample normalization (`ddof=1`). Full feature regeneration also matched the persisted feature table.

### An actual zone example

For zone 132 at the target hour **Jan 27, 04:00**, the preceding counts were:

| Source hour | Pickup count |
|---|---:|
| 01:00 | 28 |
| 02:00 | 8 |
| 03:00 | 6 |

```text
lag_1 = 6
rolling_mean_3 = (28 + 8 + 6)/3 = 14
rolling_std_3 = sqrt(((28−14)² + (8−14)² + (6−14)²)/(3−1))
              = sqrt(148) ≈ 12.165525
```

The Jan 27 04:00 target count is excluded from these inputs. The 168-hour lag explains why the first retained feature hour is Jan 8, although Jan 1–7 remain available as historical context.

## Step 4 — Change future targets and check what responds

In memory only, add 10,000 to zone 132's target counts at and after Jan 27, 04:00, then regenerate features. The stored data is not modified.

Results:

- All predictors through the origin were unchanged, including predictors at the origin itself.
- All other zones' predictors were unchanged, including later hours.
- Later predictors in the changed zone did change, showing that the test intervention reached the historical calculations.

This experiment reinforces the independent all-row reconstruction. It tests the chosen zone/origin; it does not enumerate every possible perturbation.

## Step 5 — Reproduce and verify

From `C:\Data\BITS\labs\taxi-forecasting-student`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_splits.py tests/unit/test_timestamp_group_split.py -q

.\.venv\Scripts\python.exe -m scripts.audit_demand_time --output evidence/2026-10-24/demand-time-audit-repeat --strict-dir data/features/strict-hourly-v2
```

The first audit has already been performed. A repeat requires new output paths; the script refuses to overwrite existing directories. Focused tests: **9 passed**, including unequal timestamp-group sizes, row conservation and rejected invalid inputs. Full local CI: **Ruff passed, 127 tests passed, coverage 94.72%, one existing multipart deprecation warning; Terraform skipped**. Results are recorded in [local-ci.txt](local-ci.txt).

## What these checks establish and what remains

The features use earlier counts from their own zone, and the new partitions have strictly separated hourly timestamps. This supports **rolling one-step evaluation**, where completed previous hours become available before the next prediction. It does not establish a fixed-origin multi-hour forecast: features for later test hours currently use earlier actual test counts. For that claim, use recursive predicted history or an explicit horizon-specific evaluation.

Publication/ingestion latency, source completeness, the pre-fit model's availability at a given origin, and performance quality require separate evidence. No models were trained, no metrics were improved by this audit, and no held-out target values were used to select a model. Ordinary historical context crossing a split boundary is legitimate when it would be available at prediction time; current/future targets are not.
