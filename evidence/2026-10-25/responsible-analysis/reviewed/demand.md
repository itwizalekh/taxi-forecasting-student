# Model Card — taxi-demand-forecaster

_Generated: 2026-10-24 19:01 UTC_

## Model details

- **Problem:** demand
- **Algorithm:** LGBMRegressor
- **Target:** `pickup_count`
- **Registry version:** 1
- **Training run ID:** `771eb4d4470f4da9ab8467568f9a8f34`
- **Evaluated model:** `models:/taxi-demand-forecaster/1`

## Intended use

Historical hourly pickup-count forecasting for fleet-planning research.

## Evaluation — overall (test split)

| Metric | Value |
|--------|-------|
| rmse | 8.7022 |
| mae | 2.5350 |
| mape | 40.1919 |
| r2 | 0.9707 |

- Configured data period: 2024-01.
- Test period: 2024-01-29 14:00:00 to 2024-01-31 23:00:00; 14,573 rows. Stored timestamps are used without timezone conversion.
- Strict timestamp separation across train/validation/test: False.
- SHA256 hashes of evaluated splits and the zone lookup are recorded in the fairness JSON; these identify current evaluation inputs, not proof of original training-data identity.
- Training trials per estimator recorded by MLflow: 1.
- SHAP uses up to 2,000 test rows, sampled with random_state=42; it is explanatory, not causal.
- Raw RMSE disparity depends on target scale and sample coverage; flags warrant investigation, not a demographic-discrimination conclusion. Groups smaller than 30 rows are omitted. MAPE excludes near-zero targets and can be large for small nonzero targets.
- Demand evaluation uses historical lag features and supports a rolling one-step interpretation; later test rows use earlier actual counts. Fixed-origin multi-hour accuracy is not established.
- The registered model is evaluated on the configured canonical splits; the separate strict-hour audit does not alter this run. Retraining on strict splits remains a separate experiment.

## Evaluation — subgroup fairness

### By borough

Disparity ratio (worst/best RMSE): **218.50** (threshold 1.5) — ⚠️ **flagged**. Worst: `Manhattan`, best: `Staten Island`.

| Group | n | RMSE | MAE | MAPE |
|-------|---|------|-----|------|
| Manhattan | 3862 | 15.551 | 7.713 | 29.69 |
| Queens | 3971 | 6.466 | 1.190 | 52.64 |
| Unknown | 116 | 3.181 | 1.991 | 47.47 |
| Brooklyn | 3457 | 0.741 | 0.441 | 53.93 |
| Bronx | 2476 | 0.441 | 0.260 | 64.57 |
| EWR | 58 | 0.267 | 0.093 | 97.02 |
| Staten Island | 633 | 0.071 | 0.043 | 91.09 |

### By time_of_day

Disparity ratio (worst/best RMSE): **2.60** (threshold 1.5) — ⚠️ **flagged**. Worst: `evening`, best: `overnight`.

| Group | n | RMSE | MAE | MAPE |
|-------|---|------|-----|------|
| evening | 4554 | 11.823 | 3.365 | 37.30 |
| afternoon | 3947 | 8.527 | 2.946 | 36.29 |
| morning | 3036 | 6.218 | 2.361 | 39.05 |
| overnight | 3036 | 4.542 | 0.930 | 57.55 |

### By day_type

**Insufficient comparison:** fewer than two groups have positive, finite RMSE. No parity conclusion is available; a zero denominator also prevents this ratio from being assessed.

| Group | n | RMSE | MAE | MAPE |
|-------|---|------|-----|------|
| weekday | 14573 | 8.702 | 2.535 | 40.19 |

### By holiday

**Insufficient comparison:** fewer than two groups have positive, finite RMSE. No parity conclusion is available; a zero denominator also prevents this ratio from being assessed.

| Group | n | RMSE | MAE | MAPE |
|-------|---|------|-----|------|
| non-holiday | 14573 | 8.702 | 2.535 | 40.19 |

### By airport

Disparity ratio (worst/best RMSE): **4.63** (threshold 1.5) — ⚠️ **flagged**. Worst: `airport`, best: `non-airport`.

| Group | n | RMSE | MAE | MAPE |
|-------|---|------|-----|------|
| airport | 116 | 37.377 | 26.392 | 38.08 |
| non-airport | 14457 | 8.070 | 2.344 | 40.24 |

## Top features (SHAP)

| Feature | Mean absolute SHAP value |
|---------|-----------|
| lag_1 | 12.5161 |
| lag_168 | 7.9227 |
| lag_24 | 3.9744 |
| rolling_mean_3 | 0.9312 |
| hour_cos | 0.6129 |
| rolling_std_24 | 0.4443 |
| lag_3 | 0.4159 |
| rolling_std_3 | 0.3890 |
| hour | 0.3786 |
| lag_2 | 0.3481 |

## Limitations

- Trained on a single month of NYC Yellow Taxi data; may not generalise to other periods, boroughs served sparsely, or green/for-hire vehicles.
- Predictions degrade under distribution shift (see drift monitoring).

## Ethical considerations

- No demographic or protected attributes are used or available; fairness is assessed as geographic/temporal service equity, not demographic parity.
- Large borough-level disparities could translate into unequal service quality across neighbourhoods and should be monitored.
