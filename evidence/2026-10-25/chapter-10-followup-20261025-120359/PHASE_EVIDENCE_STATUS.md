# Day 3 phase/evidence status

Evidence inventory updated 2026-10-25T07:36:26.482757+00:00 (UTC). Status describes inspected artifacts, not a full assessment grade.

| Phase / scope | Status | Evidence and observed result | Remaining requirement / limit |
| --- | --- | --- | --- |
| Local serving | Verified local execution | 200 health with both loaded flags; fare 200 and rejection 422; demand and recursive HTTP 200. [health.json](health.json), [fare-valid.json](fare-valid.json), [fare-invalid.json](fare-invalid.json), [demand-valid.json](demand-valid.json), [recursive-api.json](recursive-api.json), [api-startup-and-requests.log](api-startup-and-requests.log) | No container or hosted inference claim. |
| Batch persistence | Verified one generation | 759 unique zone/hour rows = 253 zones x 3 hours; 2024-02-01 00:00 through 02:00. [batch-console.txt](batch-console.txt), [batch-generations.csv](batch-generations.csv), [batch-forecast.csv](batch-forecast.csv), [lineage.json](lineage.json) | Generation 2026-10-25T07:01:12.370071+00:00; database label latest is resolved by the pinned-run sidecar. |
| Model/data lineage | Recorded for new pinned run | Both configured model names use numeric version 1; run IDs and config/history hashes are captured. [lineage.json](lineage.json), [config-diff.patch](config-diff.patch), [api-startup-and-requests.log](api-startup-and-requests.log) | Code revision 61ea01cb4bc5961c2f5ecd66ae87377c3217d327 plus recorded local changes; does not resolve old latest runs. |
| Quality checks: policy function | Verified function checks only | All seven Day 3 release_allowed cases pass; archived source and checker snapshots. [day-3-checker-verified.json](day-3-checker-verified.json), [day-3-checker-verification.log](day-3-checker-verification.log), [day-3-submission-snapshot.py](day-3-submission-snapshot.py), [day-3-checker-snapshot.py](day-3-checker-snapshot.py) | Tests use supplied cases; this is not approval of actual model quality or deploy permission. |
| Quality checks: served-model release approval | Not established by this package | No combined same-model/revision demand and fare quality thresholds and baseline decision is evidenced here. [toy-matched-origin-metrics.csv](toy-matched-origin-metrics.csv), [toy-source.json](toy-source.json), [reflection.md](reflection.md) | Toy metrics are synthetic. Existing strict-hour candidate assessment is a distinct model scope and does not automatically approve these served v1 models. |
| Container build | Pending / not evidenced in reviewed package | A successful build log tied to the intended source and immutable image identity is still required. None in this Day 3 package | Dockerfile/Compose configuration alone is insufficient. |
| Container runtime | Pending / not evidenced in reviewed package | Need running container identity/image, startup logs, readiness JSON and real inference from its exposed endpoint. None in this Day 3 package | Host Python/uvicorn success does not establish container runtime. |
| Hosted deployment | Pending / not evidenced in reviewed package | Need successful hosted workflow/task revision and image digest, stable runtime status, remote readiness and representative inference. None in this Day 3 package | No actual infrastructure/access failure is asserted; absence of evidence is not a diagnosed blocker. |
| Day 3 written assessment | Incomplete / unreviewed | answers.md still contains answer placeholders; the Day 3 reflection template also remains unfilled. Chapter 10 reflection.md is present, assessment answers/reflection are separate | Keep independent reasoning and assistance declaration with the submission. No score or mastery grade is assigned. |

## How to maintain this table

Update one phase at a time. For each claim retain its command/cwd, observed status or exit code, execution time, source revision plus relevant local changes, model/run/data identity, and linked output. Mark a phase verified only at the scope the evidence demonstrates. Use pending when required evidence is absent; use blocked only with an observed failure and diagnostic. Never copy a local pass into container or hosted rows.

The new batch generation is 2026-10-25T07:01:12.370071+00:00. Select that generation explicitly rather than summing all appended database rows. Its SQLite model_version remains latest due to the writer default; the separate lineage captures the pinned numeric demand model.

The checker snapshots were executed during this inventory update; they preserve the checked function source independently of later edits. Existing raw HTTP, batch, lineage, reflection and transcript files were not rewritten. No API, batch, container or hosted execution was rerun by this inventory update.

API and session logs can still grow while their writers are running. Manifest hashes are snapshots taken during this update, not proof the logs are finalized. Stop the API/transcript before creating a final hash inventory for publication.

Day 3 mastery remains **unreviewed** and capstone readiness remains **unverified**. Chapter 10 execution is one part of P4, whose remaining scope includes Chapters 11-12.
