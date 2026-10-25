"""Reconcile every SHAP contribution with an independently computed raw prediction."""

from __future__ import annotations

import argparse
import copy
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import mlflow
import numpy as np
import pandas as pd

from scripts.responsible.run_analysis import file_sha256, resolve_model
from src.config import Config, get_config
from src.models.common import split_to_xy
from src.responsible.explain import explain_instance


def reconcile(model, row: pd.DataFrame) -> dict:
    """Compare the complete vector with model.predict, without clipping or rounding."""
    explanation = explain_instance(model, row)
    if list(explanation.contributions) != list(row.columns):
        raise ValueError("Contribution vector does not match the full feature schema")
    raw = float(model.predict(row)[0])
    contribution_sum = math.fsum(explanation.contributions.values())
    reconstructed = explanation.base_value + contribution_sum
    if not np.isfinite([raw, reconstructed, explanation.base_value]).all():
        raise ValueError("Nonfinite prediction or explanation")
    if not math.isclose(raw, reconstructed, rel_tol=1e-8, abs_tol=1e-8):
        raise ValueError(f"SHAP reconciliation failed: {raw=} {reconstructed=}")
    return {
        "base_value": explanation.base_value,
        "contributions": explanation.contributions,
        "contribution_sum": contribution_sum,
        "reconstructed": reconstructed,
        "raw_prediction": raw,
        "residual": raw - reconstructed,
        "tolerance": {"relative": 1e-8, "absolute": 1e-8},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--problem", choices=["fare", "demand"], required=True)
    parser.add_argument("--version", type=int, required=True)
    parser.add_argument("--row", type=int, default=0, help="Zero-based position in the test file")
    parser.add_argument("--analysis-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--attach-card", action="store_true", help="Log evidence to the training run and tag the model version")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; choose a new directory to preserve previous evidence")
    if args.version < 1 or args.row < 0:
        parser.error("Version must be positive and row must be nonnegative")

    config = Config(copy.deepcopy(get_config().raw))
    config.raw.setdefault("serving", {})["model_stage"] = str(args.version)
    model, identity = resolve_model(args.problem, config)
    report_path = args.analysis_dir / f"{args.problem}_fairness.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    for key in ("model_uri", "run_id"):
        if report["provenance"][key] != identity[key]:
            raise ValueError(f"Analysis/model identity mismatch: {key}")
    source_card = args.analysis_dir / f"{args.problem}.md"
    card_text = source_card.read_text(encoding="utf-8")
    if identity["run_id"] not in card_text or identity["model_uri"] not in card_text:
        raise ValueError("Source card does not identify the selected model and training run")
    test_path = config.features_dir / f"{args.problem}_test.parquet"
    test_sha = file_sha256(test_path)
    if report["provenance"]["input_sha256"][test_path.name] != test_sha:
        raise ValueError("Test-file hash differs from the reviewed analysis")
    frame = pd.read_parquet(test_path)
    X, y = split_to_xy(frame, args.problem)
    if args.row >= len(X):
        parser.error(f"Row must be less than {len(X)}")
    row = X.iloc[[args.row]]
    result = reconcile(model, row)
    result.update({
        "model": identity, "generated_at_utc": datetime.now(UTC).isoformat(),
        "test_row_position": args.row, "test_file_sha256": test_sha,
        "source_card_sha256": file_sha256(source_card),
        "actual_target": float(y.iloc[args.row]),
        "feature_order": list(row.columns),
        "feature_values": {name: float(row[name].iloc[0]) for name in row.columns},
        "row_keys": {name: str(frame.iloc[args.row][name]) for name in
                     ("pickup_hour", "PULocationID", "tpep_pickup_datetime") if name in frame},
    })
    args.output.mkdir(parents=True)
    cumulative = result["base_value"]
    records = []
    for feature, value in result["contributions"].items():
        cumulative += value
        records.append({"feature": feature, "input_value": result["feature_values"][feature],
                        "signed_contribution": value, "running_total": cumulative})
    table = pd.DataFrame(records)
    table.to_csv(args.output / "full_contributions.csv", index=False, float_format="%.17g")
    (args.output / "reconciliation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    scope = (
        f"\n## Single-row reconciliation scope\n\n"
        f"- Exact evaluated model: `{identity['model_uri']}`; run `{identity['run_id']}`.\n"
        f"- Test row position: {args.row} (zero based); file SHA256: `{test_sha}`.\n"
        f"- Baseline: {result['base_value']:.15g}; sum of ALL {len(row.columns)} signed contributions: "
        f"{result['contribution_sum']:.15g}.\n"
        f"- Independent model.predict: {result['raw_prediction']:.15g}; "
        f"reconstructed: {result['reconstructed']:.15g}; residual: {result['residual']:.3g}.\n"
        "- Explanation target: raw regressor output, before demand clipping, integer history "
        "rounding or API presentation. The baseline is the TreeExplainer expected value, "
        "not an independently asserted mean of this test file.\n"
        "- This row illustrates attribution; it does not establish causal effects, "
        "subgroup parity, future accuracy or deployment identity. Population metrics "
        "and limitations above refer to the separate reviewed analysis.\n"
    )
    (args.output / "scoped_card.md").write_text(card_text + scope, encoding="utf-8")

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shap

    shap.plots.waterfall(shap.Explanation(
        values=np.array(list(result["contributions"].values())),
        base_values=result["base_value"], data=row.iloc[0].to_numpy(),
        feature_names=list(row.columns),
    ), max_display=len(row.columns), show=False)
    plt.gcf().savefig(args.output / "waterfall.png", dpi=140, bbox_inches="tight")
    plt.close()
    if args.attach_card:
        client = mlflow.MlflowClient()
        artifact_path = f"scoped-explanations/{args.problem}-v{args.version}/{uuid4().hex}"
        client.log_artifacts(identity["run_id"], str(args.output), artifact_path=artifact_path)
        uri = f"runs:/{identity['run_id']}/{artifact_path}/scoped_card.md"
        client.set_model_version_tag(identity["registry_name"], str(args.version), "scoped_card_uri", uri)
        client.set_model_version_tag(identity["registry_name"], str(args.version), "scoped_card_sha256", file_sha256(args.output / "scoped_card.md"))
        (args.output / "attachment.json").write_text(json.dumps({"card_uri": uri}, indent=2) + "\n", encoding="utf-8")
        print(f"Attached card: {uri}")
    print(table.to_string(index=False))
    print(json.dumps({k: result[k] for k in ("base_value", "contribution_sum", "raw_prediction", "reconstructed", "residual")}, indent=2))
    print(f"Evidence saved to {args.output}")


if __name__ == "__main__":
    main()
