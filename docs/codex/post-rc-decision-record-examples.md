# Post-RC Decision Record Examples

Status: example pack for post-v1.0 RC boundary decisions.

These examples show how to apply the
[Post-RC Decision Record Template](post-rc-decision-record-template.md) after the v1.0 local-preview
RC feature freeze. They are examples only. They do not approve runtime behavior, manifests,
executors, policy changes, API/MCP behavior, UI runtime behavior, Mission Control runtime behavior,
sandbox orchestration, local model invocation, trusted-host promotion, SIEM adapters, production
identity, runtime Postgres, hosted telemetry, remote MCP, plugin SDK behavior, compliance
automation, or public/security-product positioning.

Current governed tool count: `24`.

Current selected capability: `not selected`.

The current active lane statuses are tracked in the
[Post-RC Decision Register](post-rc-decision-register.md).

## Example PRD-MC-DISPLAY-001

- Decision ID: `PRD-MC-DISPLAY-001`
- Decision record status: `approved_for_planning`
- Target lane: Mission Control display importer continuation.
- Trigger: Mission Control needs a display-only way to import Ithildin evidence packet metadata.
- Requested change: Draft schema, packet, and UI display planning for imported labels, hashes,
  warnings, and links.
- Current boundary being changed: none; this example keeps the lane planning-only.
- Allowed scope: docs, schema sketches, static fixtures, display-only packet examples, and review
  prompts.
- Explicitly forbidden scope: Mission Control execution authority, policy authority, approval
  authority, audit authority, local-model runner behavior, VM/container management, sandbox
  orchestration, trusted-host promotion, file mutation, runtime importer behavior, and production
  identity.
- Runtime surfaces touched: none.
- Runtime surfaces not touched: manifests, executors, policy/rules, API/MCP behavior, approval/audit
  logic, UI runtime behavior, Mission Control runtime behavior, sandbox/VM runtime behavior, local
  model invocation, trusted-host promotion, SIEM/telemetry, identity, storage, and remote services.
- Tool count impact: none; remains `24`.
- Manifest impact: none.
- Policy/rule impact: none.
- API/MCP impact: none.
- UI runtime impact: none.
- Mission Control impact: planning artifacts only.
- Sandbox/VM impact: none.
- Local model impact: none.
- Trusted-host promotion impact: none.
- SIEM/telemetry impact: none.
- Identity/storage/remote impact: none.
- Compliance/public-positioning impact: none; no regulated-industry assurance claim is made.
- Required source-review or external-review evidence: review of schema and display-only packet before
  runtime importer work is proposed.
- Required implementation plan: required before any runtime importer implementation.
- Required tests: docs and schema validation only for this planning decision.
- Required gates: `make post-rc-decision-gate`,
  `make post-rc-decision-record-template-check`, and
  `make post-rc-decision-record-examples-check`.
- Required packet artifacts: Mission Control display review packet.
- Required negative transcripts: none for planning-only work; required before runtime importer work.
- Required accepted-risk update: none for planning-only work.
- Required operator warning language: Mission Control remains a display/import planning surface only.
- Go/no-go outcome: go for planning only; no-go for runtime behavior.

## Example PRD-SANDBOX-PREFLIGHT-001

- Decision ID: `PRD-SANDBOX-PREFLIGHT-001`
- Decision record status: `no_go`
- Target lane: live sandbox/VM preflight.
- Trigger: operator wants to probe a real local VM/container profile from Ithildin.
- Requested change: run live preflight checks against a VM/container profile.
- Current boundary being changed: live host or sandbox environment inspection would move beyond static
  fixture evidence.
- Allowed scope: static fixture evidence, source-review disposition, docs, review packets, negative
  fixture planning, and operator warnings.
- Explicitly forbidden scope: live VM/container inspection, SSH, shell, Docker socket access,
  Kubernetes tools, local model invocation, sandbox orchestration, trusted-host promotion, runtime
  preflight runner behavior, production identity, and remote control-plane behavior.
- Runtime surfaces touched: none.
- Runtime surfaces not touched: manifests, executors, policy/rules, API/MCP behavior, approval/audit
  logic, UI runtime behavior, Mission Control runtime behavior, sandbox/VM runtime behavior, local
  model invocation, trusted-host promotion, SIEM/telemetry, identity, storage, and remote services.
- Tool count impact: none; remains `24`.
- Manifest impact: none.
- Policy/rule impact: none.
- API/MCP impact: none.
- UI runtime impact: none.
- Mission Control impact: none.
- Sandbox/VM impact: static evidence only.
- Local model impact: none.
- Trusted-host promotion impact: none.
- SIEM/telemetry impact: none.
- Identity/storage/remote impact: none.
- Compliance/public-positioning impact: none.
- Required source-review or external-review evidence: external/source review of sandbox/VM preflight
  contract and a separate implementation plan before reconsideration.
- Required implementation plan: missing; live behavior remains blocked.
- Required tests: static profile fixture, negative fixture, and redaction checks only.
- Required gates: `make post-rc-decision-gate`,
  `make post-rc-decision-record-template-check`, and
  `make post-rc-decision-record-examples-check`.
- Required packet artifacts: sandbox/VM static preflight source-review packet.
- Required negative transcripts: static negative fixture transcripts only.
- Required accepted-risk update: required before live runtime work.
- Required operator warning language: Ithildin does not start, inspect, or manage VMs/containers in
  this decision.
- Go/no-go outcome: no-go for live runtime behavior.

## Example PRD-SANDBOX-LIVE-POC-001

- Decision ID: `PRD-SANDBOX-LIVE-POC-001`
- Decision record status: `no_go`
- Target lane: live sandbox/VM worker proof of concept.
- Trigger: operator wants to run a local model or agent inside an operator-managed VM/container and
  compare Ithildin evidence with sandbox/workshop evidence.
- Requested change: plan or run a live worker POC that invokes a local model inside a VM/container,
  observes sandbox posture, and prepares artifacts for later host-side review.
- Current boundary being changed: live worker execution, local model invocation, and sandbox run
  evidence would move beyond static fixture evidence and the current local-preview runtime boundary.
- Allowed scope: the decision-intake packet in
  `sandbox-vm-live-poc-decision-intake.md`, favorable `ERG-003` disposition tracking, decision-record
  drafting, docs, review packets, and operator warnings.
- Explicitly forbidden scope: live VM/container inspection, local model invocation, Mission Control
  runtime behavior, sandbox orchestration, SSH, shell, Docker socket access, Kubernetes tools,
  browser automation, arbitrary HTTP, broad filesystem writes, trusted-host promotion, runtime
  profile loading, production identity, SIEM adapters, and public/security-product positioning.
- Runtime surfaces touched: none.
- Runtime surfaces not touched: manifests, executors, policy/rules, API/MCP behavior, approval/audit
  logic, UI runtime behavior, Mission Control runtime behavior, sandbox/VM runtime behavior, local
  model invocation, trusted-host promotion, SIEM/telemetry, identity, storage, and remote services.
- Tool count impact: none; remains `24`.
- Manifest impact: none.
- Policy/rule impact: none.
- API/MCP impact: none.
- UI runtime impact: none.
- Mission Control impact: display-only boundary discussion only.
- Sandbox/VM impact: decision-intake evidence only.
- Local model impact: none; invocation remains blocked.
- Trusted-host promotion impact: none.
- SIEM/telemetry impact: none.
- Identity/storage/remote impact: none.
- Compliance/public-positioning impact: none.
- Required source-review or external-review evidence: favorable `ERG-003` disposition and a separate
  source/external review before any implementation plan may be proposed.
- Required implementation plan: missing; live worker behavior remains blocked.
- Required tests: decision-intake check, post-RC decision gates, packet redaction, and future
  negative transcripts before any live implementation planning.
- Required gates: `make sandbox-vm-live-poc-decision-intake-check`,
  `make post-rc-decision-gate`, `make post-rc-decision-record-template-check`, and
  `make post-rc-decision-record-examples-check`.
- Required packet artifacts: sandbox/VM live POC decision intake and a future focused review packet.
- Required negative transcripts: cleanup transcript and failure transcript are required before
  implementation planning, not created by this no-go example.
- Required accepted-risk update: required before live worker implementation planning.
- Required operator warning language: Ithildin does not run a local model, inspect a live
  VM/container, orchestrate a sandbox, or promote sandbox artifacts in this decision.
- Go/no-go outcome: no-go for live worker runtime behavior; go only for decision-intake evidence.

## Example PRD-CAPABILITY-001

- Decision ID: `PRD-CAPABILITY-001`
- Decision record status: `no_go`
- Target lane: new governed tool after the v1.0 RC freeze.
- Trigger: operator or reviewer proposes a new read-only or write-capable tool.
- Requested change: add a new manifest, executor, MCP exposure, and policy/runtime path.
- Current boundary being changed: governed tool count and runtime tool surface.
- Allowed scope: candidate selection, design packet, proposal, risk analysis, source-review request,
  and implementation plan draft.
- Explicitly forbidden scope: manifest addition, executor code, policy/rule semantics, MCP/API
  behavior, approval behavior, audit behavior, UI runtime behavior, runtime storage changes, local
  model invocation, sandbox orchestration, and trusted-host promotion.
- Runtime surfaces touched: none.
- Runtime surfaces not touched: manifests, executors, policy/rules, API/MCP behavior, approval/audit
  logic, UI runtime behavior, Mission Control runtime behavior, sandbox/VM runtime behavior, local
  model invocation, trusted-host promotion, SIEM/telemetry, identity, storage, and remote services.
- Tool count impact: none in this decision; remains `24`.
- Manifest impact: none in this decision.
- Policy/rule impact: none in this decision.
- API/MCP impact: none in this decision.
- UI runtime impact: none in this decision.
- Mission Control impact: none.
- Sandbox/VM impact: none.
- Local model impact: none.
- Trusted-host promotion impact: none.
- SIEM/telemetry impact: none.
- Identity/storage/remote impact: none.
- Compliance/public-positioning impact: none.
- Required source-review or external-review evidence: source-review handoff and finding disposition
  before implementation approval.
- Required implementation plan: required and not yet accepted.
- Required tests: proposal gate, implementation-plan gate, no-new-powers evidence, policy parity
  plan, negative transcript plan, source-review bundle check, and release/readiness wiring plan.
- Required gates: `make post-rc-decision-gate`,
  `make post-rc-decision-record-template-check`, and
  `make post-rc-decision-record-examples-check`.
- Required packet artifacts: focused capability design packet.
- Required negative transcripts: required before implementation.
- Required accepted-risk update: required before implementation.
- Required operator warning language: no new governed tool is approved by this record.
- Go/no-go outcome: no-go for runtime implementation; go for design packet work only.

## Validation

Run:

```sh
make post-rc-decision-record-examples-check
make post-rc-decision-record-template-check
make post-rc-decision-gate
```

All checks must remain green before `make release-check` can pass.
