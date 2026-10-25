"""Run the actual pipeline on a labelled one-in-100 sample in an isolated folder.

This representative live demonstration does not replace full-data training
evidence or alter the data/history used by the running API.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from scripts.capstone_golden_path import sha256

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    original = ROOT / "data/raw/yellow_tripdata_2024-01.parquet"
    lookup = ROOT / "data/raw/taxi_zone_lookup.csv"
    if not original.is_file() or not lookup.is_file():
        raise FileNotFoundError("Prepare the January 2024 raw file and zone lookup first.")
    label = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT / "artifacts/capstone-live" / label
    raw = out / "raw"
    raw.mkdir(parents=True, exist_ok=False)
    source = pq.ParquetFile(original)
    rows = 0
    with pq.ParquetWriter(raw / original.name, source.schema_arrow) as writer:
        for batch in source.iter_batches(batch_size=50_000):
            sampled = pa.Table.from_batches([batch]).take(
                pa.array(range(0, batch.num_rows, 100), type=pa.int64())
            )
            writer.write_table(sampled)
            rows += len(sampled)
    shutil.copy2(lookup, raw / lookup.name)
    context = {
        "scope": "Representative live processing of one-in-100 source rows; not full training input",
        "source": str(original), "source_sha256": sha256(original),
        "original_rows": source.metadata.num_rows, "sample_rows": rows,
        "sampling": "Every 100th row in successive 50,000-row record batches",
        "output_dir": str(out),
    }
    print(json.dumps(context, indent=2), flush=True)
    (out / "sample-context.json").write_text(json.dumps(context, indent=2), encoding="utf-8")
    env = os.environ.copy()
    env.update({"DATA_RAW_DIR": str(raw), "DATA_PROCESSED_DIR": str(out / "processed"),
                "DATA_FEATURES_DIR": str(out / "features")})
    result = subprocess.run(
        [sys.executable, "-m", "scripts.run_pipeline", "--year", "2024",
         "--month", "1", "--skip-download"], cwd=ROOT, env=env, check=False,
    )
    if result.returncode == 0:
        summary = json.loads((out / "processed/pipeline_summary.json").read_text())
        cleaning = summary["cleaning"]
        if (cleaning["input_rows"] != rows or cleaning["output_rows"] <= 0
                or cleaning["output_rows"] + cleaning["total_dropped"] != rows
                or summary["demand_feature_rows"] <= 0 or summary["fare_feature_rows"] <= 0):
            raise RuntimeError("Representative pipeline validation failed.")
        context["pipeline_summary"] = summary
        context["validation"] = "Row conservation, nonempty clean data and feature tables passed"
    context["exit_code"] = result.returncode
    (out / "sample-context.json").write_text(json.dumps(context, indent=2), encoding="utf-8")
    (out.parent / "latest.json").write_text(json.dumps(context, indent=2), encoding="utf-8")
    print(f"\nLIVE PIPELINE OUTPUT: {out}", flush=True)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
