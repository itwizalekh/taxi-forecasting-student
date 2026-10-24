# Generate Model Cards

The checked-in cards document the author's local January 2024 evaluation;
they do not include model bundles or establish that your environment uses those models.
After your own data preparation and model registration, run from the project root:

```powershell
.\.venv\Scripts\python.exe -m scripts.responsible.run_analysis
```

This generates `demand.md` and `fare.md` here, plus fairness JSON and SHAP plots
under `artifacts/responsible/`. For fare alone, add `--problem fare`.
Follow [setup](../SETUP.md) first. Preserve outputs before regenerating them.

The workflow resolves the configured selector to a numeric version before loading,
then records its training run, split periods and input SHA256 hashes in the fairness JSON.
Cards record the numeric model reference and limits of the evaluation. Comparisons
with insufficient usable groups are labelled as such, not reported as parity.
Preserved originals and reviewed outputs are in
[`evidence/2026-10-25/responsible-analysis/`](../../evidence/2026-10-25/responsible-analysis/).
These reports describe a local run; they are
not proof that a deployed service uses the same model. A mutable `latest`
reference is not immutable provenance.

Dashboard cloud builds require the actual generated cards, not just this README.
Publish and restore your own cards into the build context before releasing an
image intended to display them. Do not copy another account's model artifacts.
