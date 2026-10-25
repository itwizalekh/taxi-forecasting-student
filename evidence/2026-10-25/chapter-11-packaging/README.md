# Chapter 11: repaired local quality and portable preparation

## Observed results

- Learner initial CI: lint failed; one forecast-reference assertion failed; 147 tests passed, 1 failed. Coverage 95.02% did not override failure.
- Repaired actual local runner: Ruff passed; **149 tests passed**, one warning; **95.02% coverage**, above 75%; exit code **0**. Terraform explicitly skipped with `-NoTerraform`.
- Portable registry: **22 artifact paths rewritten**; both configured numeric v1 model records map to container paths and corresponding local model files exist. Original registry hash remained unchanged.
- Docker CLI was not found on the execution session PATH. No image build, container runtime, hosted build or deployment was executed.

## Repair and scope

Ruff excludes archived evidence so recorded source snapshots and hashes stay unchanged. Maintained source/tests/scripts remain linted. The active teaching script's import spacing and unused loop variable were fixed. The forecast integration test explicitly checks latest and numeric 1 references, rather than assuming the local config always uses latest. No production prediction behavior or coverage threshold was changed.

`checked-sources/` retains the relevant source/config/build definitions from this check. `repair.patch` contains the three maintained-file repairs. The source commit and local changes are recorded in `manifest.json`: this was a working-copy check, not a claim that the commit alone contains every checked edit. The pre-existing config pin and release-gate source/tests remain local changes where shown.

`learner-initial-ci-failure.txt` is the original pasted output. `local-ci-after-repair.txt`, `local-ci-execution.json` and `coverage.xml` retain the actual repaired execution. An earlier agent execution stalled at local socket creation before TestClient requests; `execution-environment-note.txt` describes the diagnosis and the final retry with local access. That interruption is not an application assertion failure.

`portable-registry-verification.json` contains source/destination hashes, model identities and model-file hashes. The ignored databases/models/history are not committed as part of this evidence package. Path conversion and file presence do not establish Linux loading; container inference remains a separate requirement.

See [the phase table](PHASE_EVIDENCE_STATUS.md) and [the packaging instructions](../../../docs/CHAPTER_11_PACKAGING_NEXT_STEPS.md). The earlier finalized Chapter 10 package was not edited.

## Later Docker installation review

`docker-install-review.json` records the newly installed user-profile CLI and Compose, WSL2 Ubuntu, and valid Compose configuration. The engine connection still failed at inspection. This updates prerequisite knowledge, not container execution status. The packaging guide now uses the installed path and provides separate build, startup, readiness/inference and final evidence steps. Release-gate helper/test snapshots were added during this follow-up; they were already present in the recorded 149-test working-copy run.
