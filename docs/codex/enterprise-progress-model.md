# Ithildin Enterprise Progress Model

Status: checked progress model for the v1.0 local-preview and enterprise-readiness path.

This model turns the current checkpoint, v1.0 progress assessment, enterprise runway, and enterprise
gap matrix into a single operator-readable ladder. It is an estimation aid only. It is not a release
approval, external review result, production deployment claim, sandbox claim, SIEM custody claim,
compliance claim, or permission to add runtime powers.

## Current Checked Inputs

- Governed tool count: `24`.
- Current selected capability: `not selected`.
- Recommended next enterprise review: `ERG-004`.
- Recommended send set: `ERG-004`.
- Technical MVP state: `operator_trial_observed`.
- Enterprise send package ready: `true`.
- Enterprise response evidence present: `0`.
- Enterprise closure-ready lanes: `0`.
- Capability expansion: blocked.
- Runtime changes: blocked.
- Public/security-product positioning: blocked.

## Progress Ladder

| Checkpoint | Approximate band | Current status | What moves it |
| --- | ---: | --- | --- |
| Local governed tool gateway | `92-96%` | Mature for local preview. | Keep `make release-check`, policy parity, tool-surface invariants, audit/evidence checks, and review packets green. |
| v1.0 local-preview RC | `84-90%` | RC handoff machinery is ready to regenerate, the operator trial is observed, and the current enterprise send package is fresh. | Same-commit `make release-check`, `make review-candidate`, packet redaction `findings: 0`, and final local handoff evidence. |
| Operator workbench and demo path | `78-86%` | Useful local review-console, Agent Run evidence, demo packets, and observed demo-flow evidence exist. | A cleaner guided demo and more real user feedback without new runtime powers. |
| Mission Control display/import path | `50-65%` | Design/display lane is packaged but not closed. | Favorable `ERG-002` disposition and a later Mission Control-side display-only implementation plan. |
| Sandbox/VM governed agent workflow | `45-60%` | Static profile/preflight evidence and ERG-004 planning artifacts exist; live VM/container work remains blocked. | Runtime-ticket review closure before any live preflight or local-model/sandbox planning advances. |
| Enterprise control-plane architecture | `35-50%` | Major lanes are explicit but blocked or planning-only. | Separate decisions for identity/storage, SIEM-shaped adapters, compliance mapping support, trusted-host promotion, and public claim wording. |
| Long-term governed-agent workbench vision | `55-65%` | The shape is coherent, but several hard enterprise lanes remain future work. | Close external/source review loops, keep boundaries separate, and add runtime powers only after lane-specific gates. |

## Major Checkpoint Definitions

### Checkpoint A: v1.0 Local-Preview RC

This checkpoint is about a local, single-operator governed MCP/tool workbench. It is close because
Ithildin already has bounded tools, policy, manifests, approval evidence, audit/export evidence,
Agent Run evidence, review packets, and a local operator console.

It is not the same as enterprise deployment, production identity, hosted trust, or sandbox
orchestration.

### Checkpoint B: Mission Control Display Integration

This checkpoint lets Mission Control display Ithildin evidence and mission/run labels while keeping
Mission Control outside execution, policy, approval, audit, model invocation, sandbox lifecycle, and
trusted-host promotion authority.

It requires the `ERG-002` response path and a later repository-specific implementation decision.

### Checkpoint C: Sandbox/VM Static Preflight Disposition

This checkpoint decides whether the static sandbox/VM profile and preflight lane can close for
local-preview planning. It does not approve live VM/container inspection, local model invocation,
container lifecycle management, or sandbox orchestration.

It is now a recorded precondition for the ERG-004 runtime-ticket review lane.

### Checkpoint D: Live Sandbox/VM Proof Of Concept

This checkpoint remains blocked until the ERG-004 runtime-ticket review lane is dispositioned. It
would eventually prove a local agent working in an operator-managed sandbox/VM with evidence
correlation, but it still must not claim OS isolation beyond the actual sandbox layer that is
inspected and reviewed.

### Checkpoint E: Trusted-Host Promotion

This checkpoint remains blocked. It would require exact artifact hash binding, approval evidence,
source and destination zone contracts, negative transcripts, source review, and a later decision
before any sandbox output can move into trusted host staging or approved zones.

### Checkpoint F: Enterprise Architecture Lanes

These lanes remain planning-only or blocked:

- production identity and multi-user authorization;
- durable runtime storage and retention;
- SIEM-shaped export adapters;
- compliance mapping support;
- public/security-product positioning.

They require separate decision records and external/source review before stronger claims or runtime
behavior can be added.

## Current Best Next Action

The best next action is the ERG-004 runtime implementation-gate prep lane:

```sh
make sandbox-vm-live-poc-runtime-ticket-internal-review-check
make sandbox-vm-live-poc-runtime-implementation-gate-check
make sandbox-vm-live-poc-runtime-descriptor-contract-check
make sandbox-vm-live-poc-runtime-descriptor-contract-internal-review-check
make sandbox-vm-live-poc-runtime-gate-readiness-review-bundle-check
```

This gate draft remains non-runtime work. If a later implementation packet receives a response,
save the raw response only under the ignored enterprise response inbox, check the waiting-room
state, and run:

```sh
make enterprise-dual-response-inbox
make enterprise-response-waiting-room
make enterprise-response-paste-preflight
make enterprise-response-inbox
make enterprise-response-status-board
make enterprise-response-intake-drill
make enterprise-response-application-protocol
```

Do not manually promote a lane from planning or blocked status. Use the lane-specific response kit
and closure gate.

## Blocked Claims And Powers

This model does not approve:

- live VM/container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- Mission Control runtime behavior;
- local model invocation;
- trusted-host promotion;
- SIEM adapter runtime behavior;
- production identity or enterprise RBAC;
- runtime Postgres;
- hosted telemetry;
- remote MCP hosting;
- compliance automation;
- public/security-product positioning;
- new governed tool powers.

## Validation

Run:

```sh
make enterprise-progress-model
make v1-progress-assessment
make enterprise-current-checkpoint
make enterprise-readiness-gap-matrix-check
```

`make release-check` includes this model so progress bands, tool count, next-review ordering, and
blocked-boundary wording cannot quietly drift.
