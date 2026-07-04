# Trusted-Host Promotion State Machine

Status: design-only state-machine contract for `ERG-005` and `PRD-TRUSTED-HOST-001`.

Current governed tool count: `24`.

Current `ERG-005` status: `blocked`.

Current selected capability: `not selected`.

This contract defines the future states and evidence that would be required before a sandbox
artifact could move toward a trusted host staging or approved-output zone. It does not approve
runtime behavior, direct host writes, overwrite/delete/move behavior, broad archive extraction,
automatic promotion, promotion without exact artifact hash binding, promotion without approval
evidence, API/MCP behavior, Mission Control runtime behavior, local model invocation, VM/container
lifecycle management, sandbox orchestration, SIEM adapters, production identity, runtime Postgres,
hosted telemetry, shell, Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad
filesystem writes, compliance automation, or public/security-product claims.

Validate this state-machine contract with:

```sh
make trusted-host-promotion-state-machine-check
```

The matching negative fixture contract is
[trusted-host-promotion-negative-fixtures.md](trusted-host-promotion-negative-fixtures.md), validated
with `make trusted-host-promotion-negative-fixtures-check`.
The matching zone contract is
[trusted-host-promotion-zone-contract.md](trusted-host-promotion-zone-contract.md), validated with
`make trusted-host-promotion-zone-contract-check`.
The matching implementation-plan contract is
[trusted-host-promotion-implementation-plan.md](trusted-host-promotion-implementation-plan.md),
validated with `make trusted-host-promotion-implementation-plan-check`.

## State Vocabulary

Only `not_promoted` is valid in current runtime/demo evidence. Every other state below is a future
design state until a separate implementation decision authorizes the exact runtime path.

| State | Meaning | Runtime posture today |
| --- | --- | --- |
| `not_promoted` | Artifact evidence exists only in sandbox/staging evidence; no trusted-host placement occurred. | allowed evidence state |
| `promotion_requested` | A future operator requested review of one exact artifact hash and zone-label pair. | design-only |
| `promotion_reviewing` | A future reviewer is inspecting exact binding evidence before approval. | design-only |
| `promotion_approved` | A future approval binds exact artifact hash, labels, policy, manifest, principal, and expiry. | design-only |
| `promotion_in_progress` | A future implementation has begun one bounded promotion attempt. | design-only |
| `promotion_completed` | A future implementation records matching source, staging, and approved-output hashes after placement. | design-only |
| `promotion_rejected` | A reviewer denied the request and no trusted-host placement occurred. | design-only |
| `promotion_expired` | Approval or request evidence expired before a trusted-host placement occurred. | design-only |
| `promotion_conflicted` | Existing target, hash mismatch, label conflict, or unsupported target blocked placement. | design-only |
| `promotion_stale` | Source, staging, policy, manifest, principal, schema, or request evidence drifted before placement. | design-only |
| `promotion_replay_denied` | A reused approval, promotion ID, request hash, or one-time scope was rejected. | design-only |
| `promotion_recovery_required` | A future incomplete attempt requires read-only diagnostics before any operator decision. | design-only |

## Allowed Transition Sketch

Current evidence may only remain at `not_promoted`.

Future implementation planning may model these transitions:

| From | To | Required evidence |
| --- | --- | --- |
| `not_promoted` | `promotion_requested` | Request ID, source label, source artifact hash, requested staging label, requested approved label, requesting principal, workspace ID, sandbox ID, and created timestamp. |
| `promotion_requested` | `promotion_reviewing` | Reviewer principal, decision session ID, current policy hash, current manifest hash, current source hash, and warning-state acknowledgement. |
| `promotion_reviewing` | `promotion_approved` | Approval ID, approval expiry, one-time scope hash, exact artifact hash binding, policy hash, manifest hash, principal, workspace, schema/tool version, and review reason. |
| `promotion_requested` | `promotion_rejected` | Denial principal, denial reason label, and unchanged source/staging/approved hashes. |
| `promotion_reviewing` | `promotion_rejected` | Denial principal, denial reason label, reviewed evidence hash, and unchanged source/staging/approved hashes. |
| `promotion_approved` | `promotion_in_progress` | Atomic attempt ID, compare-and-set approval consumption evidence, current source hash, current policy hash, current manifest hash, and one-time scope match. |
| `promotion_in_progress` | `promotion_completed` | Source hash, staging hash, approved hash, destination label, completed timestamp, audit event ID, approval consumption evidence, and diagnostics status. |
| `promotion_requested` | `promotion_expired` | Request expiry or policy-defined timeout evidence. |
| `promotion_reviewing` | `promotion_expired` | Approval-review expiry evidence. |
| `promotion_approved` | `promotion_expired` | Approval expiry at execution time and no trusted-host placement. |
| `promotion_requested` | `promotion_conflicted` | Conflict reason label and safe metadata for existing target, unsupported type, unsafe label, or hash mismatch. |
| `promotion_reviewing` | `promotion_conflicted` | Conflict reason label and reviewed evidence hash. |
| `promotion_approved` | `promotion_stale` | Drift reason label for changed source hash, policy hash, manifest hash, principal, schema/tool version, request hash, or workspace. |
| `promotion_approved` | `promotion_replay_denied` | Reused approval, reused promotion ID, reused request hash, or one-time scope mismatch. |
| `promotion_in_progress` | `promotion_recovery_required` | Attempt ID, phase label, expected hash, observed safe status label, and read-only diagnostic pointer. |

No transition may skip approval evidence, hash binding, policy/manifest evidence, or one-time scope
evidence. Every runtime transition would need one-time scope evidence before host placement. No
transition may record file contents, prompts, diffs, response bodies, raw host paths, raw
sandbox-internal paths, shell output, VM logs, secrets, dependency names, package script values, or
environment values.

## Stable Evidence Fields

A future promotion state event must use secret-free fields:

```json
{
  "schema_version": "1",
  "promotion_id": "promotion_...",
  "state": "not_promoted",
  "previous_state": null,
  "transition_id": "ptr_...",
  "run_id": "run_...",
  "mission_id": "mc-demo-...",
  "workspace_id": "workspace://demo",
  "sandbox_id": "sandbox://demo",
  "source_artifact_label": "sandbox://demo/output.txt",
  "source_artifact_sha256": "sha256:...",
  "host_staging_label": "host-staging://demo/output.txt",
  "host_staging_sha256": "sha256:...",
  "approved_host_label": "approved://demo/output.txt",
  "approved_host_sha256": "sha256:...",
  "approval_id": "appr_...",
  "request_hash": "sha256:...",
  "scope_hash": "sha256:...",
  "policy_hash": "sha256:...",
  "manifest_hash": "sha256:...",
  "operator_principal": "admin:local-ui",
  "reason_label": "not_promoted",
  "created_at": "timestamp",
  "expires_at": "timestamp",
  "runtime_promotion_performed": false,
  "auto_promotion_performed": false
}
```

The current implementation may only emit `promotion_status: not_promoted` in demo/review packets.
Future state-event JSON is a contract target, not a current API, MCP, executor, or Mission Control
runtime surface.

## Transition Denials

Future negative transcripts must prove fail-closed behavior for:

- transition not listed in the allowed transition sketch;
- transition missing approval ID, request hash, scope hash, policy hash, manifest hash, or exact
  artifact hash;
- approval not bound to source label, staging label, approved label, workspace, principal, expiry,
  schema/tool version, policy hash, and manifest hash;
- approval reuse, promotion ID reuse, request hash reuse, stale one-time scope, and expired approval;
- changed source hash, staging hash mismatch, approved-output hash mismatch, stale sandbox evidence,
  and changed artifact after approval;
- absolute path, parent traversal, encoded traversal, URL, Unicode ambiguity, control-character,
  hidden path, `.git`, symlink, hardlink, directory, binary target, unsupported type, and broad
  archive extraction;
- existing target conflict, overwrite request, delete request, move request, chmod request,
  automatic promotion request, and promotion without operator acknowledgement;
- missing warning state, stale evidence timestamp, mismatched packet commit, unsupported schema,
  unsupported state value, and unsafe label.

## Current Allowed State

Current artifacts may reference this state machine as a future decision checklist only. Today this
state machine allows docs, transition sketches, static fixtures, review packets, source-review
questions, and operator warnings. It does not approve runtime behavior.

Current output must continue to report:

- decision record required: `true`;
- implementation approved: `false`;
- runtime changes allowed: `false`;
- trusted-host promotion allowed: `false`;
- direct host writes allowed: `false`;
- overwrite/delete/move allowed: `false`;
- broad archive extraction allowed: `false`;
- automatic promotion allowed: `false`;
- promotion without exact artifact hash binding allowed: `false`;
- promotion without approval evidence allowed: `false`;
- Mission Control runtime allowed: `false`;
- local model invocation allowed: `false`;
- sandbox orchestration allowed: `false`;
- SIEM adapter allowed: `false`;
- new power classes allowed: `false`;
- public/security-product positioning allowed: `false`.
