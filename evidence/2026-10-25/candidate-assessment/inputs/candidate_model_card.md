# Model Card — taxi-demand-forecaster-strict-hourly

_Generated: 2026-10-25 02:34 UTC_

## Model details

- **Problem:** demand
- **Algorithm:** XGBRegressor
- **Target:** `pickup_count`
- **Registry version:** 1
- **Training run ID:** `2f79615caca841f2b44b7627c4de5a96`
- **Evaluated model:** `models:/taxi-demand-forecaster-strict-hourly/1`

## Intended use

Historical hourly pickup-count forecasting for fleet-planning research.

## Evaluation — overall (test split)

| Metric | Value |
|--------|-------|
| rmse | 8.6842 |
| mae | 2.5208 |
| mape | 40.2072 |
| r2 | 0.9707 |

- Configured data period: 2024-01.
- Test period: 2024-01-29 14:00:00 to 2024-01-31 23:00:00; 14,674 rows. Stored timestamps are used without timezone conversion.
- Strict timestamp separation across train/validation/test: True.
- SHA256 hashes of evaluated splits and the zone lookup are recorded in the fairness JSON; these identify current evaluation inputs, not proof of original training-data identity.
- Training trials per estimator recorded by MLflow: 25.
- SHAP uses up to 2,000 test rows, sampled with random_state=42; it is explanatory, not causal.
- Raw RMSE disparity depends on target scale and sample coverage; flags warrant investigation, not a demographic-discrimination conclusion. Groups smaller than 30 rows are omitted. MAPE excludes near-zero targets and can be large for small nonzero targets.
- Demand evaluation uses historical lag features and supports a rolling one-step interpretation; later test rows use earlier actual counts. Fixed-origin multi-hour accuracy is not established.
- The registered model is evaluated on configured splits with strictly separated timestamps; this does not establish fixed-origin multi-hour accuracy.

## Evaluation — subgroup fairness

### By borough

Disparity ratio (worst/best RMSE): **197.26** (threshold 1.5) — ⚠️ **flagged**. Worst: `Manhattan`, best: `Staten Island`.

| Group | n | RMSE | MAE | MAPE |
|-------|---|------|-----|------|
| Manhattan | 3886 | 15.759 | 7.675 | 29.70 |
| Queens | 4002 | 5.869 | 1.164 | 52.36 |
| Unknown | 116 | 3.277 | 2.007 | 46.73 |
| Brooklyn | 3480 | 0.741 | 0.449 | 53.91 |
| Bronx | 2494 | 0.443 | 0.270 | 65.12 |
| EWR | 58 | 0.270 | 0.104 | 97.16 |
| Staten Island | 638 | 0.080 | 0.053 | 91.65 |

### By time_of_day

Disparity ratio (worst/best RMSE): **2.59** (threshold 1.5) — ⚠️ **flagged**. Worst: `evening`, best: `overnight`.

| Group | n | RMSE | MAE | MAPE |
|-------|---|------|-----|------|
| evening | 4554 | 11.965 | 3.346 | 36.84 |
| afternoon | 4048 | 8.301 | 2.927 | 36.58 |
| morning | 3036 | 6.045 | 2.315 | 39.63 |
| overnight | 3036 | 4.622 | 0.946 | 56.91 |

### By day_type

**Insufficient comparison:** fewer than two groups have positive, finite RMSE. No parity conclusion is available; a zero denominator also prevents this ratio from being assessed.

| Group | n | RMSE | MAE | MAPE |
|-------|---|------|-----|------|
| weekday | 14674 | 8.684 | 2.521 | 40.21 |

### By holiday

**Insufficient comparison:** fewer than two groups have positive, finite RMSE. No parity conclusion is available; a zero denominator also prevents this ratio from being assessed.

| Group | n | RMSE | MAE | MAPE |
|-------|---|------|-----|------|
| non-holiday | 14674 | 8.684 | 2.521 | 40.21 |

### By airport

Disparity ratio (worst/best RMSE): **4.14** (threshold 1.5) — ⚠️ **flagged**. Worst: `airport`, best: `non-airport`.

| Group | n | RMSE | MAE | MAPE |
|-------|---|------|-----|------|
| airport | 116 | 33.870 | 25.135 | 33.79 |
| non-airport | 14558 | 8.178 | 2.341 | 40.34 |

## Top features (SHAP)

| Feature | Mean absolute SHAP value |
|---------|-----------|
| lag_1 | 11.2002 |
| lag_168 | 7.9861 |
| lag_24 | 4.4064 |
| rolling_mean_3 | 1.1733 |
| hour_cos | 0.7140 |
| lag_2 | 0.5365 |
| lag_3 | 0.4363 |
| rolling_mean_168 | 0.3070 |
| rolling_std_3 | 0.2843 |
| hour | 0.2735 |

## Limitations

- Trained on a single month of NYC Yellow Taxi data; may not generalise to other periods, boroughs served sparsely, or green/for-hire vehicles.
- Predictions degrade under distribution shift (see drift monitoring).

## Ethical considerations

- No demographic or protected attributes are used or available; fairness is assessed as geographic/temporal service equity, not demographic parity.
- Large borough-level disparities could translate into unequal service quality across neighbourhoods and should be monitored.
