# Capstone submission steps

Use `C:\Data\BITS\labs\taxi-forecasting-student` throughout. Budget the final 90 minutes for recording, export and portal submission. These steps assume the Docker API already verified on 25 October is still running. No AWS or Terraform commands are required.

Prepared locally: `.github/workflows/capstone.yml`, `scripts/capstone_golden_path.py` and `scripts/capstone_live_pipeline.py`. They are not committed or published by preparation. The clean GitHub workflow has not yet run. Verify mode passed local lint, 149 tests, existing-model lineage, container status, real inference, metrics, 253-row batch and controlled drift; dashboard was explicitly skipped in that diagnostic. The representative live pipeline also succeeded in about five seconds.

## 1 Open a working PowerShell terminal

```powershell
Set-Location C:\Data\BITS\labs\taxi-forecasting-student
$env:Path = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin;" + $env:Path
git branch --show-current
git rev-parse HEAD
docker compose -f docker/docker-compose.yml ps
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected branch: `responsible-analysis-evidence`. Require `status: ok`, both model flags true, history hours and zones greater than zero. Keep the running API and MLflow containers. If they were stopped, run `docker compose -f docker/docker-compose.yml up -d` and repeat readiness. The existing repaired images should be reused; stop if actual startup fails.

## 2 Install the missing dashboard dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dashboard.txt
if ($LASTEXITCODE -ne 0) { throw 'Dashboard dependency installation failed.' }
.\.venv\Scripts\python.exe -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Resolve the reported dependency error before continuing.' }
```

## 3 Review and publish the prepared route

This publishes the selected working source to your existing public repository. The workflow starts automatically on a push to the named branch. No merge to main is necessary.

```powershell
git diff -- README.md config/config.yaml docker/Dockerfile requirements.txt
git status --short
git add -- README.md config/config.yaml docker/Dockerfile requirements.txt .github/workflows/capstone.yml scripts/capstone_golden_path.py scripts/capstone_live_pipeline.py docs/CAPSTONE_SUBMISSION_STEPS.md
git diff --cached --stat
git -c core.whitespace=cr-at-eol diff --cached --check
```

Review the staged files, including the two new scripts and workflow in your editor. They should contain no credentials. The model version pin and SQLAlchemy repair are intentional. Other unstaged documentation/old evidence remains on disk; it is not deleted by these commands.

```powershell
git commit -m "Add reproducible capstone workflow and submission runbook"
if ($LASTEXITCODE -ne 0) { throw 'Commit failed.' }
git push origin responsible-analysis-evidence
if ($LASTEXITCODE -ne 0) { throw 'Push failed; complete GitHub sign-in or inspect the error.' }
git rev-parse HEAD
```

Copy the complete commit identifier. In a browser, open:

- Repository branch: https://github.com/itwizalekh/taxi-forecasting-student/tree/responsible-analysis-evidence
- Actions: https://github.com/itwizalekh/taxi-forecasting-student/actions

Open **Capstone clean run** for that commit. If GitHub asks you to enable Actions on this fork, enable it and push another reviewed commit, or rerun the available workflow. The push trigger works on this branch; the manual Run workflow button may be absent while the workflow is not on the default branch.

The job installs Python 3.11 dependencies and executes the actual route from an unused checkout: pipeline, one-trial training, registry preparation, Docker build/test deployment, real inference, batch, monitoring/drift, responsible analysis and dashboard server readiness. This deployment exists on the temporary GitHub runner and is removed after its evidence is collected. The local demo containers remain running.

Leave this running while completing steps 4–7. Check it again after 20–30 minutes. Do not label it successful until it is green. If it fails, open the first failed stage and its log before retrying. The job's artifact includes retained failure evidence when available.

## 4 Execute the complete local verification

```powershell
.\.venv\Scripts\python.exe -m scripts.capstone_golden_path --mode verify
if ($LASTEXITCODE -ne 0) { throw 'Read the failed stage and its evidence log before continuing.' }
$capstoneRun = Get-Content artifacts/capstone-runs/latest-verify.json -Raw | ConvertFrom-Json
$capstoneManifest = Get-Content -LiteralPath $capstoneRun.manifest -Raw | ConvertFrom-Json
$capstoneManifest | Select-Object mode,success,revision,output_dir
$capstoneManifest.stages | Format-Table name,status
```

Require `success: True` and every listed stage passed. Do not use `--skip-dashboard` for this completion check. Verify mode reuses existing data/training, checks the existing deployment, creates a new one-hour batch generation and writes separate drift/evidence outputs. Its successful result is not a clean generation claim. Clean generation is independently established only when the fresh workflow succeeds.

The script briefly checks dashboard startup on port 8765 and stops only that temporary dashboard. It never stops or rebuilds the existing API. A browser interaction is still required in step 5.

## 5 Open the dashboard and perform a real interaction

In a second PowerShell terminal:

```powershell
Set-Location C:\Data\BITS\labs\taxi-forecasting-student
$capstoneRun = Get-Content artifacts/capstone-runs/latest-verify.json -Raw | ConvertFrom-Json
$env:API_BASE_URL = 'http://127.0.0.1:8000'
$env:DRIFT_DIR = Join-Path $capstoneRun.output_dir 'drift'
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8501
```

Keep that terminal running. Open http://127.0.0.1:8501 in your browser.

1. Confirm Overview reports both models loaded.
2. Select **Demand forecast**. Set the horizon to 1–3 hours and select one or two zones.
3. Change a zone/horizon and show the resulting actual forecast graph.
4. Select **Monitoring & KPIs** and inspect the computed drift panel.
5. Select **Responsible AI**, then fare or demand, and inspect a real report/SHAP plot.

If an interaction errors, retain the message and fix the specific source/API issue. Server health alone does not establish the dashboard interaction. Forecasts use the saved January 2024 history; the deliberately shifted drift samples are a controlled demonstration, not a production incident.

## 6 Rehearse the live pipeline and inference commands

Use your first terminal. The pipeline helper creates a clearly labelled one-in-100 sample spanning the January source file, then runs the actual cleaning/aggregation/features/splits pipeline in a new `artifacts/capstone-live` folder. It leaves the full-data model inputs and running API history untouched.

```powershell
.\.venv\Scripts\python.exe -m scripts.capstone_live_pipeline
if ($LASTEXITCODE -ne 0) { throw 'Representative pipeline failed.' }
$livePipeline = Get-Content artifacts/capstone-live/latest.json -Raw | ConvertFrom-Json
$livePipeline | Select-Object scope,sample_rows,validation
$livePipeline.pipeline_summary | ConvertTo-Json -Depth 5
```

Observed rehearsal: 29,647 source-sample rows -> 27,254 clean rows, plus nonempty demand and fare feature tables. Explain that the recorded model-training metrics come from the full-data run, not this sample. Re-running creates a separate output folder.

Run these genuine predictions and batch command:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
$fareRequest = @{
  trip_distance=3.2; passenger_count=1; pu_location_id=161; do_location_id=236
  pickup_datetime='2024-01-20T10:00:00'; trip_duration_min=18.0
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/predict/fare -ContentType application/json -Body $fareRequest
$demandRequest = @{zone=132;target_hour='2024-02-01T00:00:00'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/predict/demand -ContentType application/json -Body $demandRequest
.\.venv\Scripts\python.exe -m scripts.batch_forecast --horizon 1
```

Expected batch result: 253 rows, 253 zones, one hour. Each batch execution appends a separate generation. Use the current generation and the verification lineage when interpreting it; the database's historical `latest` text alone does not identify the numeric model.

## 7 Prepare evidence screens

Open and prearrange:

- Public branch and final commit page. Match the Actions run's head commit.
- http://127.0.0.1:5000 for the existing container MLflow UI. Show the version-1 demand/fare run, metrics and model artifact. Existing local test RMSE: demand 8.7022, fare 3.4717. The fresh runner produces separate run identities; do not mix them.
- http://127.0.0.1:8000/docs for API contracts, if useful.
- http://127.0.0.1:8000/metrics for real request/latency metrics.
- Dashboard browser tab.
- The local verification `SUMMARY.md`, `manifest.json`, model/data lineage, drift context and responsible evidence in the output folder.
- The successful **Capstone clean run**, its summary and downloaded `capstone-evidence-...` artifact. Confirm `mode: fresh`, `clean_execution: true`, `success: true` and all stages passed. A green job that only installs dependencies is insufficient.

The fresh job regenerates model cards in its own checkout. Existing local cards describe local version-1 models. Their model/run IDs are expected to differ across independent executions.

If full clean execution is still failing after two hours of the sprint, stop open-ended development and prepare a truthful reduced-scope submission. The supplied instructions do not guarantee a numerical score by phase. Do not label phases 4/8 complete based solely on the locally prepared workflow/script files.

## 8 Save concise public evidence and submission details

The workflow artifact retains detailed evidence. For convenient repository review, you may additionally copy the final local logs/reports (not databases/models/data) into a new evidence folder after checking for confidential content:

```powershell
$capstoneRun = Get-Content artifacts/capstone-runs/latest-verify.json -Raw | ConvertFrom-Json
$capstoneEvidence = Join-Path 'evidence/2026-10-25' ('submission-verification-' + (Get-Date -Format yyyyMMdd-HHmmss))
New-Item -ItemType Directory -Path $capstoneEvidence | Out-Null
Copy-Item -LiteralPath $capstoneRun.output_dir -Destination (Join-Path $capstoneEvidence 'verification') -Recurse
```

If you commit/push this evidence, a fresh workflow starts for that new commit too. Use its final successful run for the recording and submission. Avoid repeated unnecessary pushes. Keeping the downloaded detailed artifact alongside the video and linking the existing successful run is also useful; the portal excerpt only permits .mp4/.txt, so do not assume it accepts ZIP uploads.

Prepare a plain-text submission file with the public branch URL, full final commit identifier, successful workflow URL and concise execution instructions. Use your actual identity only where the submission requires it. Do not publish your BITS ID in the repository just to satisfy the video introduction.

## 9 Record approximately eleven minutes

First record a 20-second test and play it back to check full-screen capture, microphone, readable text and webcam. Keep a usable first take until a replacement is verified.

| Elapsed | Show and explain |
| --- | --- |
| 00:00–00:30 | Full name, BITS ID, project details, webcam identity; public repository and commit |
| 00:30–01:40 | Run `capstone_live_pipeline`; show sample label, processed output and validation |
| 01:40–02:35 | Completed full-data MLflow training run, metrics and model artifact |
| 02:35–03:50 | Live API request(s) and `batch_forecast --horizon 1` |
| 03:50–05:00 | Successful clean Actions run and its temporary deployment stage; live local Compose status/readiness |
| 05:00–06:00 | Real `/metrics`, controlled drift context and computed result |
| 06:00–06:50 | One relevant SHAP/subgroup finding and limitation |
| 06:50–07:45 | Actual dashboard interaction |
| 07:45–10:15 | Setup instructions, Golden Path entry point, completed clean-run stage evidence |
| 10:15–10:45 | Public repository/commit, evidence location and concise scope/limitations |

For phase 8, show the completed fresh run first. To trigger the full clean entry point during recording, rerun that same successful GitHub job using **Re-run jobs / Re-run all jobs**. Explain that long operations are starting again and use the previous successful attempt's logs/artifact for completed evidence, as the instructions permit. Do not suggest the newly triggered attempt has already passed. You can also run local `--mode verify` and explicitly identify its reused inputs; that command alone does not replace the clean run.

Do not run `--mode fresh` in the populated local demonstration checkout. It deliberately refuses existing outputs. Do not remove its safeguards or delete the working registry to make it proceed.

If a later triggered attempt fails, preserve that outcome and resolve the discrepancy before claiming the rerun succeeded. Retain the completed earlier attempt and exact revision as historical evidence.

## 10 Export, check and submit

1. Export an .mp4 with duration below 12 minutes; aim below 11:30.
2. Play the beginning, live demonstrations and end. Check audio, webcam identity and readability.
3. Verify public access to the submitted repository branch/commit while signed out.
4. Put the final repository URL, commit and successful workflow URL in the .txt file if the portal has no dedicated URL field.
5. Upload through the actual course portal, complete its final submission action and wait for confirmation.
6. Retain the submitted video/text locally and save the receipt/confirmation. Only the most recent submission is kept, so verify any replacement before submitting it.

Completion is the portal's confirmed submission, not a selected file or upload progress bar. A working implementation, a successful recorded demonstration and a confirmed submission are separate checkpoints.
