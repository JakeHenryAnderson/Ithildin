# Local v1 LV1-003 O4 Attempt 004 Disposition

Status: `ATTEMPT_004_CONSUMED_REPAIR_REQUIRED_NO_LIVE_AUTHORITY`

Attempt `LV1-003-O4-ATTEMPT-004` is consumed. The attempt budget is zero, retry and automatic retry
are false, and all 19 authority fields are false. No further execution, image recovery, evidence
deletion, release, promotion, production action, or UAT action is authorized.

## Exact Attempt

The attempted candidate was commit `6452111a1d78f218a24432aaf833004195679318`, tree
`e8ea86cbd577a2d1323c27b2c3326b3c99ff7804`. The operator command was exactly
`make local-v1-lv1-003-o4-producer-run`, whose module command remained
`uv run python -m scripts.local_v1_lv1_003_o4_producer`.

The run identity was `20260725T162319Z-329e129a`; its unique Compose project was
`ithildin-local-v1-o4-329e129a`. The outward failure code was `recovery_required`.

## Bounded Diagnostic Facts

The exact retained diagnostic records that both the base-service and Hermes bridge builds
completed, all four image identities were bound, and the highest completed producer stage was `7`.
The stable primary failure was `base_services_start_failed`. The separate cleanup failure was
`owned_image_id_absence_probe_failed`, and the outward result was `recovery_required`.

The four bound identities were:

1. `ithildin/api-o4:329e129a` —
   `sha256:493df3eb92c9196cdc11f6f69ab517e88be8a44c731343d8cd0927fd6bec2914`
2. `ithildin/ui-o4:329e129a` —
   `sha256:d3cd7f2521d07ceceb2cf1f75aaa73278215ad7bc010ff9697fa883a3693f977`
3. `ithildin/node-o4:329e129a` —
   `sha256:c5f7368093d2735e060f9337c0be2a9654a8f515c59f4bf8dfe5c37b57095933`
4. `ithildin/hermes-node-bridge-o4:329e129a` —
   `sha256:048653b7091ceee199cbb1b6c0b47f1420a663fd1610fff340cc8378fc5610c1`

The diagnostic is bounded failure evidence. It does not contain raw Docker logs, credentials,
provider output, model output, prompts, tool results, or arbitrary paths.

## Verified Classifier Mismatch

The cleanup failure is explained by a verified classifier mismatch: the Docker absent-image-ID
response included a stdout newline, while the producer required stdout to be empty. The producer
therefore emitted `owned_image_id_absence_probe_failed` even though a separate read-only postcheck
found the exact IDs absent.

This explains the stable cleanup classifier. It does not establish generic Docker absence, completed
cleanup, a non-bypass guarantee, or permission to change the producer in this closure. No producer
repair is included.

## Point-In-Time Postcheck

A separate read-only, exact-run-scoped postcheck after the failure observed:

- all four exact run references absent;
- all four exact bound image IDs absent;
- zero exact-project containers;
- zero exact-project volumes;
- zero exact-project networks;
- the Attempt 004 runtime run directory absent; and
- the owner-only runtime base retaining only
  `attempt-003-image-recovery-001-consumed.json`.

These are point-in-time exact-run postconditions only. They are not ongoing live truth, a general
Docker absence claim, proof that cleanup completed, or evidence of successful O4 execution. On this
exact evidence no image recovery is required or authorized.

## Retained Evidence

The owner-only `0700` receipt root
`var/local-v1-lv1-003-o4-receipts/20260725T162319Z-329e129a` contains exactly:

1. `candidate/`
2. `candidate-manifest.json`
3. `diagnostic.json`
4. `disposition.json`

The exact retained files are:

- `disposition.json`: owner-only `0600`, 119 bytes,
  `sha256:03bceb292828f68440c2183438f856edd4b291130d6f276b9418a3d2ad967992`
- `diagnostic.json`: owner-only `0600`, 6,885 bytes,
  `sha256:dcff6467ffa83cad6f9b86d4e9883d7206b76fa5f2f8407f5d8f765284eac3e6`
- `candidate-manifest.json`: owner-only `0600`, 96,772 bytes,
  `sha256:4e1256eba744acb3d1dbcef123cdf04e57d801c89cf83a4754448739234ff534`
- `candidate/`: owner-only `0500`, exactly 664 files

The validator reads Attempts 002, 003, and 004 retained receipts directly and independently of Git
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
3. `docs/codex/local-v1-lv1-003-o4-attempt-004-disposition.json`
4. `docs/codex/local-v1-lv1-003-o4-attempt-004-disposition.md`
5. `docs/codex/local-v1-lv1-003-o4-execution-authorization.json`
6. `docs/codex/local-v1-lv1-003-o4-execution-authorization.md`
7. `scripts/local_v1_lv1_003_o4_execution_authorization_check.py`
8. `tests/test_local_v1_lv1_003_o4_execution_authorization_check.py`

All producer, bridge, policy, tool-manifest, and runtime paths remain byte-identical to the attempted
candidate.

## Closed Authority And Next Action

Attempts 001 through 004 are consumed. Attempt 003 image recovery remains consumed and closed. The
Attempt 004 budget is zero, retry is false, and all 19 authority fields are false. Release,
promotion, production, credential custody, new powers, new tools, and UAT remain false.

The next action is to prepare a separate reviewed producer repair for Docker not-found output
normalization plus a bounded diagnostic for the earlier `base_services_start_failed` primary
failure. That future repair does not exist here and receives no execution authority from this
closure.
