# Learner SHAP reconciliation and scoped-card attachments

Preserved 25 October 2026 (IST) after the learner ran fare and demand version 1
on test-row positions 0 and 1 and attached the row-1 scoped cards to both model
versions. These are the learner's actual generated files, copied byte-for-byte
from `artifacts/learner-shap/`; they are not reconstructed screenshots or toy runs.

## Results

| Model / row position | Features | Baseline | Signed contribution sum | Independent raw prediction | Residual |
|---|---:|---:|---:|---:|---:|
| fare v1 / 0 | 14 | 18.5282969850 | 44.4919818265 | 63.0202788115 | 1.71e-13 |
| fare v1 / 1 | 14 | 18.5282969850 | -7.7103622479 | 10.8179347371 | 2.84e-14 |
| demand v1 / 0 | 20 | 14.8130754600 | -14.2393196864 | 0.5737557736 | -3.04e-14 |
| demand v1 / 1 | 20 | 14.8130754600 | 21.9731456959 | 36.7862211559 | -2.27e-13 |

Each CSV includes the complete signed vector and running total. JSON identifies
the raw feature values, model, source run, test-file hash and precise numeric
values. The waterfall visualizes the same row; labels are rounded for display.
Two attached row-1 runs duplicate their unattached counterparts intentionally,
preserving the separate attachment event and its URI.

Both original models were reloaded by numeric version during preservation.
Fresh `model.predict` outputs matched the recorded rows. CSV feature order,
vector length and all contributions matched their JSON. Both attached cards
were retrieved from MLflow and matched the exact version tags and SHA256 values.
`manifest.json` records preserved-file hashes and this verification context.

## Attached versions

- Fare: `models:/taxi-fare-predictor/1`, source run
  `431fcbd5c9784409994a95ea11453a87`. The row-1 card is under
  `scoped-explanations/fare-v1/46b12be2b3a544aa9db322844322edf1/scoped_card.md`.
- Demand: `models:/taxi-demand-forecaster/1`, source run
  `771eb4d4470f4da9ab8467568f9a8f34`. The row-1 card is under
  `scoped-explanations/demand-v1/1f2beb282a6b4a35a8359115b026da0b/scoped_card.md`.

These paths are inside the local source runs. `attachment.json` stores the full
`runs:/` URI. A GitHub checkout contains evidence, not the local MLflow database
or trained model bundles. Version tags are mutable pointers; the saved URI and
card hash identify the particular captured attachment. No deployed-model identity
is asserted.

## Interpretation and limits

Additivity is checked against a separate raw `model.predict`, not merely the
explanation helper's reconstructed `prediction` property. It establishes an
attribution decomposition, not model accuracy or causality. Beeswarm colors show
input values; waterfall colors show contribution sign. Global importance averages
absolute contributions across a sample, rather than explaining a named row.

Demand's recorded predictions are before serving clipping and recursive-history
integer rounding. Version 1 still uses the old canonical row splits with shared
boundary hours. These explanations do not close strict-split training,
multi-hour backtesting or missing weekend/holiday coverage.

Continue with [the strict-demand walkthrough](../../../docs/STRICT_DEMAND_NEXT_STEPS.md).
The full learning exercise is in
[the hands-on guide](../../../docs/HANDS_ON_SHAP_AND_EVALUATION_PLAN.md).

`learner-console-*.txt` retain pasted console output, including existing prompt
concatenation artifacts. `fare-v1-registry-tags.png` is the learner's registry
screen capture. Neither is interpreted as executable instructions.

## Validation

- Full offline suite: **137 passed**, coverage **95.01%** of `src`, one existing
  multipart pending-deprecation warning.
- Changed Python files: Ruff passed.
- Existing repository-wide Ruff issues in unchanged
  `scripts/learner_demand_history.py` remain: I001 import ordering and B007 unused
  `timestamp`. A repository-wide clean lint result is not claimed.
- Strict-hour preflight passed without model training or registration; its
  separate evidence is in `../strict-demand-preflight/`.
- Training smoke dispatch was unit-tested with a mock. Actual candidate smoke
  and tuned training are the next hands-on tasks, not completed evidence.
