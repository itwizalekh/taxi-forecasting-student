"""Execute a clean capstone route, or verify an explicitly reused local setup.

Fresh mode refuses existing model/data outputs. Verify mode never retrains,
rebuilds, stops or replaces the existing API. It writes a new batch generation
and drift reports. Neither mode certifies a grade or manual dashboard interaction.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(UTC).isoformat()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def request_json(url: str, payload: dict | None = None) -> dict:
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def require_ready(base_url: str, seconds: int = 90) -> dict:
    deadline = time.monotonic() + seconds
    last_error = "not checked"
    while time.monotonic() < deadline:
        try:
            health = request_json(base_url + "/health")
            if (health.get("status") == "ok" and health.get("fare_model_loaded")
                    and health.get("demand_model_loaded") and health.get("zones", 0) > 0):
                return health
            last_error = str(health)
        except Exception as exc:
            last_error = str(exc)
        time.sleep(2)
    raise RuntimeError(f"API readiness failed: {last_error}")


class Run:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        label = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        self.out = ROOT / "artifacts" / "capstone-runs" / f"{label}-{args.mode}"
        self.out.mkdir(parents=True, exist_ok=False)
        self.manifest = {
            "started_at_utc": now(), "mode": args.mode,
            "clean_execution": args.mode == "fresh", "python": sys.executable,
            "platform": platform.platform(), "output_dir": str(self.out),
            "success": False, "stages": [],
            "scope": "Automated execution evidence; manual video/dashboard requirements are separate.",
            "deployment_scope": "Temporary test deployment" if args.mode == "fresh"
            else "Existing local Compose deployment; no automated redeployment in verify mode",
        }
        self.env = os.environ.copy()
        self.env["MLFLOW_TRACKING_URI"] = "sqlite:///" + (ROOT / "mlflow.db").as_posix()
        self.env["MPLBACKEND"] = "Agg"
        self.env["PYTHONUNBUFFERED"] = "1"
        self.compose: list[str] = []
        self.owns_stack = False
        self.dashboard: subprocess.Popen | None = None
        self.dashboard_log = None
        self.save()

    def save(self) -> None:
        write_json(self.out / "manifest.json", self.manifest)
        write_json(self.out.parent / f"latest-{self.args.mode}.json", {
            "output_dir": str(self.out), "manifest": str(self.out / "manifest.json"),
            "success": self.manifest["success"],
        })

    def stage(self, name: str, action) -> None:
        item = {"name": name, "started_at_utc": now(), "status": "running"}
        self.manifest["stages"].append(item)
        self.save()
        print(f"\nSTART {name}", flush=True)
        try:
            result = action()
            if result is not None:
                item["result"] = result
            item["status"] = "passed"
        except Exception as exc:
            item["status"] = "failed"
            item["error"] = str(exc)
            raise
        finally:
            item["finished_at_utc"] = now()
            self.save()
            print(f"{item['status'].upper()} {name}", flush=True)

    def command(self, name: str, args: list[str], timeout: int = 1200) -> dict:
        log = self.out / f"{name}.log"
        record = {"command": args, "cwd": str(ROOT), "log": str(log)}
        write_json(self.out / f"{name}-command.json", record)
        with log.open("w", encoding="utf-8") as handle:
            result = subprocess.run(
                args, cwd=ROOT, env=self.env, stdout=handle,
                stderr=subprocess.STDOUT, timeout=timeout, check=False,
            )
        record["exit_code"] = result.returncode
        write_json(self.out / f"{name}-command.json", record)
        print("\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-12:]))
        if result.returncode:
            raise RuntimeError(f"{name} exited {result.returncode}; see {log}")
        return record

    def python(self, name: str, *args: str, timeout: int = 1200) -> dict:
        return self.command(name, [sys.executable, *args], timeout)

    def preflight(self) -> dict:
        if sys.version_info[:2] != (3, 11):
            raise RuntimeError("Use Python 3.11 (the project's .venv on Windows).")
        if self.args.mode == "fresh":
            existing = [p for p in (ROOT / "mlflow.db", ROOT / "mlflow.container.db") if p.exists()]
            existing += list((ROOT / "data/processed").glob("*.parquet"))
            existing += list((ROOT / "data/features").glob("*.parquet"))
            existing += list((ROOT / "mlruns").glob("*"))
            if existing:
                raise RuntimeError("Fresh mode requires an unused checkout. Existing outputs found; nothing deleted.")
        packages = {}
        for name in ("pandas", "mlflow", "SQLAlchemy", "pytest", "ruff"):
            packages[name] = importlib.metadata.version(name)
        if not self.args.skip_dashboard:
            for name in ("streamlit", "plotly"):
                packages[name] = importlib.metadata.version(name)
        docker = shutil.which("docker")
        if not docker and os.name == "nt":
            candidate = Path.home() / "AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe"
            if candidate.exists():
                docker = str(candidate)
        if not docker:
            raise RuntimeError("Docker CLI missing; start Docker Desktop and use a fresh terminal.")
        self.compose = [docker, "compose"]
        if self.args.mode == "fresh":
            self.compose += ["-p", "capstone-clean"]
        self.compose += ["-f", "docker/docker-compose.yml"]
        self.command("docker-version", [docker, "version"], 30)
        for name, args in (("revision", ["rev-parse", "HEAD"]),
                           ("working-tree", ["status", "--short"])):
            self.command(name, ["git", *args], 30)
        self.manifest["revision"] = (self.out / "revision.log").read_text().strip()
        if os.getenv("GITHUB_RUN_ID"):
            self.manifest["workflow_url"] = (
                f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/"
                f"{os.environ['GITHUB_RUN_ID']}"
            )
        files = [ROOT / "requirements.txt", ROOT / "config/config.yaml", ROOT / "docker/Dockerfile"]
        files += sorted((ROOT / "src").rglob("*.py"))
        files += sorted((ROOT / "scripts").rglob("*.py"))
        write_json(self.out / "source-hashes.json", {
            str(p.relative_to(ROOT)): sha256(p) for p in files
        })
        return packages

    def lineage(self) -> dict:
        db = ROOT / "mlflow.db"
        with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as connection:
            rows = connection.execute(
                "SELECT name,version,run_id,source FROM model_versions WHERE version=1 "
                "AND name IN ('taxi-demand-forecaster','taxi-fare-predictor')"
            ).fetchall()
            if len(rows) != 2:
                raise RuntimeError("Both standard registered version-1 models are required.")
            models = []
            for name, version, run_id, source in rows:
                metrics = dict(connection.execute(
                    "SELECT key,value FROM metrics WHERE run_uuid=?", (run_id,)
                ).fetchall())
                artifacts = list((ROOT / "mlruns").glob(f"*/{run_id}/artifacts/model/MLmodel"))
                if not artifacts:
                    raise RuntimeError(f"Missing local model artifact for {run_id}")
                models.append({"name": name, "version": version, "run_id": run_id,
                               "source": source, "metrics": metrics,
                               "artifact_hashes": {str(p.relative_to(ROOT)): sha256(p)
                                   for p in artifacts[0].parent.rglob("*") if p.is_file()}})
        paths = [ROOT / "data/processed/pipeline_summary.json",
                 ROOT / "data/processed/demand_hourly.parquet"]
        paths += sorted((ROOT / "data/features").glob("*_test.parquet"))
        if len(paths) != 4 or any(not p.exists() for p in paths):
            raise RuntimeError("Required pipeline/history/test files missing.")
        result = {"models": models, "input_hashes": {
            str(p.relative_to(ROOT)): sha256(p) for p in paths},
            "generation": "freshly executed" if self.args.mode == "fresh"
            else "explicit reuse of existing data and training; not a clean-generation claim"}
        write_json(self.out / "model-and-data-lineage.json", result)
        return result

    def api_checks(self) -> dict:
        base = self.args.api_url.rstrip("/")
        health = require_ready(base)
        write_json(self.out / "health.json", health)
        payloads = {
            "fare": {"trip_distance": 3.2, "passenger_count": 1, "pu_location_id": 161,
                     "do_location_id": 236, "pickup_datetime": "2024-01-20T10:00:00",
                     "trip_duration_min": 18.0},
            "demand": {"zone": 132, "target_hour": "2024-02-01T00:00:00"},
        }
        result = {}
        for name, payload in payloads.items():
            response = request_json(base + "/predict/" + name, payload)
            key = "predicted_fare" if name == "fare" else "predicted_pickups"
            if not math.isfinite(response[key]) or response[key] < 0 or not response.get("request_id"):
                raise RuntimeError(f"Invalid {name} response: {response}")
            write_json(self.out / f"{name}-request-response.json", {
                "url": base + "/predict/" + name, "request": payload, "response": response,
            })
            result[name] = response
        with urllib.request.urlopen(base + "/metrics", timeout=30) as response:
            metrics = response.read().decode()
        if "http_requests_total" not in metrics:
            raise RuntimeError("Expected application request metrics not found.")
        (self.out / "application-metrics.txt").write_text(metrics, encoding="utf-8")
        return result

    def responsible_evidence(self) -> dict:
        result = {}
        for problem in ("fare", "demand"):
            files = [ROOT / f"artifacts/responsible/{problem}_fairness.json",
                     ROOT / f"artifacts/responsible/{problem}_shap_summary.png",
                     ROOT / f"docs/model_cards/{problem}.md"]
            if any(not p.is_file() for p in files):
                raise RuntimeError("Responsible-AI files missing; run scripts.responsible.run_analysis.")
            target = self.out / "responsible"
            target.mkdir(exist_ok=True)
            for path in files:
                shutil.copy2(path, target / path.name)
            result[problem] = {str(p.relative_to(ROOT)): sha256(p) for p in files}
        return result

    def dashboard_check(self) -> dict:
        port = 8765 if self.args.mode == "verify" else 8501
        env = self.env.copy()
        env["API_BASE_URL"] = self.args.api_url
        env["DRIFT_DIR"] = str(self.out / "drift")
        self.dashboard_log = (self.out / "dashboard.log").open("w", encoding="utf-8")
        self.dashboard = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", "dashboard/app.py",
            "--server.address", "127.0.0.1", "--server.port", str(port),
            "--server.headless", "true", "--browser.gatherUsageStats", "false",
        ], cwd=ROOT, env=env, stdout=self.dashboard_log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if self.dashboard.poll() is not None:
                raise RuntimeError("Dashboard exited; inspect dashboard.log.")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=3) as response:
                    if response.read().decode().strip() == "ok":
                        return {"server_ready": True, "port": port,
                                "manual_interaction": "Must still be demonstrated in the video"}
            except Exception:
                pass
            time.sleep(1)
        raise RuntimeError("Dashboard readiness timeout; inspect dashboard.log.")

    def execute(self) -> int:
        try:
            self.stage("preflight", self.preflight)
            self.stage("lint", lambda: self.python("lint", "-m", "ruff", "check", "."))
            self.stage("tests", lambda: self.python(
                "tests", "-m", "pytest", "--cov=src", "--cov-report=term-missing",
                f"--cov-report=xml:{self.out / 'coverage.xml'}"))
            if self.args.mode == "fresh":
                self.stage("data-pipeline", lambda: self.python(
                    "data-pipeline", "-m", "scripts.run_pipeline", "--year", "2024", "--month", "1"))
                self.stage("training", lambda: self.python(
                    "training", "-m", "scripts.train_models", "--n-trials", "1"))
            self.stage("model-and-data-lineage", self.lineage)
            if self.args.mode == "fresh":
                self.stage("portable-registry", lambda: self.python(
                    "portable-registry", "-m", "scripts.make_mlflow_portable"))
                self.stage("container-build", lambda: self.command(
                    "container-build", [*self.compose, "build", "api"]))
                self.owns_stack = True
                self.stage("deploy-test-container", lambda: self.command(
                    "container-start", [*self.compose, "up", "-d", "--no-build", "api"]))
            self.stage("container-status", lambda: self.command(
                "container-status", [*self.compose, "ps", "--all"]))
            self.stage("container-image-identity", lambda: self.command(
                "container-image-identity", [*self.compose, "images", "--format", "json"]))
            self.stage("live-inference-and-monitoring", self.api_checks)
            self.stage("batch-inference", lambda: self.python(
                "batch-inference", "-m", "scripts.batch_forecast", "--horizon", "1"))
            with sqlite3.connect((ROOT / "predictions.db").as_uri() + "?mode=ro", uri=True) as connection:
                rows = connection.execute(
                    "SELECT generated_at,COUNT(*),COUNT(DISTINCT PULocationID),MIN(pickup_hour),"
                    "MAX(pickup_hour) FROM demand_forecasts GROUP BY generated_at "
                    "ORDER BY generated_at DESC LIMIT 1"
                ).fetchone()
            write_json(self.out / "batch-generation.json", {
                "generation_rows_zones_start_end": rows,
                "note": "Writer stores latest label; resolved numeric model is in model-and-data-lineage.json.",
            })
            self.stage("controlled-drift", lambda: self.python(
                "controlled-drift", "-m", "scripts.monitoring.demo_drift_report",
                "--problem", "all", "--mode", "drift", "--output-dir", str(self.out / "drift")))
            write_json(self.out / "drift-context.json", {
                "source": "Training features with deliberately shifted sampled numeric features",
                "production_incident": False,
            })
            if self.args.mode == "fresh":
                self.stage("responsible-analysis", lambda: self.python(
                    "responsible-analysis", "-m", "scripts.responsible.run_analysis"))
            self.stage("responsible-evidence", self.responsible_evidence)
            if not self.args.skip_dashboard:
                self.stage("dashboard-server-readiness", self.dashboard_check)
            else:
                self.manifest["stages"].append({"name": "dashboard-server-readiness", "status": "skipped"})
            self.manifest["success"] = not self.args.skip_dashboard
            return 0
        except Exception as exc:
            self.manifest["error"] = str(exc)
            print(f"\nFAILED: {exc}", flush=True)
            return 1
        finally:
            if self.dashboard is not None:
                self.dashboard.terminate()
                try:
                    self.dashboard.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    self.dashboard.kill()
                    self.dashboard.wait(timeout=10)
            if self.dashboard_log is not None:
                self.dashboard_log.close()
            if self.owns_stack:
                for label, args in (("container-final-logs", ["logs", "--no-color"]),
                                    ("container-cleanup", ["down"])):
                    try:
                        self.command(label, [*self.compose, *args], 90)
                    except Exception as exc:
                        self.manifest.setdefault("cleanup_errors", []).append(str(exc))
            self.manifest["finished_at_utc"] = now()
            self.save()
            (self.out / "SUMMARY.md").write_text(
                "# Capstone execution evidence\n\n"
                f"Mode: {self.args.mode}\n\nAutomated run success: {self.manifest['success']}\n\n"
                f"Revision: {self.manifest.get('revision', 'preflight failed')}\n\n"
                + "\n".join(f"- {s['name']}: {s['status']}" for s in self.manifest["stages"])
                + "\n\nDashboard interaction, webcam/own-voice video and portal submission require manual completion.\n",
                encoding="utf-8",
            )
            write_json(self.out / "output-hashes.json", {
                str(p.relative_to(self.out)): sha256(p) for p in self.out.rglob("*")
                if p.is_file() and p.name != "output-hashes.json"
            })
            print(f"\nEVIDENCE: {self.out}\nMANIFEST: {self.out / 'manifest.json'}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("fresh", "verify"), required=True)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--skip-dashboard", action="store_true",
                        help="Diagnostic partial run only; success remains false.")
    args = parser.parse_args()
    return Run(args).execute()


if __name__ == "__main__":
    raise SystemExit(main())
