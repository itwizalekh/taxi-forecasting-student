# Capstone rehearsal and submission runbook

Prepared 25 October 2026. Follow this document from top to bottom. It covers:
**native Windows execution from a clean checkout -> Docker serving of those models -> GitHub-hosted clean execution -> evidence review -> video -> submission.**

The rehearsal uses a new checkout and separate ports. Your existing `C:\Data\BITS\labs\taxi-forecasting-student` environment, models and containers remain available as a fallback. Do not delete them or run a reset/cleanup against them.

## 0. Route, timing and completion criteria

| Approximate rehearsal budget | Activity | Continue when |
| --- | --- | --- |
| 0-15 minutes | New checkout, Python environment, dependencies and quality checks | Correct commit, working imports, passing lint/tests |
| 15-45 minutes | Native data pipeline, training and serving | Real data outputs, registered models, API and batch predictions |
| 45-60 minutes | Monitoring, Responsible AI and dashboard | Computed reports and successful browser interaction |
| 60-85 minutes | Docker build, deployment and predictions | Running identified container, ready models, real responses |
| 85-105 minutes | GitHub workflow and downloaded evidence | Successful fresh run for the submitted commit; archive inspected |
| 105-120 minutes | Rehearsal, missing-evidence check, recording preparation | All claimed phases have evidence and the spoken demo fits |

These are planning budgets, not runtime guarantees. Reserve additional time after rehearsal for the recording, export, playback and upload. The supplied portal page lists **25 October 2026 at 11:59 PM** as the deadline; check the portal's displayed timezone and current deadline. Do not spend the submission buffer on AWS.

The written rubric does not mandate AWS or Terraform. Week37 calls AWS good to have and non-blocking. Phases 4-5 still require successful workflow, infrastructure/deployment and monitoring evidence. This route demonstrates a local container deployment and a temporary deployment on a GitHub-hosted runner; describe both accurately. Neither is a permanent public AWS service. Assessment remains against the course rubric.

The native route runs data/training/analysis once. The Docker route reuses those exact trained models and repeats serving, batch and monitoring checks inside/against the container. The dashboard remains a native Streamlit process talking to the container. The GitHub route independently regenerates the project in a clean runner. This is not a claim that every component is containerized.

### Existing evidence, before this rehearsal

- Source branch inspected: `responsible-analysis-evidence`.
- Source commit inspected: `0ac3fd8efebb7c6afa85446c4e8b78fac74f2f8d`.
- Retained local verification: 149 passing tests, 95.09% coverage and successful API/batch/drift/dashboard-server checks. These are historical results, not a required count for future runs.
- Retained GitHub metadata records a successful **Capstone clean run**, run `40186307700`, for that commit. Inspect its detailed artifact before claiming every clean stage completed.
- A local `fresh` attempt in the populated checkout was correctly refused. It is not successful clean-execution evidence. The new checkout below avoids that issue.

### Terminal names and ports

Use ordinary PowerShell terminals; virtual-environment activation is unnecessary.

| Terminal | Purpose | Address |
| --- | --- | --- |
| A | Main commands and evidence capture | New rehearsal checkout |
| B | Native API, kept running | `http://127.0.0.1:8010` |
| C | Native MLflow UI, kept running | `http://127.0.0.1:5010` |
| D | Dashboard, kept running | `http://127.0.0.1:8510` |
| Docker | API container; MLflow UI container | API `8020`; MLflow `5020` |
| Existing fallback | Original checkout's services, if running | `8000`, `5000`, `8501` |

**Run the setup blocks once per rehearsal, not once per phase.** Keep terminal A open. If it closes, restore the session using the bootstrap block in step 4, then resume at the next unfinished step.

### 0.1 One-time commit checkpoint before R1

Inspection found no pending application-code, dependency, Dockerfile or workflow changes. There are four modified guides, this untracked runbook and retained evidence folders. **Recommended:** commit/push only this runbook and its old-entry-point redirect before cloning, so the public baseline includes the instructions. Other guide edits and untracked evidence need separate review; they are not prerequisites for rehearsal. Preparation of this document does not execute a commit/push.

Start in the original checkout:

```powershell
Set-Location -LiteralPath 'C:\Data\BITS\labs\taxi-forecasting-student'
git branch --show-current
git status --short
git diff --cached --name-only
```

Require branch `responsible-analysis-evidence` and an empty staged list. If unrelated files are already staged, review that state first; do not silently include or unstage someone else's work.

```powershell
git add -- docs/CAPSTONE_SUBMISSION_STEPS.md docs/CAPSTONE_REHEARSAL_RUNBOOK.md
git diff --cached --stat
git -c core.whitespace=cr-at-eol diff --cached --check
if ($LASTEXITCODE -ne 0) { throw 'Resolve the staged-document whitespace issue.' }
git commit -m 'Document repeatable capstone rehearsals and submission evidence'
if ($LASTEXITCODE -ne 0) { throw 'Documentation commit failed.' }
git push origin responsible-analysis-evidence
if ($LASTEXITCODE -ne 0) { throw 'Publish the baseline before cloning it.' }
git rev-parse HEAD
```

Do not use `git add .`. The push triggers a new **Capstone clean run**. Its new SHA replaces the historical `0ac3fd8...` baseline; let the workflow continue while rehearsing locally, then inspect it in step 10.

**Freeze the baseline once after the push**, in the same original checkout. Do not repeat this block between R1/R2/R3:

```powershell
$capstoneBaselineFile = 'C:\Data\BITS\labs\capstone-rehearsal-baseline.json'
if (Test-Path -LiteralPath $capstoneBaselineFile) {
    Get-Content -LiteralPath $capstoneBaselineFile
    throw 'A baseline already exists. Reuse it for repeated rehearsals; do not overwrite it accidentally.'
}
$capstoneFrozenCommit = (git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Could not identify the baseline revision.' }
@{Commit=$capstoneFrozenCommit;Branch='responsible-analysis-evidence';RecordedAt=(Get-Date -Format o)} | ConvertTo-Json | Set-Content -LiteralPath $capstoneBaselineFile -Encoding utf8
Get-Content -LiteralPath $capstoneBaselineFile
```

If you intentionally skip the recommended documentation commit, execution still works at the current public implementation SHA. Freeze that SHA instead; keep this local runbook open because the older public checkout will not contain it.

**No commits are needed during a successful rehearsal.** Generated data, registrations, model cards and logs are execution outputs. Never commit from a detached rehearsal checkout. Use step 10.2 only if a real source correction is needed.

### 0.2 Streamlit, working directory and repeated rehearsals

1. Press **Ctrl+C** in the known terminal running the old Streamlit and wait for its prompt before closing/reopening VS Code. Closing the editor is not a reliable check that every detached/background service stopped. Docker containers are independent of VS Code.
2. Start the one-time commit/freeze in `C:\Data\BITS\labs\taxi-forecasting-student`. Step 1 then creates and enters a new timestamped checkout automatically. **Do not create that directory manually.** All subsequent project commands run in that checkout, not `capstone`, the parent `labs` directory or the original checkout.
3. Use step 4's bootstrap block in every new B/C/D terminal. The original fallback services may remain on 8000/5000; rehearsal services use the separate ports above.
4. For three full clean rehearsals, run steps 1-11 for **R1**, close that round using step 14.1, then repeat for **R2** and **R3**. Use steps 12-13 for the actual recording/submission after the final selected round. Never repeat setup within one round.
5. Each round creates its own clone, environment, data, registry, trained models and unique container names, while keeping the same frozen source SHA. Dependency-download and Docker dependency-layer caches can be reused; no need to purge them to establish fresh project outputs.
6. Before another round, stop the previous round's native processes and its named rehearsal containers. The new round replaces the shared `capstone-active-rehearsal.json` pointer. Old terminals retain old variables: close them before bootstrapping terminals for the next round. Each round also retains its own `artifacts/rehearsal/session.json` for recovery.
7. New run IDs, timestamps, evidence paths and container IDs are expected. Do not mix R1 metrics/reports with R3's served model. Retain the final chosen round's services and use its own evidence for the video.
8. Three complete clean rounds repeat installation, training and image assembly, so do not assume they fit the original two-hour budget. Check disk space with `Get-PSDrive C` before each round; multiple environments/data/images consume many GB. Preserve recording/export/upload time. A practical shorter alternative is one full clean round plus two timed presentation rehearsals, labeled accurately.

### 0.3 L1-L12 correspondence

The labs cover most implementation building blocks. Isolated lab completion does not establish the complete capstone's integration or video evidence. The mapping below uses the **eight submission phases**, not the seven conceptual engineering phases in some recordings.

| Lab and guide | Capstone contribution | Runbook steps | Qualification / additional work |
| --- | --- | --- | --- |
| L1: [setup](SETUP.md), environment check | Prerequisite environment and quality baseline | 1-2, 6 | Setup alone is not training/deployment evidence. |
| L2: [fare metrics](L2_FARE_METRICS_LAB.md) | Interpret phase-2 evaluation | 4, 12 | Arithmetic/learning activity; does not produce trained models. |
| L3: [exploration](L3_DATA_EXPLORATION_LAB.md) | Phase 1: source and validation understanding | 3 | Notebook exploration/findings remain lab practice; persisted pipeline outputs are used here. |
| L4: [pipeline](L4_PIPELINE_EVIDENCE_LAB.md) | Phase 1: cleaning, aggregation, features and splits | 3 | Check actual generated outputs and row consistency. |
| L5: [MLflow](L5_MLFLOW_MODEL_TRACKING_LAB.md) | Phase 2: candidates, validation comparison and tracking | 4 | Its fare-only `--no-register` exercise does not supply both serving registrations. The runbook adds demand/fare registration. |
| L6: [explainability](L6_EXPLAINABILITY_LAB.md) | Phases 2/6: SHAP and model cards | 4, 7 | The runbook generates two-model analysis; global SHAP is not causality. |
| L7: [API/Docker](L7_API_DOCKER_LAB.md) | Phase 3 and container deployment for phase 4 | 5, 9 | Runbook adds batch persistence, identities and native/container comparison. Optional invalid-request practice is below. |
| L8: [quality gate](L8_CI_QUALITY_GATE_LAB.md) | Phase 4: lint, tests, coverage and failure interpretation | 2, 6, 10 | The runbook adds a real hosted GitHub workflow. Controlled scratch lint failure is lab practice, not a capstone requirement. |
| L9: [infrastructure](L9_AWS_INFRASTRUCTURE_LAB.md) | Phase 4: request/release/infrastructure boundaries | 9-10 | Non-AWS adaptation using Docker/GitHub, not literal completion of the AWS console tasks. |
| L10: [drift](L10_DRIFT_MONITORING_LAB.md) | Phase 5: local metrics, synthetic PSI/KS and interpretation | 7, 9 | CloudWatch/SNS/SageMaker checks are skipped, not claimed. |
| L11: [fairness](L11_FAIRNESS_REVIEW_LAB.md) | Phase 6: subgroup errors, findings and mitigation | 7 | Use the labeled local fallback; S3 publishing is not demonstrated. A mitigation proposal is not a successful mitigation. |
| L12: [dashboard](L12_DASHBOARD_INSIGHT_LAB.md) | Phase 7: working interaction and evidence-based insight | 8-9 | Use the local fallback, identify source freshness and perform a real interaction. |
| Cross-lab integration | Phase 8 plus submission | 10-13 | Clean automation, complete evidence, public repo, video and portal confirmation go beyond separate lab tasks. |

For separately assessed labs, still follow their own worksheets, findings/reflections and route labels. This correspondence does not claim every optional cloud exercise is complete or alter the official capstone rubric.

## 1. Create a genuinely new rehearsal checkout

In terminal A:

```powershell
$ErrorActionPreference = 'Stop'
$capstoneSource = 'C:\Data\BITS\labs\taxi-forecasting-student'
$capstonePublicRepo = 'https://github.com/itwizalekh/taxi-forecasting-student.git'
$capstoneBaselineFile = 'C:\Data\BITS\labs\capstone-rehearsal-baseline.json'
if (-not (Test-Path -LiteralPath $capstoneBaselineFile)) { throw 'Complete the one-time baseline freeze in step 0.1 first.' }
$capstoneCommit = (Get-Content -LiteralPath $capstoneBaselineFile -Raw | ConvertFrom-Json).Commit
git -C $capstoneSource cat-file -e ($capstoneCommit + '^{commit}')
if ($LASTEXITCODE -ne 0) { throw 'The frozen source commit is not available.' }
$capstoneRound = Read-Host 'Rehearsal label: R1, R2 or R3'
if ($capstoneRound -notmatch '^R[123]$') { throw 'Use R1, R2 or R3.' }
$capstoneStamp = Get-Date -Format yyyyMMdd-HHmmss
$capstoneRepo = Join-Path 'C:\Data\BITS\labs' ('taxi-capstone-rehearsal-' + $capstoneRound + '-' + $capstoneStamp)
if (Test-Path -LiteralPath $capstoneRepo) { throw 'Choose a new rehearsal folder.' }
git clone --branch responsible-analysis-evidence --single-branch $capstonePublicRepo $capstoneRepo
if ($LASTEXITCODE -ne 0) { throw 'Clone failed; inspect the first network/authentication error.' }
git -C $capstoneRepo checkout --detach $capstoneCommit
if ($LASTEXITCODE -ne 0) { throw 'The local source commit is not available from the public branch. Resolve publication before continuing.' }
Set-Location -LiteralPath $capstoneRepo
git status --short --branch
git rev-parse HEAD
```

**Check:** the SHA matches `$capstoneCommit`; the checkout has no source changes. Detached HEAD is intentional: the rehearsal uses an exact revision. Existing uncommitted changes in the original checkout are not copied or silently attributed to this SHA.

Create session state and an evidence folder. The pointer file lets other terminals find this particular checkout.

```powershell
$capstoneEvidence = Join-Path $capstoneRepo 'artifacts\rehearsal'
New-Item -ItemType Directory -Path $capstoneEvidence -Force | Out-Null
$capstoneState = [ordered]@{
    Rehearsal = $capstoneRound
    Repo = $capstoneRepo
    Commit = $capstoneCommit
    Python = (Join-Path $capstoneRepo '.venv\Scripts\python.exe')
    Evidence = $capstoneEvidence
    Image = ('taxi-capstone-rehearsal:' + $capstoneStamp)
    Container = ('taxi-rehearsal-api-' + $capstoneStamp)
    MlflowContainer = ('taxi-rehearsal-mlflow-' + $capstoneStamp)
    PublicRepo = 'https://github.com/itwizalekh/taxi-forecasting-student'
}
$capstoneSessionFile = 'C:\Data\BITS\labs\capstone-active-rehearsal.json'
$capstoneState | ConvertTo-Json | Set-Content -LiteralPath $capstoneSessionFile -Encoding utf8
$capstoneState | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $capstoneEvidence 'session.json') -Encoding utf8
$capstonePy = $capstoneState.Python
Start-Transcript -Path (Join-Path $capstoneEvidence 'terminal-A.log')
```

The pointer can be replaced by a later rehearsal; each checkout retains its own session/evidence. Evidence under `artifacts/` is Git-ignored. Review logs before publishing them; a local transcript is not automatically suitable for a public repository.

Check the rehearsal ports before starting services:

```powershell
$capstoneOccupied = @(Get-NetTCPConnection -State Listen -LocalPort 8010,5010,8510,8020,5020 -ErrorAction SilentlyContinue)
if ($capstoneOccupied.Count -gt 0) {
    $capstoneOccupied | Select-Object LocalAddress,LocalPort,OwningProcess
    throw 'A rehearsal port is occupied. Identify the process and resolve the collision or consistently choose other rehearsal ports.'
}
```

## 2. Install the native environment and verify prerequisites

Use the working source environment's Python 3.11 to create a **new**, independent virtual environment:

```powershell
& (Join-Path $capstoneSource '.venv\Scripts\python.exe') --version
& (Join-Path $capstoneSource '.venv\Scripts\python.exe') -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Creating the rehearsal environment failed.' }
& $capstonePy --version
& $capstonePy -m pip install -r requirements.txt -r requirements-dashboard.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed; do not continue to training.' }
& $capstonePy -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Resolve the dependency consistency error.' }
& $capstonePy -c "import pandas, sklearn, fastapi, streamlit, plotly; import mlflow.store.db.utils; print('Core, dashboard and MLflow database imports passed')"
if ($LASTEXITCODE -ne 0) { throw 'Import verification failed.' }
& $capstonePy -m pip freeze | Set-Content -LiteralPath (Join-Path $capstoneEvidence 'installed-packages.txt') -Encoding utf8
```

**Check:** Python 3.11, no broken requirements, imports passed. The checked-in requirements already pin SQLAlchemy 2.0.55 to avoid the previous MLflow import problem. Do not upgrade MLflow/SQLAlchemy arbitrarily during this rehearsal.

In terminal A, remove only inherited project overrides from this shell so the new checkout uses its own local paths. Do not print all environment variables or copy an old `.env` file.

```powershell
'DATA_RAW_DIR','DATA_PROCESSED_DIR','DATA_FEATURES_DIR','MLFLOW_TRACKING_URI','MLFLOW_ARTIFACT_ROOT','MLFLOW_EXPERIMENT_DEMAND','MLFLOW_EXPERIMENT_FARE','TLC_TRIP_YEAR','TLC_TRIP_MONTH','API_BASE_URL','DRIFT_DIR','MODEL_CARDS_DIR','RESPONSIBLE_DIR','ZONE_LOOKUP_PATH' | ForEach-Object {
    Remove-Item -LiteralPath ('Env:' + $_) -ErrorAction SilentlyContinue
}
$env:MPLBACKEND = 'Agg'
$env:PYTHONUNBUFFERED = '1'
& $capstonePy -c "from src.config import get_config; c=get_config(); print('Data:', c.raw_dir); print('Tracking:', c.mlflow['tracking_uri']); print('Model reference:', c.serving['model_stage'])"
```

Expect rehearsal-local data paths, `sqlite:///mlflow.db`, model reference `1`. A fresh checkout has no model version 1 yet; training creates it.

Run quality checks:

```powershell
& $capstonePy -m ruff check .
if ($LASTEXITCODE -ne 0) { throw 'Resolve the reported lint error before proceeding.' }
& $capstonePy -m pytest --cov=src --cov-report=term-missing --cov-report=xml:artifacts/rehearsal/coverage.xml
if ($LASTEXITCODE -ne 0) { throw 'Read the first failed test before changing anything.' }
git rev-parse HEAD | Set-Content -LiteralPath (Join-Path $capstoneEvidence 'commit.txt')
```

**Evidence:** actual test count, coverage, final pass and SHA. These checks alone do not establish phases 1-8.

## 3. Native phase 1: execute the complete data pipeline

Terminal A:

```powershell
& $capstonePy -m scripts.run_pipeline --year 2024 --month 1
if ($LASTEXITCODE -ne 0) { throw 'Pipeline failed; inspect its first actionable error.' }
$capstonePipeline = Get-Content data/processed/pipeline_summary.json -Raw | ConvertFrom-Json
$capstonePipeline | ConvertTo-Json -Depth 8
Copy-Item data/processed/pipeline_summary.json -Destination (Join-Path $capstoneEvidence 'pipeline-summary.json')
Get-ChildItem data/features -Filter '*.parquet' | Select-Object Name,Length
```

Validate the outputs and retain a forecast time derived from the data:

```powershell
@'
import json
from pathlib import Path
import pandas as pd
root = Path.cwd()
summary = json.loads((root / 'data/processed/pipeline_summary.json').read_text())
cleaning = summary['cleaning']
assert cleaning['input_rows'] == cleaning['output_rows'] + cleaning['total_dropped']
assert cleaning['output_rows'] > 0
assert summary['demand_feature_rows'] > 0 and summary['fare_feature_rows'] > 0
for problem in ('demand', 'fare'):
    for split in ('train', 'val', 'test'):
        path = root / f'data/features/{problem}_{split}.parquet'
        assert path.is_file() and len(pd.read_parquet(path)) > 0, path
history = pd.read_parquet(root / 'data/processed/demand_hourly.parquet')
context = {'target_hour': (pd.Timestamp(history.pickup_hour.max()) + pd.Timedelta(hours=1)).isoformat(),
           'zones': int(history.PULocationID.nunique()), 'history_rows': len(history)}
(root / 'artifacts/rehearsal/data-context.json').write_text(json.dumps(context, indent=2))
print(json.dumps(context, indent=2))
print('PASS: row conservation and nonempty feature splits')
'@ | & $capstonePy -
if ($LASTEXITCODE -ne 0) { throw 'Data-output checks failed.' }
```

**Understand:** NYC TLC January 2024 Yellow Taxi data -> validation/cleaning -> hourly demand aggregation -> features -> chronological train/validation/test files. The full source URL is constructed by `src/data/ingestion.py` using `config/config.yaml`. Show those paths and the actual summary.

If downloading fails, fix the network error first. As a deliberate fallback, copy **only** the raw January parquet and zone lookup from the original checkout into this checkout's `data/raw`, record that you reused a raw cache, and run `scripts.run_pipeline --year 2024 --month 1 --skip-download`. Do not copy processed data/models and describe them as freshly generated.

## 4. Native phase 2: train, evaluate, explain and register models

Terminal A; run **once** in this new registry:

```powershell
& $capstonePy -m scripts.train_models --n-trials 1
if ($LASTEXITCODE -ne 0) { throw 'Training or registration failed.' }
Get-ChildItem artifacts/demand,artifacts/fare -File | Select-Object Directory,Name,Length
```

This trains both XGBoost and LightGBM for both problems, with one Optuna trial per estimator. It is real full-split training with a bounded tuning budget. Winners are selected by **validation RMSE**, not test performance. Record your actual metrics; do not copy historical numbers from another execution.

Retain the resolved model identities and metrics:

```powershell
@'
import json
from pathlib import Path
from mlflow.tracking import MlflowClient
client = MlflowClient(tracking_uri='sqlite:///mlflow.db')
models = []
for name in ('taxi-demand-forecaster', 'taxi-fare-predictor'):
    version = client.get_model_version(name, '1')
    run = client.get_run(version.run_id)
    models.append({'name': name, 'version': version.version, 'run_id': version.run_id,
                   'source': version.source, 'metrics': run.data.metrics})
Path('artifacts/rehearsal/models.json').write_text(json.dumps(models, indent=2))
print(json.dumps(models, indent=2))
'@ | & $capstonePy -
if ($LASTEXITCODE -ne 0) { throw 'Registered version-1 model verification failed.' }
```

If training partially failed after registering one problem, diagnose that partial state before rerunning. Because the serving config pins version 1, a later training run creating version 2 does not automatically change the served model. Do not change to `latest` just to hide mismatched identities.

### Bootstrap block for every new terminal

Paste this at the top of terminals B, C and D, or to restore terminal A. It changes only the current shell's project overrides.

```powershell
$ErrorActionPreference = 'Stop'
$capstoneState = Get-Content 'C:\Data\BITS\labs\capstone-active-rehearsal.json' -Raw | ConvertFrom-Json
$capstoneSource = 'C:\Data\BITS\labs\taxi-forecasting-student'
$capstoneRepo = $capstoneState.Repo
$capstonePy = $capstoneState.Python
$capstoneEvidence = $capstoneState.Evidence
Set-Location -LiteralPath $capstoneRepo
'DATA_RAW_DIR','DATA_PROCESSED_DIR','DATA_FEATURES_DIR','MLFLOW_TRACKING_URI','MLFLOW_ARTIFACT_ROOT','MLFLOW_EXPERIMENT_DEMAND','MLFLOW_EXPERIMENT_FARE','TLC_TRIP_YEAR','TLC_TRIP_MONTH','API_BASE_URL','DRIFT_DIR','MODEL_CARDS_DIR','RESPONSIBLE_DIR','ZONE_LOOKUP_PATH' | ForEach-Object {
    Remove-Item -LiteralPath ('Env:' + $_) -ErrorAction SilentlyContinue
}
$env:MPLBACKEND = 'Agg'
$env:PYTHONUNBUFFERED = '1'
```

Terminal C, after bootstrap:

```powershell
& $capstonePy -m mlflow ui --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5010
```

Keep it running. Open <http://127.0.0.1:5010>. Locate both experiments, their winning runs, validation/test metrics, model artifacts and registered version 1. Match the run IDs to `artifacts/rehearsal/models.json`.

**Check:** two trained/registered models, finite measured metrics, saved model artifacts and inspectable run lineage. A running MLflow UI alone is not training evidence.

## 5. Native phase 3: live API and persisted batch inference

Terminal B, after bootstrap:

```powershell
& $capstonePy -m uvicorn src.serving.api:app --host 127.0.0.1 --port 8010
```

Keep it running. If the port is occupied, inspect the owning process and resolve that known collision; do not terminate arbitrary Python processes.

Terminal A: define a readiness check and a reusable genuine-request demonstration:

```powershell
function Test-CapstoneReady {
    param([string]$BaseUrl)
    $ready = $false
    for ($attempt = 0; $attempt -lt 45; $attempt++) {
        try {
            $health = Invoke-RestMethod -Uri ($BaseUrl + '/health')
            if ($health.status -eq 'ok' -and $health.fare_model_loaded -and $health.demand_model_loaded -and $health.history_hours -gt 0 -and $health.zones -gt 0) {
                $ready = $true
                break
            }
        } catch { }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) { throw ('API readiness failed: inspect the server log for ' + $BaseUrl) }
    return $health
}
function Invoke-CapstoneRequests {
    param([string]$BaseUrl, [string]$Label)
    $health = Test-CapstoneReady $BaseUrl
    $health | ConvertTo-Json | Tee-Object -FilePath (Join-Path $capstoneEvidence ($Label + '-health.json'))
    $fare = @{trip_distance=3.2;passenger_count=1;pu_location_id=161;do_location_id=236;pickup_datetime='2024-01-20T10:00:00';trip_duration_min=18.0}
    $context = Get-Content (Join-Path $capstoneEvidence 'data-context.json') -Raw | ConvertFrom-Json
    $demand = @{zone=132;target_hour=$context.target_hour}
    $fareResponse = Invoke-RestMethod -Method Post -Uri ($BaseUrl + '/predict/fare') -ContentType 'application/json' -Body ($fare | ConvertTo-Json)
    $demandResponse = Invoke-RestMethod -Method Post -Uri ($BaseUrl + '/predict/demand') -ContentType 'application/json' -Body ($demand | ConvertTo-Json)
    if ($null -eq $fareResponse.predicted_fare -or $fareResponse.predicted_fare -lt 0 -or -not $fareResponse.request_id) { throw 'Invalid fare response.' }
    if ($null -eq $demandResponse.predicted_pickups -or $demandResponse.predicted_pickups -lt 0 -or -not $demandResponse.request_id) { throw 'Invalid demand response.' }
    @{base_url=$BaseUrl;request=$fare;response=$fareResponse} | ConvertTo-Json -Depth 8 | Tee-Object -FilePath (Join-Path $capstoneEvidence ($Label + '-fare.json'))
    @{base_url=$BaseUrl;request=$demand;response=$demandResponse} | ConvertTo-Json -Depth 8 | Tee-Object -FilePath (Join-Path $capstoneEvidence ($Label + '-demand.json'))
    $forecast = @{horizon_hours=2;zones=@(132)} | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri ($BaseUrl + '/forecast/demand') -ContentType 'application/json' -Body $forecast | ConvertTo-Json -Depth 8 | Tee-Object -FilePath (Join-Path $capstoneEvidence ($Label + '-recursive-forecast.json'))
}
Invoke-CapstoneRequests 'http://127.0.0.1:8010' 'native'
& $capstonePy -m scripts.batch_forecast --horizon 1
if ($LASTEXITCODE -ne 0) { throw 'Native batch execution failed.' }
```

Check the persisted latest generation, rather than counting all historical rows:

```powershell
@'
import json, sqlite3
from pathlib import Path
with sqlite3.connect('predictions.db') as db:
    generation = db.execute('SELECT MAX(generated_at) FROM demand_forecasts').fetchone()[0]
    rows = db.execute('SELECT COUNT(*), COUNT(DISTINCT PULocationID), COUNT(DISTINCT pickup_hour) FROM demand_forecasts WHERE generated_at=?', (generation,)).fetchone()
    preview = db.execute('SELECT PULocationID,pickup_hour,predicted_pickups,model_version FROM demand_forecasts WHERE generated_at=? LIMIT 5', (generation,)).fetchall()
assert rows[0] > 0 and rows[0] == rows[1] and rows[2] == 1
result = {'generated_at': generation, 'rows_zones_hours': rows, 'preview': preview}
Path('artifacts/rehearsal/native-batch.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
'@ | & $capstonePy -
if ($LASTEXITCODE -ne 0) { throw 'Batch persistence verification failed.' }
```

January data has historically produced 253 zones; verify actual output rather than treating that number as universal. The batch writer stores the label `latest` even when serving config resolves numeric version 1. Use `models.json` for resolved lineage; do not treat that text label as a new registration.

Open <http://127.0.0.1:8010/docs> and identify the two prediction endpoints. The forecast time follows the saved history, not today's date. Do not enter a 2025/2026 target against January 2024 history and claim a valid live operational forecast.

### Optional L7 correspondence: validate rejection of an invalid request

This reinforces the API contract without changing code or model registration. Terminal A:

```powershell
$capstoneInvalidFare = @{trip_distance=-1;passenger_count=1;pu_location_id=161;do_location_id=236;pickup_datetime='2024-01-20T10:00:00';trip_duration_min=18.0} | ConvertTo-Json
try {
    Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8010/predict/fare' -ContentType 'application/json' -Body $capstoneInvalidFare
    throw 'An invalid negative distance was unexpectedly accepted.'
} catch {
    if (-not $_.Exception.Response -or [int]$_.Exception.Response.StatusCode -ne 422) { throw }
    @{status=422;finding='Negative trip distance rejected by request validation';request=($capstoneInvalidFare | ConvertFrom-Json)} | ConvertTo-Json -Depth 5 | Tee-Object -FilePath (Join-Path $capstoneEvidence 'native-invalid-fare.json')
}
```

Expect **422**, not a prediction. This is validation evidence, distinct from a valid request's numerical prediction.

## 6. Native phase 4 baseline: software quality

You already ran native lint/tests in step 2. Save their successful output and the actual SHA. A local test pass is the software-quality baseline; the hosted workflow and real container deployment in steps 9-10 supply the remaining phase-4 evidence. Do not mark hosted CI complete based on the existence of a YAML file.

If you specifically rehearse the repository's local runner, run this in terminal A:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/ci_local.ps1 -NoTerraform
if ($LASTEXITCODE -ne 0) { throw 'The local quality gate failed.' }
```

This repeats quality checks for familiarity; it is not necessary to rerun them during every subsequent phase. Terraform is deliberately skipped for this non-AWS route.

## 7. Native phases 5-6: monitoring, drift and Responsible AI

Terminal A:

```powershell
Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8010/metrics' -OutFile (Join-Path $capstoneEvidence 'native-metrics.txt')
Select-String -LiteralPath (Join-Path $capstoneEvidence 'native-metrics.txt') -Pattern 'http_requests_total|http_request_duration_seconds' | Select-Object -First 10
& $capstonePy -m scripts.monitoring.demo_drift_report --problem all --mode clean --output-dir artifacts/rehearsal/drift-clean
if ($LASTEXITCODE -ne 0) { throw 'Clean-sample drift report failed.' }
& $capstonePy -m scripts.monitoring.demo_drift_report --problem all --mode drift --output-dir artifacts/rehearsal/drift-shifted
if ($LASTEXITCODE -ne 0) { throw 'Shifted-sample drift report failed.' }
Get-Content artifacts/rehearsal/drift-shifted/demand_drift_metrics.json -Raw
& $capstonePy -m scripts.responsible.run_analysis
if ($LASTEXITCODE -ne 0) { throw 'Responsible-AI analysis failed.' }
Get-ChildItem artifacts/responsible -File | Select-Object Name,Length
Get-Content docs/model_cards/fare.md
```

**Monitoring checkpoint:** request/latency metrics exist after genuine inference. Explain that the clean report compares samples and the shifted report deliberately perturbs features to exercise PSI/KS detection. A clean sample is not guaranteed to have zero statistical flags. Neither report establishes an actual production incident or prediction-quality decay. This local route does not claim CloudWatch/SNS delivery.

**Responsible-AI checkpoint:** confirm both fairness JSON files, SHAP summary images and model cards exist. Read one measured result and limitation, not just the filename:

```powershell
@'
import json
from pathlib import Path
for problem in ('fare', 'demand'):
    report = json.loads(Path(f'artifacts/responsible/{problem}_fairness.json').read_text())
    print(problem, 'metrics:', report['metrics'])
    print('provenance:', json.dumps(report['provenance'], indent=2))
    for dimension in report['dimensions']:
        print(json.dumps(dimension))
    for filename in (f'artifacts/responsible/{problem}_shap_summary.png', f'docs/model_cards/{problem}.md'):
        assert Path(filename).is_file(), filename
'@ | & $capstonePy -
if ($LASTEXITCODE -ne 0) { throw 'Responsible-AI evidence is incomplete.' }
```

Choose one subgroup comparison with its sample counts, RMSE/disparity and threshold; explain any unavailable comparison or flag. Geographic/temporal subgroup error is not proof about protected attributes. SHAP describes model contributions, not causality. The fare model uses observed trip information; historical metrics do not prove pre-trip accuracy. Retain the demand split-boundary/fixed-origin limitations printed in its generated card.

For the L11 learning outcome, save a short `artifacts/rehearsal/responsible-finding.md` in your own words: model/run identity, measured subgroup finding with counts, interpretation/limit, proposed action, owner, success metric and review trigger. Keep the finding unresolved until a later evaluation demonstrates improvement; S3 publishing remains skipped on this route.

## 8. Native phase 7: dashboard interaction

Terminal D, after bootstrap:

```powershell
$env:API_BASE_URL = 'http://127.0.0.1:8010'
$env:DRIFT_DIR = Join-Path $capstoneEvidence 'drift-shifted'
& $capstonePy -m streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8510 --browser.gatherUsageStats false
```

Keep it running; open <http://127.0.0.1:8510>.

1. **Overview:** require both models loaded and nonempty history.
2. **Demand forecast:** reduce the default horizon to 1-3 hours and select one or two zones. Change the horizon/zone; confirm the graph changes from an actual API response.
3. **Fare prediction:** use the same plausible trip as step 5. Show the actual returned fare and estimated-duration status.
4. **Explainability:** prefer a fare example for the short recording. If showing demand SHAP, distinguish the raw model output from the API's nonnegative clipped prediction.
5. **Responsible AI:** select fare, then inspect the real subgroup result and SHAP plot you generated.
6. **Monitoring & KPIs:** inspect the real metrics/forecast panels and the shifted drift report. Revenue is illustrative, not realized business revenue.

Save one or two screenshots for preparation, but perform an actual interaction in the final video. A Streamlit health response or screenshot alone does not establish interaction. The report files and API are separate sources; ensure they come from this rehearsal's models.

For L12 correspondence, reconcile one displayed value against its API response or report, then record the panel, source/time, observed value, stakeholder meaning, proposed action/owner and freshness limit in `artifacts/rehearsal/dashboard-finding.md`. This is a learning/evidence note, not a source-code change requiring a rehearsal commit.

## 9. Docker route: package and run the newly trained models

Keep native terminals B/C/D running; the Docker route uses different ports. In terminal A, find the installed CLI and ensure Docker Desktop has its Linux engine running:

```powershell
$capstoneDocker = (Get-Command docker -ErrorAction SilentlyContinue).Source
if (-not $capstoneDocker) {
    $capstoneDocker = 'C:\Users\itwiz\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
}
if (-not (Test-Path -LiteralPath $capstoneDocker)) { throw 'Open Docker Desktop and locate its installed docker.exe before continuing.' }
& $capstoneDocker version
if ($LASTEXITCODE -ne 0) { throw 'Start/repair Docker Desktop engine connectivity first.' }
& $capstoneDocker info --format '{{.OSType}}'
if ($LASTEXITCODE -ne 0) { throw 'Docker engine check failed.' }
```

Require a server section and `linux`. If the CLI points to the wrong context, inspect `docker context ls` and choose the actual Desktop Linux context listed. Do not reinstall Docker just because a shell's PATH is stale. The original CLI location above is machine-specific and belongs in setup, not in the public video introduction.

### 9.1 Make the registry portable

Stop terminal C's MLflow UI with **Ctrl+C** and leave training/registry-writing commands idle while copying the SQLite registry. The native API is read-only for model loading and can stay running. The following helper overwrites only the new rehearsal's portable copy; never point it at the original registry as destination.

```powershell
Get-FileHash mlflow.db | Format-List
& $capstonePy -m scripts.make_mlflow_portable --src mlflow.db --dest mlflow.container.db --new-base file:///app/mlruns
if ($LASTEXITCODE -ne 0) { throw 'Portable registry conversion failed.' }
Get-FileHash mlflow.db,mlflow.container.db | Export-Csv -NoTypeInformation -LiteralPath (Join-Path $capstoneEvidence 'registry-hashes.csv')
```

After the copy, restart terminal C with the same MLflow UI command if you want both UIs available. The Linux copy rewrites artifact locations to `/app/mlruns`; it does not retrain the models.

### 9.2 Build the API image from this checkout

```powershell
& $capstoneDocker build --progress plain -f docker/Dockerfile --label ('org.opencontainers.image.revision=' + $capstoneState.Commit) -t $capstoneState.Image .
if ($LASTEXITCODE -ne 0) { throw 'Docker build failed; inspect the first failed layer.' }
& $capstoneDocker image inspect --format '{{.Id}} {{json .Config.Labels}}' $capstoneState.Image | Tee-Object -FilePath (Join-Path $capstoneEvidence 'docker-image.txt')
```

The image bakes in the portable registry, model artifacts and demand history. Its build includes the SQLAlchemy pin and an MLflow database import check. A build success still needs inference verification.

### 9.3 Deploy two named local containers

Check 8020 and 5020 are free. These names are unique to the rehearsal; do not remove an older container to make a name collision disappear.

```powershell
& $capstoneDocker run -d --name $capstoneState.Container -p 127.0.0.1:8020:8000 $capstoneState.Image
if ($LASTEXITCODE -ne 0) { throw 'API container startup command failed.' }
& $capstoneDocker run -d --name $capstoneState.MlflowContainer -p 127.0.0.1:5020:5000 $capstoneState.Image mlflow ui --backend-store-uri sqlite:////app/mlflow.db --host 0.0.0.0 --port 5000
if ($LASTEXITCODE -ne 0) { throw 'MLflow UI container startup failed.' }
& $capstoneDocker logs $capstoneState.Container
& $capstoneDocker inspect --format '{{.Id}} {{.Image}} {{json .State}} {{json .Mounts}}' $capstoneState.Container | Tee-Object -FilePath (Join-Path $capstoneEvidence 'docker-runtime.txt')
Invoke-CapstoneRequests 'http://127.0.0.1:8020' 'docker'
```

These `docker run` commands deliberately use **no host data mounts**. This verifies the baked image can load its own copied models/history. Inspect should show no added mounts. Responses should match native predictions for identical inputs and model identities, allowing normal numerical rounding. Open <http://127.0.0.1:8020/docs> and <http://127.0.0.1:5020>.

Compare the retained predictions in terminal A:

```powershell
$capstoneNativeFare = Get-Content (Join-Path $capstoneEvidence 'native-fare.json') -Raw | ConvertFrom-Json
$capstoneDockerFare = Get-Content (Join-Path $capstoneEvidence 'docker-fare.json') -Raw | ConvertFrom-Json
$capstoneNativeDemand = Get-Content (Join-Path $capstoneEvidence 'native-demand.json') -Raw | ConvertFrom-Json
$capstoneDockerDemand = Get-Content (Join-Path $capstoneEvidence 'docker-demand.json') -Raw | ConvertFrom-Json
if ([math]::Abs($capstoneNativeFare.response.predicted_fare - $capstoneDockerFare.response.predicted_fare) -gt 0.01 -or [math]::Abs($capstoneNativeDemand.response.predicted_pickups - $capstoneDockerDemand.response.predicted_pickups) -gt 0.01) {
    throw 'Native/container predictions differ. Check the model/run identities and input payloads.'
}
'PASS: native and container predictions agree within 0.01'
```

If a container exits or readiness stays degraded, inspect `docker logs <name>` and the actual MLflow/model-path error. HTTP 200 alone is insufficient. Native and Docker models should refer to the same training runs; the artifact URI prefix changes for Linux.

### 9.4 Run batch inference inside the API container

```powershell
& $capstoneDocker exec $capstoneState.Container python -m scripts.batch_forecast --horizon 1
if ($LASTEXITCODE -ne 0) { throw 'Container batch execution failed.' }
$capstoneContainerDb = $capstoneState.Container + ':/app/predictions.db'
& $capstoneDocker cp $capstoneContainerDb (Join-Path $capstoneEvidence 'docker-predictions.db')
if ($LASTEXITCODE -ne 0) { throw 'Could not retain the container batch database.' }
& $capstonePy -c "import sqlite3; c=sqlite3.connect('artifacts/rehearsal/docker-predictions.db'); print(c.execute('SELECT generated_at,COUNT(*),COUNT(DISTINCT PULocationID) FROM demand_forecasts GROUP BY generated_at ORDER BY generated_at DESC LIMIT 1').fetchone()); print(c.execute('SELECT * FROM demand_forecasts LIMIT 3').fetchall())"
Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8020/metrics' -OutFile (Join-Path $capstoneEvidence 'docker-metrics.txt')
& $capstoneDocker logs $capstoneState.Container 2>&1 | Out-File -LiteralPath (Join-Path $capstoneEvidence 'docker-api.log') -Encoding utf8
```

This batch database is inside the container, separately copied as evidence; it is not the native `predictions.db`. Raw database files need not be published publicly.

### 9.5 Point the dashboard at the Docker API

In terminal D, **Ctrl+C** to stop only that dashboard, then:

```powershell
$env:API_BASE_URL = 'http://127.0.0.1:8020'
$env:DRIFT_DIR = Join-Path $capstoneEvidence 'drift-shifted'
& $capstonePy -m streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8510 --browser.gatherUsageStats false
```

Refresh <http://127.0.0.1:8510>. The sidebar must show API port **8020**. Repeat a short demand/fare interaction. Label this **native dashboard + container API, same model/report lineage**. No cloud or Docker-hosted dashboard is implied.

**Docker checkpoint:** image ID and source label, container identity, running state, empty mount list, ready models, live inference, persisted container batch and request metrics. Keep this deployment running for the recording.

## 10. GitHub Actions: independently execute the clean route

Use the existing **GitHub-hosted Ubuntu runner**. Installing a self-hosted runner on your laptop is unnecessary for this route. Hosted containers are temporary and cleaned up after the job; the local Docker deployment remains the application used for interactive recording.

1. Open [your repository Actions page](https://github.com/itwizalekh/taxi-forecasting-student/actions).
2. Open **Capstone clean run** for the SHA in `artifacts/rehearsal/commit.txt`. The retained known successful run is [40186307700](https://github.com/itwizalekh/taxi-forecasting-student/actions/runs/40186307700), for commit `0ac3fd8...`. If your source SHA differs, find its own run.
3. Inspect **Execute clean pipeline, training, test deployment and analysis** and the summary. Require completed/success; do not equate queued/in-progress with passed.
4. To rehearse executing it yourself, choose **Re-run all jobs**. This reuses that run's original SHA/ref. Record the attempt number. No code push is needed for an unchanged implementation.
5. While it runs, inspect `.github/workflows/capstone.yml` and `scripts/capstone_golden_path.py`. The workflow installs dependencies and calls the exact entry point below:

```text
python -m scripts.capstone_golden_path --mode fresh
```

The fresh route checks lint/tests, generates data, trains/registers models, makes the registry portable, builds/deploys a temporary API container, performs API/batch/metrics/drift checks, generates Responsible AI artifacts and checks dashboard server readiness. It then saves evidence and cleans up its own temporary deployment. **Dashboard interaction remains a manual video requirement.**

Do not execute `--mode fresh` in either already-populated local checkout. Do not delete registries to evade its safeguard. Your manual native rehearsal demonstrates fresh local stages; this workflow demonstrates the automated clean entry point.

If the workflow fails, inspect the first failed stage and retained log. A requirements/source fix must be committed and pushed before a new hosted run can test it. Clicking rerun on an older SHA does not pick up uncommitted local changes. The workflow currently triggers on pushes to `responsible-analysis-evidence`; its manual button may be absent before it is present on the default branch.

### 10.1 Download and inspect the successful artifact

On the successful attempt's run page, scroll to **Artifacts** and download `capstone-evidence-<full-SHA>-attempt-<number>`. Sign in to GitHub if the download requires it. Keep the ZIP locally; the course portal lists only `.mp4` and `.txt` uploads.

Terminal A, after the ZIP has downloaded to your ordinary Downloads folder:

```powershell
$capstoneZipPattern = 'capstone-evidence-' + $capstoneState.Commit + '-attempt-*.zip'
$capstoneZips = @(Get-ChildItem -LiteralPath (Join-Path $env:USERPROFILE 'Downloads') -Filter $capstoneZipPattern | Sort-Object LastWriteTime -Descending)
$capstoneZips | Select-Object Name,LastWriteTime,Length
if ($capstoneZips.Count -eq 0) { throw 'Save the downloaded workflow artifact ZIP in Downloads, or set its actual path explicitly.' }
$capstoneZip = $capstoneZips[0]
$capstoneHosted = Join-Path $capstoneEvidence ('hosted-' + (Get-Date -Format yyyyMMdd-HHmmss))
Expand-Archive -LiteralPath $capstoneZip.FullName -DestinationPath $capstoneHosted
$capstoneFresh = @(Get-ChildItem -LiteralPath $capstoneHosted -Recurse -Filter manifest.json | ForEach-Object {
    $manifest = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
    if ($manifest.mode -eq 'fresh' -and $manifest.revision -eq $capstoneState.Commit -and $manifest.success -eq $true) {
        [pscustomobject]@{Path=$_.FullName;Manifest=$manifest}
    }
})
if ($capstoneFresh.Count -ne 1) { throw 'Expected one successful fresh manifest for the submitted SHA; inspect the selected artifact/attempt.' }
$capstoneFreshManifest = $capstoneFresh[0].Manifest
$capstoneFreshManifest | Select-Object mode,clean_execution,success,revision,workflow_url
$capstoneFreshManifest.stages | Format-Table name,status
if ($capstoneFreshManifest.clean_execution -ne $true -or @($capstoneFreshManifest.stages | Where-Object status -ne 'passed').Count -gt 0) { throw 'The artifact does not establish complete fresh execution.' }
$capstoneHosted | Set-Content -LiteralPath (Join-Path $capstoneEvidence 'hosted-artifact-location.txt')
```

Confirm the selected ZIP is the intended attempt, not merely an older successful download. Inspect the downloaded `SUMMARY.md`, `training.log`, `data-pipeline.log`, container build/start logs, health and request-response JSON, model/data lineage, batch generation, drift context, Responsible AI reports and dashboard log.

Hosted model/run IDs will differ from your newly trained local IDs. Their lineage must be internally consistent, not identical across independent executions. Record the actual workflow URL and attempt. A success badge without its stage evidence does not demonstrate all project phases.

### 10.2 Freeze the submitted implementation revision

Use the rehearsal SHA and corresponding successful workflow as your submission baseline. The public branch and README must expose the actual implementation and execution instructions. View the commit permalink while signed out to check public accessibility:

```powershell
$capstoneCommitUrl = $capstoneState.PublicRepo + '/tree/' + $capstoneState.Commit
$capstoneCommitUrl
git rev-parse HEAD
git status --short
```

Analysis generated model cards may show as local documentation changes. Preserve their new reports under your evidence; do not claim the public commit already contains their regenerated contents. Detailed hosted reports are in the retained artifact.

The recommended documentation commit is handled once before R1 in step 0.1. Do not make new commits merely because R1/R2/R3 generated outputs. Optional curated public evidence can be published in a deliberate separate commit after review, but that changes the submission SHA and requires its corresponding successful workflow. Keep large data/models/databases and private logs out of that commit.

### 10.3 Commit only if a genuine source fix is needed

1. Stop the active rehearsal at the failed stage and preserve its log. Write down the source file, exact failure and proposed correction.
2. Make/review the correction in the **original** `responsible-analysis-evidence` checkout. Keep the detached rehearsal as the historical failed attempt. Do not edit requirements differently in three rehearsals.
3. Run the relevant narrow check, then the full quality gate. Stage only the reviewed correction and any accompanying test; inspect the staged diff. Commit and push to `responsible-analysis-evidence`. Step 0.1 shows the commit/push pattern, but use the actual corrected filenames instead of the runbook filenames.
4. Inspect the new commit's hosted run. An older run's rerun cannot test the new fix.
5. Deliberately update the existing baseline record only after deciding to adopt that fix:

```powershell
Set-Location -LiteralPath 'C:\Data\BITS\labs\taxi-forecasting-student'
$capstoneNewBaseline = (git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot identify the corrected revision.' }
$capstoneBaselineFile = 'C:\Data\BITS\labs\capstone-rehearsal-baseline.json'
$capstonePreviousBaseline = Get-Content -LiteralPath $capstoneBaselineFile -Raw | ConvertFrom-Json
$capstonePreviousBaseline | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $capstoneEvidence 'superseded-baseline.json') -Encoding utf8
@{Commit=$capstoneNewBaseline;Branch='responsible-analysis-evidence';RecordedAt=(Get-Date -Format o)} | ConvertTo-Json | Set-Content -LiteralPath $capstoneBaselineFile -Encoding utf8
```

6. Close the failed round's known processes/containers using step 14.1 and begin a new clean checkout at the corrected baseline. The failed round remains evidence of the earlier SHA; do not relabel it a successful execution of the fix. If necessary, reuse a round label with its new unique timestamp.

## 11. Native phase 8 and concise live demonstration

You now have three complementary pieces of evidence:

1. An unused checkout that you actually built through native setup, pipeline, training, inference, reports and dashboard.
2. Those native models packaged into a working Docker API image and exercised by real requests and batch execution.
3. A successful **fresh** automated execution for a known commit on a GitHub-hosted runner.

The provided entry point requires Docker even in `verify` mode, and its container-status check assumes the original Compose stack. Do not point it at the standalone rehearsal containers and treat that as equivalent verification. The manual checks above verify your rehearsal containers; the hosted fresh run verifies the complete automation.

For a short genuine live pipeline run during recording, use the existing helper in terminal A:

```powershell
& $capstonePy -m scripts.capstone_live_pipeline
if ($LASTEXITCODE -ne 0) { throw 'Representative live pipeline failed.' }
$capstoneLive = Get-Content artifacts/capstone-live/latest.json -Raw | ConvertFrom-Json
$capstoneLive | Select-Object scope,original_rows,sample_rows,validation,exit_code
$capstoneLive.pipeline_summary | ConvertTo-Json -Depth 6
```

It samples one in every 100 source rows and executes the real pipeline into a new isolated `artifacts/capstone-live` folder. It does not replace your full-data training inputs or the Docker image. Say **representative live pipeline**; use the retained full-data training log for training evidence. Rehearse its actual duration once before recording.

For a quick inference demonstration:

```powershell
Invoke-CapstoneRequests 'http://127.0.0.1:8020' 'recording'
& $capstoneDocker exec $capstoneState.Container python -m scripts.batch_forecast --horizon 1
if ($LASTEXITCODE -ne 0) { throw 'Recorded container batch execution failed.' }
```

Every batch run appends a generation. These requests overwrite only the rehearsal evidence files with the `recording` label; use different labels if preserving multiple takes is useful. The native/Docker request helpers are defined in step 5; restore those function definitions if terminal A was restarted.

For phase 8 in the video: show the setup instructions, identify the fresh entry point, then trigger **Re-run all jobs** for the recorded successful SHA. Explain that a new attempt has started and show the completed previous attempt's traceable logs/artifact as the allowed evidence for long operations. Do not say the new attempt has passed before it finishes. If it fails later, retain and investigate that discrepancy before claiming it succeeded.

## 12. Evidence checklist and recording sequence

Mark each row using your actual rehearsal. A partial run is not a pass.

| Phase | Required working evidence | Your prepared screen/file |
| --- | --- | --- |
| Identity/revision | Full name, BITS ID, project details, webcam, public repo and SHA | Intro slide; commit permalink |
| 1 Data | Source, live pipeline execution, processed output and validation | Live sample helper + full pipeline summary |
| 2 Training | Training command/code, completed logs, evaluation and saved model | Terminal-A training output; `models.json`; MLflow UI |
| 3 Serving | One live API inference and batch predictions | Docker request helper; container batch; persisted rows |
| 4 CI/CD and infrastructure | Successful hosted workflow and deployed service/container status | GitHub attempt/stages; Docker image/container evidence |
| 5 Monitoring/drift | Real metrics and computed drift report/alert | Docker `/metrics`; clean/shifted report context |
| 6 Responsible AI | Relevant analysis with actual results | Fairness JSON/model card + SHAP plot |
| 7 Dashboard | Functional dashboard and real interaction | Browser at 8510, backend 8020 |
| 8 Golden Path | Clean instructions, triggered entry point and traceable full execution | Successful hosted fresh manifest/logs + rerun trigger |

Read the following claims aloud once, and make sure you understand them:

- What data was cleaned, why rows were dropped, and how train/validation/test were formed.
- What is predicted for fare versus demand; the units of RMSE/MAE and validation-based model selection.
- Which numeric model version/run is being served; where its artifact lives.
- Why a healthy HTTP endpoint is insufficient if models are not loaded.
- How batch output is persisted and distinguished by generation.
- How the native model registry becomes portable inside Linux.
- What GitHub Actions executed, which SHA it used and why its deployment is temporary.
- Why synthetic drift, fairness flags and SHAP are different evidence types.
- Which components are local, which are containers, and which ran on the hosted runner.
- What limitations remain; do not describe an unevaluated future forecast as production-ready.

### Recording plan: aim for about 11 minutes, stay below 12

| Elapsed | Show | Keep the explanation to |
| --- | --- | --- |
| 00:00-00:30 | Introduction, webcam, public repo and SHA | Identity, two prediction problems and non-AWS scope |
| 00:30-01:40 | Execute representative live pipeline | Source -> validation -> processed outputs; label the sample |
| 01:40-02:35 | Completed training evidence/MLflow | Validation choice, actual test metric, model artifact/run |
| 02:35-03:55 | Live API request and container batch | Input, output, request ID and saved generation |
| 03:55-05:05 | GitHub success and running container | Same implementation SHA, image ID, deployment/readiness |
| 05:05-06:05 | Metrics and drift report | Genuine requests, deliberate shift, PSI/KS result |
| 06:05-07:00 | Responsible AI finding | One measured explanation/subgroup result and limitation |
| 07:00-07:55 | Dashboard interaction | Change zone/horizon or fare input and show actual output |
| 07:55-10:15 | Golden Path | Setup, entry point trigger, completed fresh logs and stages |
| 10:15-10:50 | Repository/evidence close | Reproducibility and truthful remaining limitations |

The approximate 4/8/12-minute rows in the rubric are cumulative targets for phase groups, not four minutes per phase. Do not rely on informal permission for a 20-minute video.

Before the final take:

1. Stop terminal-A transcript capture with `Stop-Transcript` once preparation is complete; your final screen recording remains separate. Keep logs locally.
2. Create the intro slide privately with full name, BITS ID and project details. Do not put identity details in the public repository merely to satisfy the video.
3. Open required tabs: commit, successful workflow, MLflow 5010/5020, API docs 8020, dashboard 8510, metrics and selected reports.
4. Select one model/run family for narration; do not mix old local metrics with fresh hosted model identities.
5. Confirm container readiness and dashboard interaction again. Leave native/Docker services ready; no restart is required merely to record.
6. Increase terminal/browser text size; hide unrelated tabs and notifications. Do not display `.env`, tokens, credentials, full environment listings or confidential account information.
7. Record and play back a 20-second full-screen, microphone and webcam test.
8. Do one timed spoken rehearsal. If long-running work would exceed the budget, show its traceable completed evidence, as the official instructions permit.

## 13. Save submission details, export and upload

Prepare a `.txt` file outside the repository or inside ignored rehearsal artifacts. Replace the workflow URL with the actual successful run/attempt selected in step 10:

```powershell
$capstoneWorkflowUrl = Read-Host 'Paste the successful GitHub workflow URL selected for submission'
if ($capstoneWorkflowUrl -notlike 'https://github.com/itwizalekh/taxi-forecasting-student/actions/runs/*') { throw 'Use the actual run URL.' }
$capstoneSubmission = @(
    'Project: NYC Taxi Demand Forecasting and Fare Prediction',
    ('Public repository: ' + $capstoneState.PublicRepo),
    ('Implementation commit: ' + $capstoneState.Commit),
    ('Commit permalink: ' + $capstoneState.PublicRepo + '/tree/' + $capstoneState.Commit),
    ('Successful workflow: ' + $capstoneWorkflowUrl),
    'Execution instructions: README.md; docs/SETUP.md; scripts/capstone_golden_path.py',
    'Automated clean entry point: python -m scripts.capstone_golden_path --mode fresh (unused checkout with Docker)',
    'Deployment demonstrated: local Docker plus temporary GitHub-hosted test deployment; no AWS deployment claimed',
    'Detailed clean execution evidence: artifact attached to the successful workflow; see its attempt number'
)
$capstoneSubmission | Set-Content -LiteralPath (Join-Path $capstoneEvidence 'submission-details.txt') -Encoding utf8
```

Add the actual attempt number and any necessary data/model limitations in your own words. If the submitted SHA changed, update the file and ensure its workflow/evidence matches. Do not leave a placeholder or an earlier SHA in the final upload.

1. Export `.mp4` below 12 minutes; aim below 11:30.
2. Play the intro, live executions and ending. Verify readable text, audible own-voice explanation and webcam identity.
3. Check the public commit/README while signed out. Confirm it contains complete implementation and usable setup instructions; generated large models/data can be reproduced rather than checked into Git.
4. Upload the `.mp4` and `.txt` through the actual course portal. The supplied page permits those extensions; do not assume ZIP/PDF is accepted.
5. Complete the final submission action, wait for confirmation and save the receipt/status.
6. Only the most recent submission is kept. Verify any replacement video before replacing an accepted upload.

**Completion means a playable compliant video, accessible repository and confirmed portal submission.** A successful rehearsal, a selected upload file and a finished submission are separate checkpoints.

## 14. Troubleshooting and stop points

| Symptom | Next action |
| --- | --- |
| Wrong import/path or data from another checkout | Confirm `Get-Location`, explicit `$capstonePy`, session pointer and project overrides. Do not reuse an old `.env`. |
| MLflow SQLAlchemy import error | Confirm the selected environment uses the checked-in SQLAlchemy 2.0.55 pin; rebuild a Docker image after dependency changes. |
| Docker client exists, no server | Open Docker Desktop, wait for Linux engine readiness, inspect its exact error/context. |
| Port already in use | Identify the known service and choose/record a free rehearsal port consistently. Do not kill all Python/Docker processes. |
| API HTTP 200 but degraded JSON | Read startup logs; verify both registrations, artifact paths and nonempty demand history. |
| Registered version 2 but API still version 1 | The config is pinned. Keep model identity explicit; a new registration is not an automatic rollout. |
| Demand request fails or dashboard is slow | Use a target immediately after saved history, 1-3 hours and one or two zones. |
| SHAP/fairness file missing | Inspect responsible-analysis warnings and file paths; do not replace missing output with a historical example. |
| Workflow rerun ignores local fix | Reruns reuse the original SHA. Publish the reviewed fix and inspect its new run. |
| Clean-mode refusal in a populated checkout | Correct behavior. Use the unused hosted checkout; do not erase the working registry. |
| Dashboard readiness passed but interaction fails | Inspect API/browser errors and actual response. Server readiness is a narrower check. |
| Little time remains before recording/submission | Stop expanding scope; submit only phases with successful evidence. Preserve time for export/upload. |

AWS is a later extension only after the non-AWS submission is safely ready. Nothing in this runbook requires Terraform, cloud credentials or a billable cloud deployment.

### 14.1 Close R1/R2 before starting the next round

For the final chosen recording round, defer this shutdown until after submission. For an earlier full rehearsal:

1. Keep terminal A and its state intact. In B, C and D, press Ctrl+C to stop that round's native API, MLflow UI and Streamlit. Wait for the prompts. Close those terminals so their old variables cannot be confused with the next round's session.
2. In A, confirm the departing round's identity. Do this **before** running step 1 for the next round and replacing the shared pointer:

```powershell
$capstoneState | Select-Object Rehearsal,Repo,Commit,Container,MlflowContainer
Get-Content -LiteralPath (Join-Path $capstoneEvidence 'session.json')
```

3. If this round reached Docker startup, stop **only its named rehearsal containers**. If terminal A was restored, locate Docker again as in step 9 first:

```powershell
& $capstoneDocker stop $capstoneState.Container $capstoneState.MlflowContainer
```

4. Retain that round's session and a completion marker, without claiming the marker verifies every phase:

```powershell
@{Rehearsal=$capstoneState.Rehearsal;Repo=$capstoneRepo;Commit=$capstoneState.Commit;ClosedAt=(Get-Date -Format o);Note='Services stopped; phase success is established by the retained execution evidence, not this marker'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $capstoneEvidence 'round-closed.json') -Encoding utf8
Stop-Transcript -ErrorAction SilentlyContinue
```

5. Open a new terminal A, return to the original checkout, skip the one-time step-0.1 commit/freeze, and begin step 1 with R2 or R3. Its port check confirms the previous round released the shared rehearsal ports. Do not run that port preflight again while the same round's services are intentionally running.

Keep the checkout, models, logs and ZIP for each round. Stopped containers/images also remain; this preserves evidence and uses disk space. No recursive delete, Docker prune, Compose down against the original project or Git reset is part of this procedure. After final submission, use the same targeted shutdown for the last round.

## Reference basis

- Official submission-page text supplied by the learner: video <= approximately 12 minutes, public GitHub implementation, phase-specific executed evidence, representative live data/inference, traceable completed evidence for lengthy operations.
- Week37 recording, `00:00:05-00:00:25` and `01:28:27-01:28:46`: AWS is recommended and non-blocking, rather than stated as mandatory.
- Current checked-out `README.md`, `docs/SETUP.md`, `scripts/capstone_golden_path.py`, `scripts/capstone_live_pipeline.py`, Dockerfile, configuration and workflow; inspected at the revision recorded above. This runbook is an updated working document and is not automatically part of that earlier published SHA.
- [Docker run reference](https://docs.docker.com/reference/cli/docker/container/run/) for named containers and port publication.
- [GitHub workflow reruns](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs) for same-SHA rerun behavior.
- [Downloading workflow artifacts](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts) for artifact retrieval and access requirements.
