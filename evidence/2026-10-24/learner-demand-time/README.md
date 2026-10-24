# Learner demand-time audit: staged source and evidence

Prepared 24 October 2026 from the learner's cumulative `scripts/learner_demand_time_audit.py`. Stage-specific files were carved by the assistant at the learner's request, retaining the calculations. They are cumulative, standalone entry points: Stage 2 repeats Stage 1; Stage 3 repeats Stages 1 and 2. The original cumulative source was not edited.

## Source-to-evidence map

| Stage | Standalone source, relative to repository root | Original learner console output | Final verified fresh console capture |
|---|---|---|---|
| 1: existing boundaries | `scripts/learner_demand_time_stage_01.py` | [01-boundaries.txt](01-boundaries.txt) | [Stage 1 rerun](stage-runs-v2/stage-01-console.txt) |
| 2: duplicate keys and shared hours | `scripts/learner_demand_time_stage_02.py` | [02-boundary-rows.txt](02-boundary-rows.txt) | [Stage 2 rerun](stage-runs-v2/stage-02-console.txt) |
| 3: whole-hour masks and conservation | `scripts/learner_demand_time_stage_03.py` | [03-whole-hour-splits.txt](03-whole-hour-splits.txt) | [Stage 3 rerun](stage-runs-v2/stage-03-console.txt) |

The original logs are preserved byte-for-byte. Exact source versions at those historical executions were not previously archived; these newly carved files must not be represented as historical snapshots from before they were created. Fresh reruns establish their verified source/output relationship now. Comment clarifications were applied in carved files; Stage 3 additionally includes reviewed fail-fast assertions and full-value conservation. This is guided learner work with disclosed assistant assistance.

## Manifest and identity

[stage-runs-v2/manifest.json](stage-runs-v2/manifest.json) records:

- SHA256 byte hashes before/after execution of the three directly read input files: `data/features/demand_train.parquet`, `demand_val.parquet`, `demand_test.parquet`.
- SHA256 hashes of all stage sources, original cumulative source, and evidence runner.
- SHA256 hashes of the three untouched historical logs and each fresh stdout/stderr file.
- Commands, working directory, UTC execution times, return codes, Python/platform identity and installed pandas/NumPy/PyArrow versions.
- Input and source stability checks; every stage returned exit code zero.

The manifest's Git HEAD is the parent commit at capture time. The commit that contains this manifest identifies the final committed evidence bundle; embedding that commit's own ID inside its contents would be circular. Input Parquet files remain ignored by Git and must be retained separately for exact-byte reproduction. Scoped `.gitattributes` rules disable newline conversion for these sources and evidence files so Git preserves the exact captured bytes across checkouts. Editing or reformatting a hashed file requires a new capture rather than updating the old manifest's execution claims.

## Findings verified

- Original demand boundary hours are shared across adjacent splits, with no duplicated zone/hour keys.
- The learner's whole-hour split yields 460/58/58 hours and 116,380/14,674/14,674 rows.
- Both strict time comparisons pass; all 576 hours belong to exactly one split.
- All 145,728 rows and zone/hour keys remain, and every original column value is unchanged.
- Ruff passes for the four added executable scripts. Console captures are UTF-8.

Stage scripts do not write new Parquet splits or train models. Existing pipeline defaults remain unchanged. Lag/rolling-feature verification is a later learning stage, not a completed claim of this learner bundle.

## Reproduce

From the repository root, using the existing environment:

```powershell
Set-Location C:\Data\BITS\labs\taxi-forecasting-student
.\.venv\Scripts\python.exe -m scripts.learner_demand_time_stage_01
.\.venv\Scripts\python.exe -m scripts.learner_demand_time_stage_02
.\.venv\Scripts\python.exe -m scripts.learner_demand_time_stage_03
```

To generate a new complete console/hash bundle:

```powershell
.\.venv\Scripts\python.exe -m scripts.capture_learner_stages --output evidence/2026-10-24/learner-demand-time/stage-runs-v3
```

The runner refuses to overwrite an existing output directory. The final reviewed capture is `stage-runs-v2`; any `stage-runs-v1` directory is an earlier preparation capture, not the final committed bundle.

For later stages, preserve these stage files and add a new stage source, log and manifest. Commit each completed stage so its source remains recoverable.
