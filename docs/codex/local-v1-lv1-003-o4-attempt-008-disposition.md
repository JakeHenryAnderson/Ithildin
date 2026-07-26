# Local v1 LV1-003 O4 Attempt 008 Disposition

Status:
`ATTEMPT_008_CONSUMED_ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REQUIRED_RECOVERY_REQUIRED_NO_LIVE_AUTHORITY`

Attempt `LV1-003-O4-ATTEMPT-008` is consumed. The budget is zero, retry and automatic retry are
false, and all 19 authority fields are false. No further execution, recovery action, evidence
deletion, release, promotion, production action, credential custody, or UAT action is authorized.

## Exact Attempt And Diagnostic

The attempted candidate was `ae6824bd6d81f58efc5a3383d63341d20ae3467a`, tree
`8e5a0d45369ca559e271aa3fd58c19e6bb57e33c`. Run
`20260726T001909Z-d801f37b` used Compose project
`ithildin-local-v1-o4-d801f37b` and ended with `recovery_required`.

Both base and bridge builds completed, four image identities were bound, and stage `7` was reached.
The primary failure was `subprocess_output_rejected`. Cleanup failure codes are exactly
`[enrollment_outcome_ambiguous]`, so `recovery_required` is true.

## Bounded Candidate Code Analysis

Exact candidate source shows a deterministic code-path incompatibility. The Node CLI enrollment
return uses `NodeState.safe_summary()`, which always includes the key `private_key_present`. The
producer's exact `_FORBIDDEN_OUTPUT` expression includes `private[_ -]?key`, and
`_require_success()` performs that lexical scan before the enrollment JSON projection is parsed and
validated.

That source relationship, together with stage and return-path evidence, identifies a narrow
candidate defect suitable for a separately reviewed enrollment-output projection repair. This is
not retained raw stdout proof: raw stdout was not inspected for this disposition, no raw stdout is
quoted or retained here, and this record makes no claim about its exact bytes.

## Recovery And Retained Evidence

Cleanup success is not claimed. No image ID, run image reference, container, volume, network,
runtime plaintext, or general Docker absence is claimed. Reconciliation remains required, but this
closure authorizes neither recovery nor evidence deletion.

The exact owner-only `0700` receipt root is
`var/local-v1-lv1-003-o4-receipts/20260726T001909Z-d801f37b`. It retains:

- 119-byte disposition:
  `sha256:03bceb292828f68440c2183438f856edd4b291130d6f276b9418a3d2ad967992`
- 7,174-byte diagnostic:
  `sha256:cf303eb045cf522e62c5fa5b2f35fc54d5ecd5981e1c0c1428d4584d6a165b28`
- 96,772-byte manifest:
  `sha256:04d64359cbc275181d90b50cef3534c550a0d7e446ae12caee3f5fe7bcb19c54`
- 664-file exact candidate snapshot

The validator preserves Attempts 002 through 008 receipts and the consumed Attempt 003 recovery
receipt. Missing, changed, extra, symlink, or special evidence fails closed.

## Exact Closure And Next Action

No future child commit or tree is stated. The closure accepts only a clean direct child of the
attempted candidate with exactly eight changed paths: Makefile, README, this JSON/Markdown pair,
the authorization JSON/Markdown pair, the validator, and its focused test.

The next action is a separately reviewed enrollment-output projection repair. It must preserve the
secret-safe closed projection, must not rely on or claim retained raw stdout proof, and does not
authorize retry. This closure includes no producer, Node, runtime, Dockerfile, policy, manifest, or
tool-surface change and grants no execution authority.
