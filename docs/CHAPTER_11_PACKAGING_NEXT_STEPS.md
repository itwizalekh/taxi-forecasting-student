# Chapter 11: local quality and container packaging

Run from `C:\Data\BITS\labs\taxi-forecasting-student`.
The Chapter 11 evidence folder is
`evidence/2026-10-25/chapter-11-packaging`.

## Repair the observed local CI failure

The original learner output is preserved in `learner-initial-ci-failure.txt`.
Its lint stage and one integration test failed. Passing 75% coverage did not
override those failures.

The repair keeps archived Chapter 10 source snapshots unchanged, because their
bytes are evidence and have recorded hashes. Ruff now excludes `evidence/`,
consistent with the existing exclusions for data/artifacts. Maintained source,
tests and scripts are still linted. The active teaching script's import spacing
and unused loop variable were corrected.

The forecast API test now explicitly checks both `latest` and numeric `1`
references, with pytest restoring the config after each case. It verifies that
the response follows the configured model reference. Changing the serving pin
back to latest merely to satisfy a hard-coded test would hide this test defect.

The runner and its 75% coverage threshold are unchanged:

```powershell
.\scripts\ci_local.ps1 -NoTerraform
```

Use the retained local CI log and execution JSON for the actual outcome. This
command checks local software behavior; it does not score the real model or run
Terraform, a hosted workflow, an image build or a deployment.

## Portable registry preparation

The actual helper was executed:

```powershell
.\.venv\Scripts\python.exe -m scripts.make_mlflow_portable --src mlflow.db --dest mlflow.container.db --new-base file:///app/mlruns
```

It rewrote 22 artifact paths. Both configured numeric version-1 model records
resolve to `/app/mlruns/...` paths, and their corresponding local model files
exist. The original registry's SHA256 was unchanged. Any existing portable copy
was backed up before conversion; the verification JSON records its backup path.
The portable database remains Git-ignored.

This establishes path conversion and file presence, not that the models load
inside Linux. Container startup and real inference remain separate checks.

## Docker installation review and engine prerequisite

The follow-up inspection on 25 October located the installed Docker CLI at:
`C:\Users\itwiz\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe`.
It reports client version 29.7.2 and Compose v5.4.0. The Docker engine pipe was
unavailable: installation is present, but engine connectivity is not ready.
WSL reports the Ubuntu distribution as version 2 (stopped at inspection).
`docker compose ... config --quiet` passed without requiring a running engine.
The older preparation record correctly describes the earlier missing-PATH state;
`docker-install-review.json` records this later inspection separately.

### 1. Open Docker Desktop and check the engine

Start Docker Desktop from the Windows Start menu and complete its first-run
setup. In Settings > General, use the WSL 2 based engine if the option is shown.
This Python image requires Linux containers. If Desktop is in Windows container
mode, switch to Linux containers. Wait for the engine to report running.

Docker's [official WSL guide](https://docs.docker.com/desktop/features/wsl/)
explains these settings. Windows terminal commands do not require you to start
Ubuntu manually or enable Ubuntu terminal integration. The WSL1 warning in the
status output does not by itself block this WSL2 route.

Open a fresh PowerShell terminal and run:

```powershell
Set-Location C:\Data\BITS\labs\taxi-forecasting-student
.\.venv\Scripts\Activate.ps1
# Add the installed CLI to this terminal only if its inherited PATH is stale.
$env:Path = 'C:\Users\itwiz\AppData\Local\Programs\DockerDesktop\resources\bin;' + $env:Path
docker version
docker compose version
docker context ls
docker info --format '{{.OSType}}'
```

Require a server section in `docker version` and `linux` from `docker info`.
If the pipe error persists, check Desktop's engine status first. If Desktop
shows a working Linux engine but your selected context still points elsewhere,
select the Desktop Linux context shown by `docker context ls` (commonly
`docker context use desktop-linux`). Do not guess a context name not in that list.
If Desktop itself reports a WSL/update/reboot problem, retain that exact error
and complete its requested setup before trying a build.

### 2. Keep the project/model inputs consistent

Use the `labs` checkout above, not the separate `capstone` checkout. Stop the
host Python API and host MLflow UI with Ctrl+C in their terminals: Compose needs
ports 8000 and 5000. This leaves the registered models and history intact.

The existing local config pins `serving.model_stage` to numeric 1. Keep that pin
for this evidence run. The pin is a recorded local change; the original recorded
configuration is preserved in the checked-source evidence. Do not assume a fresh
GitHub checkout contains that local config edit.

Verify prerequisites and regenerate the portable copy after any registrations
change. Keep model training/registry writers and other containers stopped while
copying the registry:

```powershell
'mlflow.db', 'mlruns', 'data/processed/demand_hourly.parquet' |
    ForEach-Object { if (-not (Test-Path -LiteralPath $_)) { throw "Missing prerequisite: $_" } }
.\.venv\Scripts\python.exe -m scripts.make_mlflow_portable --src mlflow.db --dest mlflow.container.db --new-base file:///app/mlruns
if ($LASTEXITCODE -ne 0) { throw 'Portable registry preparation failed.' }
docker compose -f docker/docker-compose.yml config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Compose configuration is invalid.' }
```

A code-only clone lacks the ignored registry, artifacts and history. Reuse the
existing local files; no retraining is needed to resume this checkout. The image
build needs network access for its Python base image, OS packages and pip packages.

### 3. Create a new Docker execution evidence folder

Use the same terminal for the following steps so `$c11Out` stays defined:

```powershell
$c11Out = Join-Path (Get-Location).Path ("evidence/2026-10-25/chapter-11-docker-run-" + (Get-Date -Format yyyyMMdd-HHmmss))
New-Item -ItemType Directory -Path $c11Out | Out-Null
git rev-parse HEAD | Set-Content "$c11Out/source-commit.txt"
git status --short | Set-Content "$c11Out/working-tree-status.txt"
Get-FileHash config/config.yaml,mlflow.container.db,data/processed/demand_hourly.parquet |
    Export-Csv -NoTypeInformation "$c11Out/packaged-input-hashes.csv"
docker version 2>&1 | Out-File "$c11Out/docker-version.txt" -Encoding utf8
```

### 4. Build, then start the stack

```powershell
docker compose -f docker/docker-compose.yml build api mlflow-ui 2>&1 |
    Tee-Object -FilePath "$c11Out/compose-build.log"
$c11BuildExit = $LASTEXITCODE
$c11BuildExit | Set-Content "$c11Out/build-exit-code.txt"
if ($c11BuildExit -ne 0) { throw 'Build failed: retain its log before troubleshooting.' }

docker compose -f docker/docker-compose.yml up -d 2>&1 |
    Tee-Object -FilePath "$c11Out/compose-start.log"
$c11StartExit = $LASTEXITCODE
$c11StartExit | Set-Content "$c11Out/start-exit-code.txt"
if ($c11StartExit -ne 0) { throw 'Stack startup failed: inspect the startup log.' }

docker compose -f docker/docker-compose.yml ps --all |
    Tee-Object -FilePath "$c11Out/compose-status.txt"
docker compose -f docker/docker-compose.yml images |
    Tee-Object -FilePath "$c11Out/compose-images.txt"
```

The first build can take several minutes. Native Docker progress may appear red
when PowerShell handles stderr; judge success by the retained exit code and build
result. Starting detached returns to the prompt, but application model loading
may still be in progress. Inspect the logs before sending requests:

```powershell
docker compose -f docker/docker-compose.yml logs --no-color api |
    Tee-Object -FilePath "$c11Out/api-startup.log"
```

Wait for application startup completion. If readiness is degraded, retain the
model-loading error and fix the artifact/config boundary; do not call it a pass.

### 5. Identify the running container and verify real inference

```powershell
$c11ApiId = docker compose -f docker/docker-compose.yml ps -q api
if (-not $c11ApiId) { throw 'No API container exists; inspect startup logs.' }
docker inspect --format '{{.Id}} {{.Image}} {{.Config.Image}}' $c11ApiId |
    Set-Content "$c11Out/api-container-and-image.txt"
docker inspect --format '{{json .State}}' $c11ApiId |
    Set-Content "$c11Out/api-container-state.json"
docker inspect --format '{{json .Mounts}}' $c11ApiId |
    Set-Content "$c11Out/api-container-mounts.json"

$c11Health = Invoke-RestMethod -Uri http://127.0.0.1:8000/health
$c11Health | ConvertTo-Json | Tee-Object -FilePath "$c11Out/container-health.json"
if ($c11Health.status -ne 'ok' -or -not $c11Health.fare_model_loaded -or -not $c11Health.demand_model_loaded) {
    throw 'HTTP success alone is insufficient: one or more models are not ready.'
}

$c11Fare = @{
    trip_distance = 3.2
    passenger_count = 1
    pu_location_id = 161
    do_location_id = 236
    pickup_datetime = '2024-01-20T10:00:00'
    trip_duration_min = 18.0
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/predict/fare -ContentType application/json -Body $c11Fare |
    ConvertTo-Json | Tee-Object -FilePath "$c11Out/container-fare.json"
$c11Demand = @{ zone = 132; target_hour = '2024-02-01T00:00:00' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/predict/demand -ContentType application/json -Body $c11Demand |
    ConvertTo-Json | Tee-Object -FilePath "$c11Out/container-demand.json"

docker compose -f docker/docker-compose.yml logs --no-color |
    Out-File "$c11Out/compose-runtime.log" -Encoding utf8
```

The demand target matches this exercise's saved January history. If your history
changes, choose the appropriate supported origin. Keep request IDs from actual
responses. Open http://127.0.0.1:8000/docs for the API and http://127.0.0.1:5000
for the container MLflow UI.

The supplied Compose health check only verifies HTTP success; our separate
readiness check verifies both model-loaded flags. The container identity and
mount evidence link these localhost requests to the intended Compose process.

Compose mounts the portable database, artifacts and data. Label the successful
route **Compose with mounts**. It does not independently prove an unmounted image
can load its baked artifacts. Local images may have no registry RepoDigest before
being pushed; retain the immutable local image ID instead of inventing a digest.

### 6. Finish, hash and update the phase table

When the exercise is finished:

```powershell
docker compose -f docker/docker-compose.yml down 2>&1 |
    Tee-Object -FilePath "$c11Out/compose-stop.log"
Get-ChildItem -LiteralPath $c11Out -File |
    Where-Object Name -ne 'file-hashes.csv' |
    Get-FileHash -Algorithm SHA256 |
    Select-Object Path,Hash |
    Export-Csv -NoTypeInformation "$c11Out/file-hashes.csv"
```

Mark container build verified only after a successful build and recorded image
identity; mark container runtime verified only after the readiness and actual
fare/demand requests succeed. Hosted CI/deployment stays unverified until its
separate evidence exists. Preserve failed attempts rather than overwriting them.

## Boundaries and next evidence

| Phase | Evidence needed |
| --- | --- |
| Local software quality | Ruff plus passing full tests/coverage and exit code |
| Portable preparation | Source/destination registry hashes, converted paths and model file identities |
| Container build | Successful build output and exact image identity tied to source/config |
| Container runtime | Container/image identity, loaded flags, fare/demand responses and logs |
| Hosted quality/deployment | Actual hosted run/task/image identities, stability and remote inference |

The observed initial CI failure and repaired pass demonstrate a real quality-gate
failure/repair. They are not a deliberately injected disposable-copy fault; keep
that distinction if doing the tutorial's optional controlled-failure practice.

Do not manually start CodeBuild assuming it is test-only: the current buildspec
can deploy on a manual start. No hosted build is needed to complete these local
repair and preparation steps.
