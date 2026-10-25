# Chapter 10: serve predictions and generate batch forecasts

Evidence from the learner's local execution on 25 October 2026 (IST).
`learner-console.txt` is the original pasted transcript, copied unchanged.
The three PNG files are the learner's original screenshots, copied unchanged.
No requests were rerun to reconstruct these results.

## Observed results

| Check | Observed result | Source |
| --- | --- | --- |
| Health | status ok; both models loaded; 744 history hours; 253 zones | health.png |
| Fare without duration | 20.16; duration_estimated true | fare-estimated-duration.png |
| Single demand | zone 132, 2024-01-31 20:00, 224.07 pickups | single-demand.png |
| Recursive API forecast | zone 132; 3 hours; model_reference latest | learner-console.txt |
| Batch generation | 759 rows; 253 zones; 3 hours | learner-console.txt |
| SQLite readback | 2024-02-01 00:00 through 02:00; 759 rows | learner-console.txt and batch-forecast.csv |

The learner also reported a fare of 18.63 with duration_estimated false for
3.2 miles, one passenger, pickup 161, dropoff 236, pickup datetime
2024-01-20T10:00:00 and supplied duration 18 minutes. Changing distance to -1
returned a validation body with type greater_than and message
Input should be greater than 0. These two results were pasted directly into the
chat, rather than supplied in the retained console attachment. The status code
was not captured in that paste; 422 is the expected schema-validation status.

## Recursive API response

Request: horizon_hours 3, zones [132], with start_hour omitted.
Request ID: 73969833-27be-4799-8bf5-ff37ef80aea3.

| Pickup hour | Predicted pickups |
| --- | ---: |
| 2024-02-01 00:00 | 133.52 |
| 2024-02-01 01:00 | 14.39 |
| 2024-02-01 02:00 | 7.54 |

Default origin is the hour after the latest saved observation, rather than the
current wall-clock hour. Recursive feature history consumes integer-rounded
predictions, while output retains fractional predictions. API values are rounded
to two decimals, so they do not preserve every digit of the internal prediction.

## Persisted output and verification

Command: `.\.venv\Scripts\python.exe -m scripts.batch_forecast --horizon 3`.
Generation: 2026-10-25T03:54:33.544219+00:00 (UTC).
The batch CLI wrote to the ignored local predictions.db database.
`batch-forecast.csv` exports only this generation, read directly from that database
in read-only mode during evidence preservation. Checks passed for 759 rows,
253 zones, exactly three consecutive hours, and unique zone/hour keys.

The API uses the already-loaded service; the CLI independently loads registry
models. Both report a mutable latest reference. Exact loaded numeric model
versions and source run IDs were not captured for these executions. No identity
match between API and CLI models is asserted. Resolving latest now would not
prove which models were loaded at the time.

## Interpretation and limits

This evidence establishes local inference, negative-input rejection, recursive
forecast generation and SQLite persistence. It does not establish forecast
accuracy, cloud deployment, or a fixed-origin backtest against February actuals.
The repeated feature-table INFO messages and MLflow deprecation warning did not
prevent the captured batch run from completing.

Saved observed history, the single-demand result cache, per-zone temporary
recursive history, and persisted SQLite forecasts have different roles. Forecasts
are not observed counts; cache entries do not update observed history. SQLite
writes append generations, so consumers must select a generation explicitly.

The database, model bundles and training data are excluded. `manifest.json`
records SHA256 hashes of the preserved files; hashes establish file integrity,
not an independent replay of the learner's execution.
