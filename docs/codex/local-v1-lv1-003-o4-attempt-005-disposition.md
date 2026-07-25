# Local v1 LV1-003 O4 Attempt 005 Disposition

Status: `ATTEMPT_005_CONSUMED_API_EXIT_DIAGNOSTIC_REQUIRED_NO_LIVE_AUTHORITY`

Attempt `LV1-003-O4-ATTEMPT-005` is consumed. The attempt budget is zero, retry and automatic retry
are false, and all 19 authority fields are false. No further execution, image recovery, evidence
deletion, release, promotion, production action, or UAT action is authorized.

## Exact Attempt

The attempted candidate was commit `affba0570ae15e897f92629966d445ad563ec5ff`, tree
`8b262e7efa55db72b5402f6924ec938e2d06d85f`. The operator command was exactly
`make local-v1-lv1-003-o4-producer-run`, whose module command remained
`uv run python -m scripts.local_v1_lv1_003_o4_producer`.

The run identity was `20260725T172408Z-b806c1bd`; its unique Compose project was
`ithildin-local-v1-o4-b806c1bd`. The primary and outward failure code was
`base_services_start_failed`.

## Bounded Diagnostic Facts

The exact retained diagnostic records that both the base-service and Hermes bridge builds
completed, all four image identities were bound, and the highest completed producer stage was `7`.
The cleanup failure list is empty and `recovery_required` is false.

The fixed bounded base-service diagnostic completed. It classified `ithildin-api` as
`service_exited_nonzero` and `ithildin-ui` as `service_created`. Those classifications do not state
why the API exited and do not establish a root cause.

The four bound identities were:

1. `ithildin/api-o4:b806c1bd` —
   `sha256:e4ca0c62c670f38f150bb09f42a356e0d5b2956cf7cb56a3bd729004a1ffcb33`
2. `ithildin/ui-o4:b806c1bd` —
   `sha256:a1e78335549b50210d6f607dc0335e0263d60fc2d9ff5e4e9ac6a303af3b9b38`
3. `ithildin/node-o4:b806c1bd` —
   `sha256:a876ac0a41cd64e57c5b6f28839363d831187323733280929a74ffe27a0e8294`
4. `ithildin/hermes-node-bridge-o4:b806c1bd` —
   `sha256:702bd8613619440585ff6f2011c2e49fb07aed587223eab9d2298604e775ebf9`

The diagnostic is bounded failure evidence. It does not contain raw Docker logs, credentials,
provider output, model output, prompts, tool results, or arbitrary paths.

## In-Run Cleanup And Point-In-Time Postcheck

The reviewed bounded diagnostic records successful in-run cleanup for the exact bound Attempt 005
resources: `cleanup_failure_codes` is empty and `recovery_required` is false. This is an
attempt-scoped cleanup result, not generic or ongoing Docker absence.

A separate read-only, exact-run-scoped postcheck after the failure observed:

- all four exact run references absent;
- all four exact bound image IDs absent;
- zero exact-project containers;
- zero exact-project volumes;
- zero exact-project networks;
- the Attempt 005 runtime run directory and runtime plaintext absent; and
- the owner-only runtime base retaining only
  `attempt-003-image-recovery-001-consumed.json`.

These are point-in-time exact-run postconditions only. They are not ongoing live truth, a general
Docker absence claim, or evidence of successful O4 execution. On this exact evidence no image
recovery is required or authorized.

## Retained Evidence

The owner-only `0700` receipt root
`var/local-v1-lv1-003-o4-receipts/20260725T172408Z-b806c1bd` contains exactly:

1. `candidate/`
2. `candidate-manifest.json`
3. `diagnostic.json`
4. `disposition.json`

The exact retained files are:

- `disposition.json`: owner-only `0600`, 128 bytes,
  `sha256:5a84070039cc153416cf6fcc3a12c9f13bbd921befa97ee4b33a861a309b9d7a`
- `diagnostic.json`: owner-only `0600`, 7,059 bytes,
  `sha256:e4064aacddd05b2e835fcb7064ace5b88be1e3dab8328a7ebb888da899114738`
- `candidate-manifest.json`: owner-only `0600`, 96,772 bytes,
  `sha256:dddff25f5969763100f54963dfba8f3f1d74ee16f6bc5ef580d4797ae6a75a0f`
- `candidate/`: owner-only `0500`, exactly 664 files

The validator reads Attempts 002 through 005 retained receipts directly and independently of Git
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
3. `docs/codex/local-v1-lv1-003-o4-attempt-005-disposition.json`
4. `docs/codex/local-v1-lv1-003-o4-attempt-005-disposition.md`
5. `docs/codex/local-v1-lv1-003-o4-execution-authorization.json`
6. `docs/codex/local-v1-lv1-003-o4-execution-authorization.md`
7. `scripts/local_v1_lv1_003_o4_execution_authorization_check.py`
8. `tests/test_local_v1_lv1_003_o4_execution_authorization_check.py`

All producer, bridge, policy, tool-manifest, and runtime paths remain byte-identical to the attempted
candidate.

## Closed Authority And Next Action

Attempts 001 through 005 are consumed. Attempt 003 image recovery remains consumed and closed. The
Attempt 005 budget is zero, retry is false, and all 19 authority fields are false. Release,
promotion, production, credential custody, new powers, new tools, evidence deletion, and UAT remain
false.

The next action is a separate reviewed API-exit diagnostic repair. This disposition assigns no
cause to `service_exited_nonzero`, includes no producer change, and grants no execution authority.
