# Local v1 LV1-003 O4 Attempt 006 Disposition

Status: `ATTEMPT_006_CONSUMED_APPLICATION_STARTUP_DIAGNOSTIC_REQUIRED_NO_LIVE_AUTHORITY`

Attempt `LV1-003-O4-ATTEMPT-006` is consumed. The attempt budget is zero, retry and automatic retry
are false, and all 19 authority fields are false. No further execution, image recovery, evidence
deletion, release, promotion, production action, or UAT action is authorized.

## Exact Attempt

The attempted candidate was commit `d4c1d322a9d3faf24422009b7bc40f73544250af`, tree
`9acbfc6ee270613518c4c5cc74b2719604946c46`. The operator command was exactly
`make local-v1-lv1-003-o4-producer-run`, whose module command remained
`uv run python -m scripts.local_v1_lv1_003_o4_producer`.

The run identity was `20260725T183846Z-b00570b3`; its unique Compose project was
`ithildin-local-v1-o4-b00570b3`. The primary and outward failure code was
`base_services_start_failed`.

## Bounded Diagnostic Facts

The exact retained diagnostic records that both the base-service and Hermes bridge builds
completed, all four image identities were bound, and the highest completed producer stage was `7`.
The cleanup failure list is empty and `recovery_required` is false.

The base-service diagnostic classified `ithildin-api` as `service_exited_nonzero` and
`ithildin-ui` as `service_created`. The bounded API container-state diagnostic completed with
`cause_code` `api_application_exit_nonzero_no_engine_error` and health `unhealthy`. It found no
OOM-killed or container-engine-error condition. These closed facts establish only that the
application exited nonzero without a reported engine error; the exact application root cause
remains unknown.

The four bound identities were:

1. `ithildin/api-o4:b00570b3` —
   `sha256:e75264be1cf08effff08d122324410435955dd6c816c506f1b1d5da5614527a5`
2. `ithildin/ui-o4:b00570b3` —
   `sha256:2d97d8658498978da4ca610dbd51e0b6aa55bf9b35f0815a002b65054a208ce5`
3. `ithildin/node-o4:b00570b3` —
   `sha256:1ae93646eca07cf3472ea70952ee83083228eb1924aebf91ab6fa0cd54cb0ebb`
4. `ithildin/hermes-node-bridge-o4:b00570b3` —
   `sha256:1a1eb3d53d106428f1266e8ce1d1799fd6b6074449673767a2a2016da647794f`

The diagnostic is bounded failure evidence. It contains no raw Docker or application logs,
credentials, provider output, model output, prompts, tool results, environment, mounts,
configuration, commands, or arbitrary paths.

## In-Run Cleanup And Point-In-Time Postcheck

The reviewed bounded diagnostic records successful in-run cleanup for the exact bound Attempt 006
resources: `cleanup_failure_codes` is empty and `recovery_required` is false. This is an
attempt-scoped cleanup result, not generic or ongoing Docker absence.

A separate read-only, exact-run-scoped postcheck after the failure observed:

- all four exact run references absent;
- all four exact bound image IDs absent;
- zero exact-project containers;
- zero exact-project volumes;
- zero exact-project networks;
- the temporary Docker configuration cleaned;
- the Attempt 006 runtime run directory and runtime plaintext absent; and
- the owner-only runtime base retaining only
  `attempt-003-image-recovery-001-consumed.json`.

These are point-in-time exact-run postconditions only. They are not ongoing live truth, a general
Docker absence claim, or evidence of successful O4 execution. On this exact evidence no image
recovery is required or authorized.

## Retained Evidence

The owner-only `0700` receipt root
`var/local-v1-lv1-003-o4-receipts/20260725T183846Z-b00570b3` contains exactly:

1. `candidate/`
2. `candidate-manifest.json`
3. `diagnostic.json`
4. `disposition.json`

The exact retained files are:

- `disposition.json`: owner-only `0600`, 128 bytes,
  `sha256:5a84070039cc153416cf6fcc3a12c9f13bbd921befa97ee4b33a861a309b9d7a`
- `diagnostic.json`: owner-only `0600`, 7,270 bytes,
  `sha256:5203fad9e028b6596c46358de00ab5a24e78ab314dbb582f9c3184ad4ac296b5`
- `candidate-manifest.json`: owner-only `0600`, 96,772 bytes,
  `sha256:001e9c51992339079de8560d372a463ce7b30b4d9ff1be38cd516e7148f78fcd`
- `candidate/`: owner-only `0500`, exactly 664 files

The validator reads Attempts 002 through 006 retained receipts directly and independently of Git
ignore state. It requires exact run entries, file identities, owner/group, modes, sizes, digests,
manifest paths, candidate commit/tree, snapshot bytes, and directory contents using descriptor-
anchored no-follow reads. It also requires the exact retained Attempt 003 image-recovery consumption
receipt as the sole runtime-base entry. Missing, changed, extra, symlink, or special evidence fails
closed without restoring authority.

## Exact Closure Candidate

No future closure child commit or tree is stated. The validator accepts only a clean, single-parent
immediate child of the attempted candidate whose committed diff is exactly these eight paths:

1. `Makefile`
2. `README.md`
3. `docs/codex/local-v1-lv1-003-o4-attempt-006-disposition.json`
4. `docs/codex/local-v1-lv1-003-o4-attempt-006-disposition.md`
5. `docs/codex/local-v1-lv1-003-o4-execution-authorization.json`
6. `docs/codex/local-v1-lv1-003-o4-execution-authorization.md`
7. `scripts/local_v1_lv1_003_o4_execution_authorization_check.py`
8. `tests/test_local_v1_lv1_003_o4_execution_authorization_check.py`

All producer, bridge, policy, tool-manifest, and runtime paths remain byte-identical to the attempted
candidate.

## Closed Authority And Next Action

Attempts 001 through 006 are consumed. Attempt 003 image recovery remains consumed and closed. The
Attempt 006 budget is zero, retry is false, and all 19 authority fields are false. Release,
promotion, production, credential custody, new powers, new tools, evidence deletion, and UAT remain
false.

The next action is a separately reviewed application-emitted closed startup-stage diagnostic. It
must not scrape logs or persist raw application output. This disposition does not guess the
application root cause, includes no producer change, and grants no execution authority.
