# C10-A05: finish the capstone serving evidence

Run from `C:\Data\BITS\labs\taxi-forecasting-student`. These commands are
instructions for a new learner execution; they have not been executed by this guide.
Keep the existing `evidence/2026-10-25/chapter-10-serving` evidence unchanged.

## What is already done

The learner has demonstrated health, valid/invalid fare behavior, single demand,
three-hour recursive API forecasting, and the actual batch CLI. The saved batch
generation has 759 unique zone/hour rows, 253 zones and three hours, from
2024-02-01 00:00 through 02:00. Its CSV and console readback are already on GitHub
in commit `61ea01c`.

The remaining C10-A05 gaps are the toy metric calculation/explanation, complete
HTTP status/JSON/request-ID capture, and exact loaded-model lineage. The old
manifest intentionally leaves numeric loaded versions unknown. A registry lookup
today must not be used to retroactively fill those unknowns.

## 1. Start a separate follow-up folder

In the request/batch terminal, run:

```powershell
Set-Location C:\Data\BITS\labs\taxi-forecasting-student
$c10Out = "evidence/2026-10-25/chapter-10-followup-$(Get-Date -Format yyyyMMdd-HHmmss)"
New-Item -ItemType Directory -Path $c10Out | Out-Null
$env:C10_EVIDENCE_DIR = (Resolve-Path $c10Out).Path
Start-Transcript -Path "$c10Out/session.txt"
Get-Location
git rev-parse HEAD
git status --short
```

Use this same terminal for the remaining request/batch commands so the variable
and environment setting persist. Record the absolute folder path for the API terminal.

## 2. Recompute the author's matched-origin illustration

```powershell
@'
import hashlib, json, os
from pathlib import Path
import pandas as pd

out = Path(os.environ['C10_EVIDENCE_DIR'])
source = Path(r'C:/Data/BITS/capstone/study-notes/assets/learning-lab-reference/hourly/matched-origin-forecast.csv')
df = pd.read_csv(source)
assert not df.duplicated(['zone', 'hour']).any()
assert not df[['actual', 'one_step', 'recursive', 'lag_24']].isna().any().any()
records = []
for name in ['one_step', 'recursive', 'lag_24']:
    error = df[name] - df['actual']
    records.append({'method': name, 'rows': len(df),
                    'MAE': float(error.abs().mean()),
                    'RMSE': float(error.pow(2).mean() ** 0.5)})
result = pd.DataFrame(records)
result.to_csv(out / 'toy-matched-origin-metrics.csv', index=False)
(out / 'toy-source.json').write_text(json.dumps({
    'source': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'rows': len(df), 'zones': int(df.zone.nunique()),
    'hours': int(df.hour.nunique()), 'scope': 'author synthetic illustration'
}, indent=2), encoding='utf-8')
print(result.to_string(index=False))
'@ | .\.venv\Scripts\python.exe -
```

Expected for the unchanged supplied file (48 rows, 2 zones x 24 hours):

| Method    |      MAE |     RMSE |
| --------- | -------: | -------: |
| one_step  | 2.627336 | 3.606758 |
| recursive | 2.816925 | 3.965443 |
| lag_24    | 3.437500 | 4.697074 |

MAE is mean absolute error; RMSE is the square root of mean squared error. These
are pooled over the same 48 rows. One-step RMSE is about 0.359 pickups lower than
recursive RMSE. Rolling one-step inference can use newly available prior actuals;
fixed-origin recursion uses its earlier predictions instead. Lag-24 repeats the
previous day's hour. The ordering is observed here, not a universal guarantee.
Write your own explanation in `reflection.md`. These synthetic scores must not
be presented as scores of the real registered TLC model.

## 3. Pin a new execution and record lineage

The local registry inspected while preparing this guide contained version 1 of
both configured production names: `taxi-demand-forecaster` and
`taxi-fare-predictor`. The separately named strict-hourly candidate is not selected
by these default names. Do not switch models merely to improve this illustration.

For this new run, edit only `serving.model_stage` in `config/config.yaml`:

```yaml
  model_stage: "1"
```

This loader applies the same numeric version to both configured registry names.
Here both have version 1. If using a different registry where that is not true,
stop and choose an explicit per-model configuration instead of guessing.

Stop the old API with Ctrl+C in its terminal. A restart is required: editing the
file does not change an already-loaded service or clear its cache. Then start a
fresh process from the project root in that API terminal. The command below uses
the actual follow-up folder created for this learner run:

```powershell
$c10ApiOut = 'C:\Data\BITS\labs\taxi-forecasting-student\evidence\2026-10-25\chapter-10-followup-20261025-120359'
if (-not (Test-Path -LiteralPath $c10ApiOut -PathType Container)) {
    throw "The follow-up folder does not exist. Complete step 1 and use its folder path."
}
.\.venv\Scripts\python.exe -c "import logging, uvicorn; logging.basicConfig(level=logging.INFO); uvicorn.run('src.serving.api:app', host='127.0.0.1', port=8000)" 2>&1 |
    Tee-Object -FilePath (Join-Path $c10ApiOut 'api-startup-and-requests.log')
```

For a later run, set `$c10ApiOut` to that run's existing follow-up folder.
Verify startup succeeded and the log identifies numeric `/1` model references.
Keep this process running. Leave the config/history/registry unchanged until
the request and batch capture finish. Do not train/register models concurrently.

Back in the request/batch terminal, save the sidecar before making requests:

```powershell
@'
import hashlib, json, os, subprocess
from datetime import datetime, timezone
from pathlib import Path
from mlflow import MlflowClient
from src.config import PROJECT_ROOT, get_config
from src.utils.mlflow_utils import configure_mlflow

out = Path(os.environ['C10_EVIDENCE_DIR'])
cfg = get_config()
version = str(cfg.serving['model_stage'])
assert version == '1', 'Expected the explicitly pinned version 1 configuration'
configure_mlflow(cfg)
client = MlflowClient()
models = {}
for problem in ['demand', 'fare']:
    name = cfg.models['registry_' + problem]
    model = client.get_model_version(name, version)
    models[problem] = {'name': name, 'numeric_version': str(model.version),
        'uri': f'models:/{name}/{model.version}', 'run_id': model.run_id,
        'source': model.source}
history = Path(cfg.serving['demand_history_path'])
if not history.is_absolute():
    history = PROJECT_ROOT / history
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = {'captured_at_utc': datetime.now(timezone.utc).isoformat(),
    'cwd': str(Path.cwd()),
    'git_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
    'git_status': subprocess.check_output(['git', 'status', '--short'], text=True),
    'config_sha256': sha(PROJECT_ROOT / 'config/config.yaml'),
    'history_path': str(history), 'history_sha256': sha(history),
    'models': models,
    'scope': 'new pinned local run; does not identify historical latest executions'}
(out / 'lineage.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
(out / 'config-diff.patch').write_text(subprocess.check_output(
    ['git', 'diff', '--', 'config/config.yaml'], text=True), encoding='utf-8')
print(json.dumps(manifest, indent=2))
'@ | .\.venv\Scripts\python.exe -
```

The new sidecar links numeric versions, source runs, code revision, config and
history. Preserve the startup log alongside it. Config/source changes since the
recorded Git revision must remain documented; a revision alone does not identify
uncommitted changes. Keep the numeric pin until all evidence is collected.

## 4. Capture actual HTTP status, bodies and request IDs

This sends real HTTP requests to the running local API. Each saved JSON envelope
contains the input, actual HTTP status, response headers and raw response body.
In particular, a 422 response's request ID is in its response header even if
the validation body has no `request_id` field.

```powershell
@'
import json, os, uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import pandas as pd
from src.config import PROJECT_ROOT, get_config

out = Path(os.environ['C10_EVIDENCE_DIR'])
def capture(name, route, payload=None, expected=200):
    request_id = str(uuid.uuid4())
    headers = {'X-Request-ID': request_id}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = Request('http://127.0.0.1:8000' + route, data=data, headers=headers)
    try:
        response = urlopen(req, timeout=120)
    except HTTPError as error:
        response = error
    with response:
        status = response.code
        response_headers = dict(response.headers.items())
        returned_id = response.headers.get('X-Request-ID')
        raw = response.read().decode('utf-8')
    record = {'captured_at_utc': datetime.now(timezone.utc).isoformat(),
        'method': req.get_method(), 'url': req.full_url, 'request_json': payload,
        'sent_request_id': request_id, 'http_status': status,
        'response_headers': response_headers, 'response_request_id': returned_id,
        'response_body_raw': raw}
    (out / (name + '.json')).write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(name, status, returned_id, raw)
    assert status == expected, record
    assert returned_id == request_id, record
    return json.loads(raw)

health = capture('health', '/health')
assert health['status'] == 'ok'
assert health['fare_model_loaded'] and health['demand_model_loaded']
fare = dict(trip_distance=3.2, passenger_count=1, pu_location_id=161,
    do_location_id=236, pickup_datetime='2024-01-20T10:00:00', trip_duration_min=18.0)
valid = capture('fare-valid', '/predict/fare', fare)
assert valid['duration_estimated'] is False
capture('fare-invalid', '/predict/fare', dict(fare, trip_distance=-1), expected=422)
cfg = get_config()
path = Path(cfg.serving['demand_history_path'])
if not path.is_absolute():
    path = PROJECT_ROOT / path
history = pd.read_parquet(path)
assert 132 in set(history.PULocationID)
origin = pd.Timestamp(history.pickup_hour.max()) + pd.Timedelta(hours=1)
capture('demand-valid', '/predict/demand', {'zone': 132, 'target_hour': origin.isoformat()})
forecast = capture('recursive-api', '/forecast/demand', {'horizon_hours': 3, 'zones': [132]})
assert forecast['model_reference'] == '1', 'Confirm the old API was stopped and the pinned process started'
assert forecast['zones'] == 1 and len(forecast['points']) == 3
'@ | .\.venv\Scripts\python.exe -
```

If any check fails, keep the saved failure response and logs. Correct the smallest
failed boundary and use a new folder for the retest; do not overwrite failure
evidence. No predicted amount is hard-coded as a success condition.

## 5. Run the actual batch CLI and retain one generation

Run once, with no concurrent writers to the forecast database:

```powershell
.\.venv\Scripts\python.exe -m scripts.batch_forecast --horizon 3 2>&1 |
    Tee-Object -FilePath "$c10Out/batch-console.txt"
if ($LASTEXITCODE -ne 0) { throw "Batch command failed; retain its log before retesting." }
```

Then read back the latest generation (the log's generation in this exclusive run):

```powershell
@'
import hashlib, json, os, sqlite3
from pathlib import Path
import pandas as pd
from src.config import PROJECT_ROOT, get_config

out = Path(os.environ['C10_EVIDENCE_DIR'])
cfg = get_config()
assert str(cfg.serving['model_stage']) == '1'
lineage = json.loads((out / 'lineage.json').read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(PROJECT_ROOT / 'config/config.yaml') == lineage['config_sha256']
assert sha(Path(lineage['history_path'])) == lineage['history_sha256']
path = Path(cfg.serving.get('batch_db_path', 'predictions.db'))
if not path.is_absolute():
    path = PROJECT_ROOT / path
with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as conn:
    groups = pd.read_sql_query('''
        SELECT generated_at, model_version, COUNT(*) AS rows,
               COUNT(DISTINCT PULocationID) AS zones,
               MIN(pickup_hour) AS first_hour, MAX(pickup_hour) AS last_hour
        FROM demand_forecasts GROUP BY generated_at, model_version
        ORDER BY generated_at DESC LIMIT 5
    ''', conn)
    assert not groups.empty
    generation = str(groups.iloc[0]['generated_at'])
    rows = pd.read_sql_query('''SELECT * FROM demand_forecasts
        WHERE generated_at = ? ORDER BY PULocationID, pickup_hour''', conn,
        params=(generation,))
history = pd.read_parquet(lineage['history_path'])
known = set(history.PULocationID.astype(int))
origin = pd.Timestamp(history.pickup_hour.max()) + pd.Timedelta(hours=1)
assert len(rows) == len(known) * 3
assert set(rows.PULocationID.astype(int)) == known
assert not rows.duplicated(['PULocationID', 'pickup_hour']).any()
assert all(len(g) == 3 for _, g in rows.groupby('PULocationID'))
assert sorted(pd.to_datetime(rows.pickup_hour).unique()) == list(pd.date_range(origin, periods=3, freq='h'))
groups.to_csv(out / 'batch-generations.csv', index=False)
rows.to_csv(out / 'batch-forecast.csv', index=False)
lineage['batch'] = {'db_path': str(path), 'generated_at': generation,
    'rows': len(rows), 'zones': len(known), 'hours': 3,
    'stored_model_references': list(rows.model_version.unique()),
    'resolved_demand_model': lineage['models']['demand'],
    'note': 'batch writer defaults model_version to latest even with pinned loader; numeric lineage is recorded separately'}
(out / 'lineage.json').write_text(json.dumps(lineage, indent=2), encoding='utf-8')
print(groups.to_string(index=False))
print('Passed:', len(rows), '=', len(known), 'zones x 3 hours; generation:', generation)
'@ | .\.venv\Scripts\python.exe -
```

Important implementation detail: `run_batch` does not pass the numeric model
reference to `write_forecasts`; the database's `model_version` field still defaults
to `latest`. Do not relabel old database rows. The new sidecar and startup/CLI
logs explain which explicitly pinned model produced this new generation.

## 6. Finish the reflection and inventory

Write `reflection.md` in the follow-up folder, in your own words:

- Explain the matched-origin metric difference and distinguish the synthetic
  illustration from the live local execution.
- Identify the validation failure boundary: negative distance fails schema
  validation before fare feature construction and prediction. A useful retest
  changes just that invalid field and retains the new status/body/request ID.
- Explain the four stores and that the cache does not supply new observations.
- Explain why a fixed-origin third hour may use earlier predictions but not
  later observed actuals, and why these forecasts do not establish accuracy.
- State local API/batch completion and the exact model/data/generation links.
- Keep Chapter 11 container work and Chapter 12 hosted delivery explicit as
  completed, pending, skipped or blocked based on actual evidence.

After stopping transcript recording, hash the final evidence files:

```powershell
Stop-Transcript
Get-ChildItem -LiteralPath $c10Out -File |
    Where-Object Name -ne 'file-hashes.csv' |
    Get-FileHash -Algorithm SHA256 |
    Select-Object Path, Hash |
    Export-Csv -NoTypeInformation -Path "$c10Out/file-hashes.csv"
```

Hash the API log only after stopping its process/log writer, or regenerate the
hash inventory after the log is finalized. Hashes change when files change.

## P4 / Day 3 work outside this Chapter 10 closure

P4 covers Chapters 10-12. Day 3 also requires independent concept responses,
the `release_allowed` implementation and checker results, local quality checks,
and image/task/runtime/hosted evidence where applicable. Running supplied capture
commands alone does not establish independent assessment mastery.

Use the Day 3 checker only after completing your , and retain
its real output. Do not claim a pass before executing it:

```powershell
.\.venv\Scripts\python.exe C:\Data\BITS\capstone\study-notes\practice\check_learner_tasks.py --day 3 --submission C:\Data\BITS\capstone\study-notes\submissions\day-3\learner_tasks.py --output "$c10Out/day-3-code-checks.json"
```


```powershell
.\.venv\Scripts\python.exe C:\Data\BITS\capstone\study-notes\practice\check_learner_tasks.py --day 3 --submission C:\Data\BITS\capstone\study-notes\submissions\day-3\learner_tasks.py --output "$c10Out/day-3-code-checks.json"
```

In your phase/evidence table, distinguish local serving, batch persistence,
quality checks, container build/runtime and hosted deployment. A local success
does not complete the latter stages. Preserve any failed/blocked stages with
their actual diagnostic evidence.

Sources: [C10](../../../capstone/study-notes/chapters/10-serving.md),
[P4](../../../capstone/study-notes/PRACTICE_LABS.md),
[Day 3](../../../capstone/study-notes/assessments/DAY_3.md).

@'
import hashlib, json, os, sqlite3
from pathlib import Path
import pandas as pd
from src.config import PROJECT_ROOT, get_config

out = Path(os.environ['C10_EVIDENCE_DIR'])
cfg = get_config()
assert str(cfg.serving['model_stage']) == '1'
lineage = json.loads((out / 'lineage.json').read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(PROJECT_ROOT / 'config/config.yaml') == lineage['config_sha256']
assert sha(Path(lineage['history_path'])) == lineage['history_sha256']
path = Path(cfg.serving.get('batch_db_path', 'predictions.db'))
if not path.is_absolute():
    path = PROJECT_ROOT / path
with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as conn:
    groups = pd.read_sql_query('''
        SELECT generated_at, model_version, COUNT(*) AS rows,
               COUNT(DISTINCT PULocationID) AS zones,
               MIN(pickup_hour) AS first_hour, MAX(pickup_hour) AS last_hour
        FROM demand_forecasts GROUP BY generated_at, model_version
        ORDER BY generated_at DESC LIMIT 5
    ''', conn)
    assert not groups.empty
    generation = str(groups.iloc[0]['generated_at'])
    rows = pd.read_sql_query('''SELECT * FROM demand_forecasts
        WHERE generated_at = ? ORDER BY PULocationID, pickup_hour''', conn,
        params=(generation,))
history = pd.read_parquet(lineage['history_path'])
known = set(history.PULocationID.astype(int))
origin = pd.Timestamp(history.pickup_hour.max()) + pd.Timedelta(hours=1)
assert len(rows) == len(known) * 3
assert set(rows.PULocationID.astype(int)) == known
assert not rows.duplicated(['PULocationID', 'pickup_hour']).any()
assert all(len(g) == 3 for _, g in rows.groupby('PULocationID'))
assert sorted(pd.to_datetime(rows.pickup_hour).unique()) == list(pd.date_range(origin, periods=3, freq='h'))
groups.to_csv(out / 'batch-generations.csv', index=False)
rows.to_csv(out / 'batch-forecast.csv', index=False)
lineage['batch'] = {'db_path': str(path), 'generated_at': generation,
    'rows': len(rows), 'zones': len(known), 'hours': 3,
    'stored_model_references': list(rows.model_version.unique()),
    'resolved_demand_model': lineage['models']['demand'],
    'note': 'batch writer defaults model_version to latest even with pinned loader; numeric lineage is recorded separately'}
(out / 'lineage.json').write_text(json.dumps(lineage, indent=2), encoding='utf-8')
print(groups.to_string(index=False))
print('Passed:', len(rows), '=', len(known), 'zones x 3 hours; generation:', generation)
'@ | .\.venv\Scripts\python.exe -
