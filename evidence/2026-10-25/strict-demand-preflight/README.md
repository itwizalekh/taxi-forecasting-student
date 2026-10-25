# Strict-hour demand preflight — 25 October 2026 (IST)

Executed:

```powershell
.\.venv\Scripts\python.exe -m scripts.train_strict_demand --mode check --output artifacts/strict-demand/preflight-2026-10-25
```

Result: **passed**. No model was trained or registered. The checked-in
`preflight.json` is copied from the actual command output and includes the exact
three input hashes and 20-column model feature schema.

| Split | Rows | Hours | Zones | First target | Last target |
|---|---:|---:|---:|---|---|
| Train | 116,380 | 460 | 253 | 2024-01-08 00:00 | 2024-01-27 03:00 |
| Validation | 14,674 | 58 | 253 | 2024-01-27 04:00 | 2024-01-29 13:00 |
| Test | 14,674 | 58 | 253 | 2024-01-29 14:00 | 2024-01-31 23:00 |

Checks: nonempty periods; unique, nonmissing zone/hour keys; hour alignment;
identical feature order and zone sets; complete hourly grids; strictly separated
time boundaries; one-hour increments between the last earlier hour and first
later hour. Total feature rows: 145,728. Data remain Git-ignored.

These structural checks complement the earlier all-row past-only-feature audit;
they do not independently reconstruct features, validate arrival latency or
measure forecast accuracy. Whole-hour separation is not a fixed-origin backtest.
The candidate training runner is prepared but its actual training modes have
not been executed. Five offline tests cover validation, rejection of overlapping
or incomplete splits, config isolation and mocked smoke-mode dispatch.

Continue with [the next-steps guide](../../../docs/STRICT_DEMAND_NEXT_STEPS.md).
