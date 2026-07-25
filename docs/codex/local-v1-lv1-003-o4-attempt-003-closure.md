# Local v1 LV1-003 O4 Attempt 003 Closure

Status: `ATTEMPT_003_CONSUMED_RECOVERY_REQUIRED`

Attempt `LV1-003-O4-ATTEMPT-003` is consumed. No retry, recovery action, image removal, or further
execution is authorized.

## Exact Invocation And Failure

The attempted candidate was `7f819bb91c475b4b9fa69b975e629810a7254020`, tree
`7ff30d4625e6b086809703889376d34cdb0998b5`. The operator command was exactly
`make local-v1-lv1-003-o4-producer-run`, whose module command remained
`uv run python -m scripts.local_v1_lv1_003_o4_producer`.

Make exited `2`. The producer exited `1` with refusal code `recovery_required`. The run identity was
`20260725T125344Z-6460809b`, and the unique Compose project was
`ithildin-local-v1-o4-6460809b`.

The gate and producer runtime were entered. Owner-only runtime and receipt directories and the
candidate snapshot were created. The Docker mutation and image-build phase was entered, and three
base-service image outputs were observed afterward. Cleanup did not complete. This closure does not
claim that any later runtime phase was entered.

## Diagnosis Boundary

The final refusal code is `recovery_required`. This closure does not claim that an earlier primary
error existed, and it does not claim a value for one. The final refusal may have replaced an earlier
error or may have originated in cleanup itself. The absence of the run-specific Hermes image while
all three base-service images remained makes a Hermes bridge image-build failure a hypothesis, not
a proven diagnosis. No diagnosis-only command, repair, recovery, cleanup, or retry is authorized by
this closure.

The closure does not claim absence of a provider call, API start, Node enrollment, Hermes
invocation, or credential output. It claims only that mutation/build was entered, cleanup remained
incomplete, and no successful O4 evidence was created.

## Point-In-Time Residue Observation

A read-only, exact-run-scoped observation after the attempt found zero project-labeled containers,
volumes, and networks and no run-specific Hermes image. It found three retained `linux/arm64`
images, each with zero containers at observation time and the exact project and service labels:

1. `ithildin/api-o4:6460809b` —
   `sha256:19dc658884e9298b7966e5fb10c80874afaa33956e565b55dd0a30e8a02bd5d6`
2. `ithildin/ui-o4:6460809b` —
   `sha256:4b530eb0fc350c433089d88ddd75d03042e633a5b23a0fdeaaeb77c58f75b6b7`
3. `ithildin/node-o4:6460809b` —
   `sha256:0d85000f6172508554524f276d4051170e53a6c3fc79cbc5dc1b0c051b682c81`

The project label was
`com.docker.compose.project=ithildin-local-v1-o4-6460809b`; service labels were the corresponding
`ithildin-api`, `ithildin-ui`, and `ithildin-node` values. This is a point-in-time observation only,
not current live truth, a general Docker absence claim, a cleanup-completed claim, or permission to
remove the images.

## Quarantined Receipt

The owner-only `0700` receipt root
`var/local-v1-lv1-003-o4-receipts/20260725T125344Z-6460809b` is intentionally retained. Its
119-byte `0600` `disposition.json` is `quarantined_not_published` with digest
`sha256:03bceb292828f68440c2183438f856edd4b291130d6f276b9418a3d2ad967992`.

The `0600` candidate manifest is 96,628 bytes with digest
`sha256:ed011c2f54edde19a959f85e77c575aa57e47094c99f15473faecf9d1190df96`.
It binds the exact attempted commit and tree. The retained candidate snapshot is owner-only `0500`
and contains 663 files. The report base is absent. The quarantine is failure evidence, not
successful O4 evidence.

The closure validator directly reads both Attempt 002 and Attempt 003 retained receipts,
manifests, and snapshots independently of Git ignore state. It requires no-follow owner identity;
exact modes, sizes, digests, manifest paths, snapshot bytes, and directory contents; an empty
owner-only runtime base; and an absent report base. Missing, changed, extra, symlink, or special
entries invalidate the closure without restoring authority.

## Tracked Closure Scope

The Attempt 003 closure scope is exactly six tracked paths:

1. `docs/codex/local-v1-lv1-003-o4-attempt-003-closure.json`
2. `docs/codex/local-v1-lv1-003-o4-attempt-003-closure.md`
3. `docs/codex/local-v1-lv1-003-o4-execution-authorization.json`
4. `docs/codex/local-v1-lv1-003-o4-execution-authorization.md`
5. `scripts/local_v1_lv1_003_o4_execution_authorization_check.py`
6. `tests/test_local_v1_lv1_003_o4_execution_authorization_check.py`

The existing three exact evidence-root child patterns in `.gitignore` cover both retained runs.
Ignore state is convenience only and does not suppress direct retained-evidence validation.

## Closed Authority

Attempts 001, 002, and 003 are consumed. Retry and automatic retry are false, the attempt budget is
zero, and all 19 authority fields are false.

Any recovery, cleanup, image removal, repaired candidate, or new attempt requires separate
disposition and proportional independent review. Release, promotion, production, and UAT remain
false.
