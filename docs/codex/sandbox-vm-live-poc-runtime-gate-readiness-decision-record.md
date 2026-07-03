# Sandbox/VM Live POC Runtime Gate Readiness Decision Record

Status: committed decision record for `ERG-004` descriptor-only runtime implementation planning.

Current governed tool count: `24`.

Decision ID: `PRD-SANDBOX-LIVE-GATE-001`.

Decision outcome: `approved_for_descriptor_only_runtime_implementation_planning`.

This decision records an internal High proxy review of the runtime gate-readiness packet. It is not
external validation, not public/security-product approval, not runtime implementation approval, and
not `ERG-004` closure.

## Reviewed Evidence

- Reviewed commit: `7d3ef7c63099266679f2d32bfc258bec515083de`
- Reviewed packet:
  `var/review-packets/v3/sandbox-vm-live-poc-runtime-gate-readiness-review`
- Reviewed packet hash:
  `sha256:e59ea9e93927ae0ef501fa3785cc9c8dd02c01ea2f766a015798243de1989b00`
- Reviewer: `Codex internal High proxy reviewer`
- Reviewer type: `internal_ai_high_proxy`
- Source access: `packet-and-source`
- Finding namespace: `EXT-LIVE-GATE-###`
- Finding count: `0`
- Critical/high findings: `0`
- Normalized response path:
  `var/review-runs/sandbox-vm-live-poc-runtime-gate-readiness/normalized-response.json`

The review disposition was:

```text
approved_for_descriptor_only_runtime_implementation_planning
```

## Allowed Lane Movement

This record allows only this lane movement:

```text
ERG-004: ready_for_runtime_implementation_gate_review -> ready_for_descriptor_only_runtime_implementation_planning
```

The next allowed work is a descriptor-only runtime implementation-planning/decision sprint. That
future sprint must still explicitly choose exact runtime surfaces, add tests, add source-review
handoff evidence, and keep the governed tool count at `24` unless a separate approved capability
changes it.

## Scope Still Blocked

This record does not approve:

- runtime implementation;
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

## Required Next Checkpoint

Before any descriptor-only runtime code is added, a later implementation sprint must produce:

- an implementation decision that names the exact runtime surfaces touched;
- closed descriptor schema validation;
- positive and negative descriptor fixtures;
- correlation tests for Agent Run, approval, audit, and signed-export evidence if those surfaces are
  touched;
- source-review handoff with `EXT-LIVE-DESC-###` finding IDs;
- no-new-powers and tool-surface invariant evidence;
- rollback/removal notes.

## Validation

Run:

```sh
make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-check
make sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run
make sandbox-vm-live-poc-runtime-descriptor-only-plan-check
make sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket-check
make sandbox-vm-live-poc-runtime-descriptor-only-ticket-review-bundle-check
make no-new-powers-guardrail
make tool-surface-invariant-gate
```

