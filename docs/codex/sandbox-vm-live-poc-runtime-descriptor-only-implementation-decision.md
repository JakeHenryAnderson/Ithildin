# Sandbox/VM Live POC Runtime Descriptor-Only Implementation Decision

Status: planning-only implementation decision draft for the future `ERG-004` descriptor-only
runtime slice.

Current governed tool count: `24`.

Current `ERG-004` status: `ready_for_descriptor_only_runtime_implementation_decision`.

Current selected capability: `not selected`.

Run:

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-implementation-decision-check
```

This decision draft names the exact future runtime surfaces that may be considered in a later
implementation sprint. It does not add runtime behavior, does not approve runtime implementation in
this checkpoint, and does not close `ERG-004`.

## Preconditions

The decision draft depends on these already-checked artifacts:

- `docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-decision-record.md`
- `docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-plan.md`
- `docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket.md`
- `var/review-packets/v3/sandbox-vm-live-poc-runtime-descriptor-only-ticket-review`

The descriptor-only implementation ticket status must remain:

```text
ready_for_descriptor_only_runtime_implementation_ticket
```

## Future Runtime Surfaces Under Consideration

A later implementation sprint may consider only these descriptor/correlation surfaces:

- a closed Pydantic descriptor schema for operator-supplied sandbox/VM run metadata;
- a local SQLite-backed descriptor record table or equivalent local store;
- an admin-protected descriptor submission/status API;
- read-only review-console rendering of descriptor status and warnings;
- Agent Run correlation fields that reference descriptor IDs without adding run controls;
- safe audit metadata for descriptor validation attempts;
- negative transcript generation for rejected descriptor cases;
- a source-review handoff packet using `EXT-LIVE-DESC-###` finding IDs.

Every future surface must preserve the descriptor as operator-attested evidence. Ithildin must not
claim it inspected, controlled, started, stopped, paused, snapshotted, shelled into, or verified a
VM/container.

## Required Descriptor Facts

Any later implementation must preserve these fields as data, not verified isolation claims:

- `descriptor_source: operator_supplied`
- `vm_lifecycle_source: operator_managed`
- `isolation_claim_source: operator_attested`
- `network_posture_source: operator_attested`
- `mount_posture_source: operator_attested`
- `model_client_source: operator_attested`
- `ithildin_live_inspection_performed: false`
- `ithildin_lifecycle_control_performed: false`
- `mission_control_runtime_authority_used: false`
- `trusted_host_promotion_performed: false`

## Required Future Acceptance Evidence

A later implementation sprint must prove:

- closed descriptor schema validation rejects unknown fields;
- descriptors with forbidden authority claims fail closed;
- outputs contain only labels, hashes, timestamps, enums, booleans, correlation IDs, status codes,
  and safe skipped/error counts;
- Agent Run, approval, audit, and signed-export correlations are checked without exposing file
  contents, prompts, model responses, raw paths, command lines, dependency names, package scripts,
  environment values, registry URLs, diffs, transcripts, or shell output;
- negative transcripts cover all rejected descriptor categories from the implementation ticket;
- no API/MCP profile loading, VM/container lifecycle behavior, live inspection, Mission Control
  runtime authority, local model invocation, host writes, artifact promotion, network expansion, or
  trusted-host promotion is introduced;
- no governed tool count change occurs unless a separate explicit capability gate approves it.

## Explicit Non-Approvals

This decision draft does not approve:

- runtime implementation in this checkpoint;
- live VM/container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- Mission Control runtime behavior;
- local model invocation by Ithildin;
- trusted-host promotion;
- host writes or artifact promotion;
- network expansion;
- API/MCP profile loading;
- SIEM adapter runtime behavior;
- production identity;
- runtime Postgres;
- hosted telemetry;
- remote MCP;
- compliance automation;
- shell, Docker, Kubernetes, or browser governed powers;
- arbitrary HTTP;
- broad filesystem writes;
- plugin SDK behavior;
- new governed tool powers;
- public/security-product positioning.

## Stop Conditions

Stop before runtime work if implementation requires VM lifecycle authority, live inspection, local
model invocation, Mission Control runtime authority, trusted-host promotion, host writes, artifact
promotion, network expansion, API/MCP profile loading, new governed powers, unbounded raw evidence
storage, or stronger product claims.

Escalate to High review first for repeated gate failures or unclear implementation boundaries.
Escalate to XHigh or GPT 5.5 Pro / human review only if a critical/high finding appears or the
product boundary remains ambiguous after High review.

## Validation

Run:

```sh
make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-check
make sandbox-vm-live-poc-runtime-descriptor-only-plan-check
make sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket-check
make sandbox-vm-live-poc-runtime-descriptor-only-implementation-decision-check
make no-new-powers-guardrail
make tool-surface-invariant-gate
```

The normal release gates must still pass. Tool count must remain `24`.
