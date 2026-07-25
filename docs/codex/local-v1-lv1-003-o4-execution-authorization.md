# Local v1 LV1-003 O4 Execution Authorization Gate

Status: `PREPARE_REVIEW`

This is the separate execution gate for the future exact-candidate Local-v1 `O4` journey. It is
non-authorizing. Its machine contract is
`docs/codex/local-v1-lv1-003-o4-execution-authorization.json`.

The gate preserves the reviewed fixed bridge and bounded producer implementation at
`5dab3654391c14fe214a9dfe302c099d0fe5fbf8`. The current code-only authorization record retains
historical origin commit `da17fbc86369ed5a6e7f9de7c1098322bcda4ac9` while binding the later
producer review at `docs/codex/local-v1-lv1-003-o4-producer-exact-review.md`. That `GO_CODE_ONLY`
record does not bind a future execution candidate or grant a live attempt. The future commit/tree,
live exact-review, and distinct post-review execution-disposition fields remain deliberately null.

## Prepared Live Ceiling

The producer is limited to one uniquely named isolated Compose project and one server-owned
`synthetic_read_review_v1` mission. It may eventually create ephemeral local admin and enrollment
values, but they must remain in memory or owner-only anchored runtime files and must never be
printed, returned in receipts, or copied into evidence. The ordinary authenticated Node must become
eligible before mission admission. The same enrolled Node state may then be restarted through the
reviewed fixed overlay with `max_cycles=1`. Hermes may be invoked exactly once with no supplied
arguments after the fixed socket healthcheck succeeds.
Hermes stdout and stderr must be connected directly to `DEVNULL` when its subprocess is created.
They are never captured, materialized, scanned, returned, or persisted; only exit, timeout, or
interruption classification may survive.

Gateway mission detail and Gateway Agent Run detail/timeline are the only operation-correlation
authority. Runner-authored counts, runner prose, and model-provider output are never accepted as
Gateway evidence. Gateway truth, Node connectivity, runner-reported state, and provider state remain
separate.
For this journey, actual Gateway truth is mission lifecycle `runner_reported_succeeded`, Agent Run
record status `active`, and exactly two `tool.execution.completed` timeline events. Synthesizing
Agent Run completion is forbidden.

## Build And Evidence Boundary

The future run must produce actual bounded image artifact and repository-license source inventories.
Image config/layer metadata is not an SBOM. The candidate producer and assembler now use
`image_artifact_inventory_digest` and `license_source_inventory_digest`, preserve actual Gateway
Agent Run status `active`, and require exactly two distinctly identified Gateway completion events.
The independently reviewed code-only candidate remains unusable for live producer evidence until
the still-null future live-candidate, live exact-review, and separate post-review execution
disposition fields are populated by a later control step. The inventories are not placeholder
hashes and do not claim SBOM coverage, license completeness, compliance, provenance custody, or
provider truth.
Static fake evidence proves closed private-snapshot enumeration and rejects observed path
replacement. It does not prove absence of transient malicious same-UID mutation while Docker reads
the build context; that threat remains outside the Local-v1 evidence boundary, consistent with the
golden-path limitation.

## Cleanup And Stop Lines

Cleanup must revoke the synthetic Node, tear down the exact Compose project with volumes, remove
only reconciled run-specific images, and prove project containers, volumes, network, persistent
profile volume, run-specific images, and runtime plaintext absent. Any ambiguity retains the
anchored runtime for recovery, reports `recovery_required`, and stops. There is no automatic retry.
Before invoking enrollment, the producer must record the attempt as ambiguous. A nonzero exit,
timeout, interruption, or malformed response before validated Node identity retains the exact
anchored runtime and Node volume, performs no destructive cleanup, and makes no revocation or
absence claim. Only validated identity clears ambiguity, and only a closed successful revocation
response confirms revocation. Post-rename report rollback is successful only when the public name
is absent or hidden-quarantined and the held base directory is durably synchronized; permission
removal alone is insufficient, and compound rollback or sync failure requires recovery.
If a validated Node ID exists but revocation is unavailable, invalid, or interrupted, destructive
cleanup is forbidden. The producer must write and verify one bounded owner-only secret-free
`node-revocation-recovery.json` containing the exact Node, project, and Node-volume identity needed
for reconciliation, attempt only the existing exact fixed-Node stop, and retain the Node volume and
anchored runtime. That private recovery receipt is quarantined staged material, not successful
published evidence; it contains no token, enrollment value, private key, prompt, provider output,
or raw tool result. Revocation, volume absence, runtime-plaintext absence, and full cleanup remain
unclaimed, and `recovery_required` remains true.

Ambient Docker hosts, contexts, configuration, credential helpers, registry credentials, proxy
variables, cloud credentials, arbitrary providers/models/tools/commands/arguments/paths, Docker
socket mounts, or host-control APIs are rejected.
Provider preflight is host-local only at `http://127.0.0.1:11434` and must confirm the exact model
inventory entry `gemma4:e4b`. Container routing through `host.docker.internal` remains unknown until
the sole attempt; a routing failure consumes that attempt and permits no retry.

## Current Disposition

`producer_code_authorized`, `docker_lifecycle_authorized`, `live_hermes_execution_authorized`,
`model_provider_access_authorized`, and `o4_evidence_execution_authorized` are all false. Release,
promotion, production, UAT, host-control, new-power, and new-tool authority are also false.

Only a later exact-candidate review with no blocking finding and a separate post-review disposition
may populate the future bindings and grant a maximum of one execution attempt. Until then, the live
target must fail before any Docker, API, provider, filesystem-runtime, or network action.
