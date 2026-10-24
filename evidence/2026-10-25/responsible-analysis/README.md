# Responsible-analysis evidence — 25 October 2026 (IST)

This snapshot preserves the author's original local analysis and a reviewed rerun
of the same registered LightGBM models on the same canonical test splits.
It is completed evidence of that historical evaluation, not production approval
or evidence that the known model-quality and evaluation limits have been resolved.

## Contents and identity

- `original/`: exact copies of the cards, fairness JSON and SHAP images produced
  around 00:21–00:22 IST, before reporting changes. These original cards retain
  the missing version and misleading single-group “ok” labels for provenance only.
- `reviewed/`: regenerated cards, fairness JSON and SHAP images, around
  00:31–00:32 IST. Use these for interpretation; the current cards also live in
  `docs/model_cards/`.
- `manifest.json`: SHA256 hashes for preserved outputs and relevant source files,
  local model artifact files, runtime package versions and the starting Git commit.
  Source hashes describe working-copy bytes during this rerun; the manifest was
  assembled before the new commit. It does not contain datasets or model bundles.
- `validation.txt`: checks performed and their limits.

| Model | Numeric registry version | Training run ID | Test rows | RMSE |
|---|---|---|---:|---:|
| taxi-demand-forecaster | 1 | 771eb4d4470f4da9ab8467568f9a8f34 | 14,573 | 8.7022 |
| taxi-fare-predictor | 1 | 431fcbd5c9784409994a95ea11453a87 | 272,735 | 3.4717 |

Version numbers and run IDs refer to the author's local MLflow store. Resolving
`latest` once and loading the numeric URI avoids selector drift during analysis.
The source manifest fingerprints the available local model files as additional
identity evidence; model availability elsewhere is not implied.
Both runs record one tuning trial per estimator. The configured default of 25
does not describe these runs. Current input hashes identify the evaluated data,
not independently verified provenance of the original training inputs.

## Findings and reporting gaps closed

Both models retain three flagged dimensions at a worst/best RMSE threshold of 1.5:

| Dimension | Demand ratio | Fare ratio |
|---|---:|---:|
| Borough | 218.50 | 8.12 |
| Time of day | 2.60 | 1.84 |
| Airport/non-airport | 4.63 | 2.54 |

Single-group comparisons now have `status: insufficient_comparison` and a null
disparity ratio in JSON, rather than implying parity. This affects demand day type
and both models' holiday slices. The dashboard handles the new null values.
The cards record the resolved numeric model URI and training run ID. JSON also
records split periods, hashes, training parameters and generation time. The SHAP
heading renders as a two-column Markdown table. Both SHAP images were visually
inspected; axis and feature labels are readable.

Absolute RMSE differs with target scale and coverage: the demand borough ratio
compares Manhattan RMSE 15.551 against Staten Island RMSE 0.071. It cannot by
itself establish discrimination or relative accuracy. Groups below 30 rows are
omitted. MAPE excludes near-zero targets, and small nonzero targets can inflate it.
These are geographic/temporal error slices, not demographic fairness measurements.

## Remaining evaluation limits and next experiments

1. Demand train/validation and validation/test share boundary hours in the canonical
   splits. The separate strict-hour audit did not retrain these models. To evaluate
   a strict split, retrain and register a new demand version on a separately
   configured strict-split directory, then generate a separate evidence snapshot.
   Do not relabel the metrics here as strict-split performance.
2. Demand features use preceding actual counts. This is rolling one-step evidence;
   fixed-origin multi-hour accuracy requires a separate recursive backtest.
3. Fare split timestamps are strictly separated in this run, but observed trip
   distance and duration do not establish pre-trip estimation quality. Use
   information available at the intended prediction time for that experiment.
4. The January 2024 test windows do not provide holiday comparisons; demand also
   has no weekend comparison. Add genuinely held-out periods with those groups
   before making parity claims. Do not enlarge a test set already used for model
   selection or repeatedly tune against these reports.
5. Investigate airport errors, missing-zone labels, target-scale differences and
   rare/low-fare trips. Compare naive baselines and scale-aware errors by subgroup
   with uncertainty estimates before drawing service-quality conclusions.

No retraining, new registration, or claims of improved model quality are part of
this snapshot. The original evidence is retained alongside the corrected reports.

## Reproduce locally

Requires the matching data, model artifacts and local MLflow registry, which are
intentionally excluded from Git. Preserve existing outputs before regenerating.

```powershell
.\.venv\Scripts\python.exe -m scripts.responsible.run_analysis
.\.venv\Scripts\python.exe -m pytest --cov=src --cov-report=term-missing
.\.venv\Scripts\python.exe -m ruff check scripts/responsible/run_analysis.py src/responsible/fairness.py src/responsible/model_card.py tests/unit/test_responsible.py dashboard/sections.py
```

Generation timestamps use UTC inside the reports; 24 October 19:01 UTC is
25 October 00:31 IST. Plot image bytes may differ on regeneration even when the
metrics and sampled rows match. Use a new evidence folder for each preserved run.
