# Local v1 LV1-003 O4 Execution Authorization Gate

Status: `PREPARE_REVIEW`

This is the separate execution gate for the future exact-candidate Local-v1 `O4` journey. It is
non-authorizing. Its machine contract is
`docs/codex/local-v1-lv1-003-o4-execution-authorization.json`.

The gate preserves the reviewed fixed bridge implementation at
`da5fd021bddb48ad663aa0a409da036bc854b516` and the code-only authorization record at
`da17fbc86369ed5a6e7f9de7c1098322bcda4ac9`. It does not bind a future producer candidate yet.
Those future commit/tree fields, an independent exact-review record, and a distinct post-review
disposition are deliberately null.

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
Image config/layer metadata is not an SBOM. The future exact producer-and-assembler candidate must
rename the current `sbom_digest` field to `image_artifact_inventory_digest`, preserve
`license_source_inventory_digest`, and reconcile the current assembler's synthesized `completed`
Agent Run status with actual Gateway status `active`. Until its schema, checker, renderer, and tests
are reconciled, the current assembler is unusable for live producer evidence. The inventories are
not placeholder hashes and do not claim SBOM coverage, license completeness, compliance,
provenance custody, or provider truth.

## Cleanup And Stop Lines

Cleanup must revoke the synthetic Node, tear down the exact Compose project with volumes, remove
only reconciled run-specific images, and prove project containers, volumes, network, persistent
profile volume, run-specific images, and runtime plaintext absent. Any ambiguity retains the
anchored runtime for recovery, reports `recovery_required`, and stops. There is no automatic retry.

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
