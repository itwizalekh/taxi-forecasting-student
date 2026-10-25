# Reflection: Chapter 10 Serving and Forecast Evidence

## Matched-origin metrics: synthetic illustration, not live model accuracy

The matched-origin metrics were computed from an author-provided synthetic
illustration, not from the registered TLC model or the local API/batch run. Its
sidecar records 48 rows (2 zones by 24 hours) and labels the scope
`author synthetic illustration`.

All three methods were scored on those same 48 rows:

| Method | MAE | RMSE |
| --- | ---: | ---: |
| One-step | 2.627336 | 3.606758 |
| Recursive | 2.816925 | 3.965443 |
| `lag_24` | 3.437500 | 4.697074 |

On this illustration, one-step RMSE is about 0.358685 pickups lower than
recursive RMSE. This is an observed result for these rows, not a universal
ranking. One-step prediction can use an actual once its hour has completed;
recursive prediction at a fixed origin must feed its earlier predictions into
later steps. `lag_24` uses the previous day's count for the same zone and hour.

These synthetic scores are distinct from the live local execution below. The
API and batch artifacts establish that inference ran and output was returned or
persisted; they do not compare those forecasts to matching future actuals.
Therefore, this evidence does not establish live model accuracy.

## Fare validation boundary and retest

The captured invalid fare request changed `trip_distance` to `-1` while keeping
the other fields the same as the captured valid fare request (`3.2`). The
invalid request returned HTTP **422** with a Pydantic `greater_than` error:
`trip_distance` must be greater than zero. Its response header retained request
ID `1d69833e-6e63-4cf7-9e21-2baa0b358bf4`.

This failure occurs at request-schema validation, before the `/predict/fare`
handler calls fare feature construction or model prediction. The captured API
log records status 422 for that request and has no fare-feature-construction or
prediction event for it. By contrast, the valid request returned HTTP **200**
with predicted fare `18.63` and request ID
`912bc8f0-3b1b-4548-ad52-33ee054fcce4`.

The paired request artifacts are useful because only distance differs. For any
retest, change only that invalid field to a valid positive distance and retain
the new response status, body, and request ID; do not infer that downstream
feature construction was exercised by the 422 response.

## The four stores and the role of the cache

1. **Saved hourly demand history** contains observed, accepted pickup counts
   loaded from `demand_hourly.parquet`. It is a persisted historical snapshot,
   not a stream of newly arriving observations.
2. **`ModelService` single-demand result cache** stores predictions in the
   running process, keyed by zone and floored target hour. A cache hit reuses a
   previous result; it does not add an observed count to history or provide new
   observations. It is not durable and is lost when the process restarts.
3. **Batch per-zone temporary history** begins with saved observations and
   appends that zone's rounded predictions as the recursive batch proceeds.
   This lets later forecast steps build features without claiming those
   predictions are actual observations.
4. **SQLite `demand_forecasts`** persists generated forecast rows by generation.
   It stores outputs, not new observations, and appends rather than replacing a
   single canonical latest table.

These stores have different purposes. In particular, a prediction cache is
neither a substitute for refreshing observed history nor the recursive state
used by the batch forecast.

## Fixed-origin forecasts and accuracy limits

A fixed-origin forecast is issued using information available at one origin.
For a third forecast hour, the first and second forecasted values may be used
as inputs: they are predictions generated after the origin, not observations.
Actual counts from those later hours must not be used as inputs because they
were unknown when the forecast was issued. They may be retained separately and
compared with predictions afterward for evaluation.

The captured local API returned a three-hour recursive forecast for zone 132,
starting at the hour after saved history ended:

| Hour | Predicted pickups |
| --- | ---: |
| 2024-02-01 00:00 | 133.52 |
| 2024-02-01 01:00 | 14.39 |
| 2024-02-01 02:00 | 7.54 |

The local batch run likewise generated predictions for three future hours. The
evidence contains no matching observed future counts or scoring for these
outputs. Thus, successful recursive generation proves execution and
persistence, not forecast accuracy.

## Local API and batch completion, with lineage

The captured local API run completed its readiness and inference checks:

- `/health` returned HTTP 200, `status: ok`, both models loaded, 744 history
  hours and 253 zones. Request ID:
  `119639dc-1c2b-4521-821d-8197d2b0403d`.
- Valid `/predict/fare` returned HTTP 200 and `predicted_fare: 18.63`.
- Invalid `/predict/fare` returned HTTP 422 at schema validation, as described
  above.
- `/predict/demand` returned HTTP 200 for zone 132 at 2024-02-01 00:00 with
  `predicted_pickups: 133.52`. Request ID:
  `9dd76e89-1ffc-457c-9678-739ce5c36595`.
- `/forecast/demand` returned HTTP 200 for zone 132 over three hours, with
  model reference `1` and request ID
  `5f2c2786-3bdd-42bb-b22e-6a3760214847`.

The follow-up sidecar links that new pinned local execution to:

- **Code revision:** `61ea01cb4bc5961c2f5ecd66ae87377c3217d327`.
- **Demand model:** `models:/taxi-demand-forecaster/1`, run
  `771eb4d4470f4da9ab8467568f9a8f34`,
  source `file:///C:/Data/BITS/labs/taxi-forecasting-student/mlruns/2/771eb4d4470f4da9ab8467568f9a8f34/artifacts/model`.
- **Fare model:** `models:/taxi-fare-predictor/1`, run
  `431fcbd5c9784409994a95ea11453a87`,
  source `file:///C:/Data/BITS/labs/taxi-forecasting-student/mlruns/1/431fcbd5c9784409994a95ea11453a87/artifacts/model`.
- **Observed demand history:** `data/processed/demand_hourly.parquet`,
  SHA-256
  `da21702e6ba7a6d9eeff70e78b106347cd140a8734ae2aca831abc9431f21c66`.
- **Configuration:** `config/config.yaml`, SHA-256
  `19f22fcb1863997d85c353118bc43babddacd1753064d59850b62dcdef88df2f`.
- **Batch generation:** `predictions.db`, table `demand_forecasts`,
  `generated_at=2026-10-25T07:01:12.370071+00:00` (UTC), with 759 rows,
  253 zones and hours 2024-02-01 00:00 through 02:00. The rows are preserved
  in `batch-forecast.csv`.

The SQLite `model_version` column for this batch generation contains `latest`
because the writer defaults to that label. The sidecar separately resolves
this new run to numeric demand model version 1 and its run ID above. Do not
interpret the mutable `latest` label as a precise historical model identity,
or apply this new pinned lineage to earlier generations.

## Chapter 11 and Chapter 12 status

- **Chapter 11 — container work: Pending / not evidenced here.** The inspected
  follow-up evidence contains local API and batch artifacts but no Chapter 11
  image build, container runtime, or container-specific validation evidence.
  Local API success is not container completion.
- **Chapter 12 — hosted delivery: Pending / not evidenced here.** No hosted
  deployment or hosted runtime evidence is present in the inspected evidence
  folders. Localhost requests and a local SQLite batch generation do not
  establish hosted delivery.

