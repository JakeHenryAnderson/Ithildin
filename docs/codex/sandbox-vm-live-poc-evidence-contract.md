# Sandbox/VM Live POC Evidence Contract

Status: design-only evidence contract for a future `ERG-004` live sandbox/VM worker proof of
concept.

Current governed tool count: `24`.

Current `ERG-004` status: `blocked`.

Current selected capability: `not selected`.

This contract defines what a future live sandbox/VM worker proof of concept would have to prove
across Ithildin evidence, operator-managed sandbox evidence, and optional Mission Control display
evidence. It does not implement live VM/container inspection, sandbox orchestration, local model
invocation, Mission Control runtime behavior, trusted-host promotion, SIEM adapters, production
identity, runtime Postgres, hosted telemetry, remote MCP, plugin SDK behavior, shell, Docker socket
access, Kubernetes tools, browser automation, arbitrary HTTP, broad filesystem writes, compliance
automation, or public/security-product positioning.

Validate this contract with:

```sh
make sandbox-vm-live-poc-evidence-contract-check
```

## Preconditions

Any future live POC implementation plan must prove these preconditions first:

- favorable `ERG-003` disposition;
- a non-draft post-RC decision record for `PRD-SANDBOX-LIVE-POC-001`;
- an implementation plan that still treats the VM/container as operator-managed infrastructure;
- source/external review of the live POC plan;
- a local model invocation plan that is reviewed separately before runtime use;
- cleanup transcript and failure transcript requirements;
- explicit stop conditions for host-boundary ambiguity, unreviewed writes, network expansion,
  local-model authority drift, or Mission Control authority drift.

## Required Evidence Sources

A future live POC must correlate at least these evidence sources:

| Source | Required evidence | Non-authority |
| --- | --- | --- |
| Operator intent | mission ID, operator principal label, requested task label, approved scope label | Does not authorize host writes or production use |
| Ithildin run evidence | run ID, tool call IDs, policy hash, manifest hash, approval IDs, audit head, export hash | Covers mediated actions only |
| Sandbox/VM evidence | sandbox ID, operator-managed profile ID, mount/root posture, network posture, cleanup status | Does not prove all host activity or replace Ithildin audit |
| Local model/client evidence | model/client label, request hash, output/proposal hash, authority warnings | Does not grant filesystem, shell, network, or host authority |
| Mission Control display evidence | imported packet hash, warning chips, display timestamp, source packet commit | Display-only; no execution, policy, approval, audit, or sandbox authority |

## Stable Evidence Fields

The future evidence bundle must be secret-free and use labels rather than raw sensitive paths.

```json
{
  "schema_version": "1",
  "evidence_type": "ithildin.sandbox_vm_live_poc",
  "decision_record_id": "PRD-SANDBOX-LIVE-POC-001",
  "erg_id": "ERG-004",
  "prior_lane": "ERG-003",
  "mission_id": "mission_...",
  "run_id": "run_...",
  "workspace_id": "workspace://...",
  "sandbox_id": "sandbox://...",
  "sandbox_profile_id": "sandbox_profile_...",
  "operator_principal": "admin:local-ui",
  "model_client_label": "local-model://label",
  "model_request_hash": "sha256:...",
  "model_output_hash": "sha256:...",
  "ithildin_audit_head": "sha256:...",
  "ithildin_evidence_export_hash": "sha256:...",
  "policy_hash": "sha256:...",
  "manifest_hash": "sha256:...",
  "sandbox_transcript_hash": "sha256:...",
  "cleanup_transcript_hash": "sha256:...",
  "failure_transcript_hash": "sha256:...",
  "mission_control_packet_hash": "sha256:...",
  "promotion_status": "not_promoted",
  "implementation_approved": false
}
```

## Cross-Source Correlation Requirements

A future live POC must prove:

- the operator mission ID matches the Ithildin run evidence;
- the sandbox ID matches the operator-managed profile;
- the Ithildin run ID appears in the exported audit evidence;
- the local model/client proposal hash matches the governed request evidence;
- the sandbox transcript hash is recorded without exposing prompts, file contents, secrets, raw VM
  internals, or shell output;
- the cleanup transcript hash is present even when cleanup is manual;
- the failure transcript hash is present for at least one denied or failed scenario;
- the Mission Control packet hash, if present, matches display-only imported evidence;
- the promotion status remains `not_promoted` unless a separate trusted-host promotion lane is
  approved later.

## Required Negative Evidence

A future implementation plan must include denial or failure evidence for:

- missing or unfavorable `ERG-003` disposition;
- missing post-RC decision record;
- missing sandbox profile;
- unsupported platform or support status;
- missing cleanup transcript;
- missing failure transcript;
- local model request for shell, Docker socket, Kubernetes, browser automation, arbitrary HTTP, or
  broad filesystem writes;
- Mission Control packet claiming execution, policy, approval, audit, local-model, sandbox, or
  promotion authority;
- sandbox evidence that includes raw host paths, credentials, prompts, file contents, diffs, shell
  output, dependency names, package script values, or response bodies;
- any attempted trusted-host promotion before a separate promotion implementation is approved.

## Current Allowed State

Current artifacts may reference this contract as a future evidence target only. Today this contract
allows decision records, review packets, static fixtures, source-review questions, and operator
warnings. It does not approve runtime behavior.

Current output must continue to report:

- runtime changes allowed: `false`;
- live VM/container inspection allowed: `false`;
- Mission Control runtime allowed: `false`;
- local model invocation allowed: `false`;
- sandbox orchestration allowed: `false`;
- trusted-host promotion allowed: `false`;
- SIEM adapter allowed: `false`;
- public/security-product positioning allowed: `false`.
