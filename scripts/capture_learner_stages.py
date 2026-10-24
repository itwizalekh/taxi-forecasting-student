"""Capture fresh, hash-linked evidence from the three carved learner scripts."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    inputs = [ROOT / f"data/features/demand_{part}.parquet"
              for part in ("train", "val", "test")]
    before = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    historical = ROOT / "evidence/2026-10-24/learner-demand-time"
    scripts = [ROOT / f"scripts/learner_demand_time_stage_{stage:02d}.py"
               for stage in (1, 2, 3)]
    sources = [*scripts, Path(__file__), ROOT / "scripts/learner_demand_time_audit.py"]
    source_before = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    runs = []
    for stage, script in enumerate(scripts, start=1):
        started = datetime.now(UTC).isoformat()
        command = [sys.executable, str(script)]
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                                   encoding="utf-8", errors="strict", check=False)
        log = output / f"stage-{stage:02d}-console.txt"
        errors = output / f"stage-{stage:02d}-stderr.txt"
        log.write_text(completed.stdout, encoding="utf-8")
        errors.write_text(completed.stderr, encoding="utf-8")
        runs.append({"stage": stage, "source": str(script.relative_to(ROOT)),
                     "command": command, "cwd": str(ROOT), "started_utc": started,
                     "ended_utc": datetime.now(UTC).isoformat(),
                     "exit_code": completed.returncode,
                     "stdout": log.name, "stdout_sha256": sha(log),
                     "stderr": errors.name, "stderr_sha256": sha(errors)})
        print(f"Stage {stage}: exit {completed.returncode}; {log}")
    after = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    source_after = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    original_logs = [historical / name for name in
                     ("01-boundaries.txt", "02-boundary-rows.txt", "03-whole-hour-splits.txt")]
    manifest = {
        "provenance": "Fresh assistant-captured reruns of learner code carved into cumulative stages; not the original historical execution records.",
        "git_head_before_capture": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "python": sys.version, "platform": platform.platform(),
        "packages": {name: importlib.metadata.version(name)
                     for name in ("pandas", "numpy", "pyarrow")},
        "inputs_sha256_before": before, "inputs_sha256_after": after,
        "inputs_unchanged": before == after,
        "sources_sha256": source_before, "sources_unchanged": source_before == source_after,
        "original_logs_preserved_sha256": {str(p.relative_to(ROOT)): sha(p) for p in original_logs},
        "runs": runs,
        "all_stages_passed": all(run["exit_code"] == 0 for run in runs),
        "limitations": ["Input byte hashes require retaining/reacquiring the matching Parquet files for exact reproduction; data files are not committed.",
                        "Carved stage sources were prepared now; exact source versions at the original three executions were not previously archived.",
                        "Stage 3 additionally enforces reviewed assertions and full-value conservation; no feature or model training is performed."]}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if not (manifest["all_stages_passed"] and manifest["inputs_unchanged"]
            and manifest["sources_unchanged"]):
        raise SystemExit("Evidence capture failed: inspect manifest and stderr logs")
    print("PASS: all stages completed; inputs and sources unchanged during capture.")


if __name__ == "__main__":
    main()
