# Sandbox/VM Live POC Runtime Gate Readiness Decision Record Skeleton

Status: design-only decision-record skeleton for the `ERG-004` runtime gate-readiness review.

Current governed tool count: `24`.

Current `ERG-004` status: `ready_for_runtime_implementation_gate_review`.

Current selected capability: `not selected`.

This skeleton gives a future reviewer disposition for
`sandbox-vm-live-poc-runtime-gate-readiness-review` a safe landing zone. It does not approve runtime
implementation, live VM/container inspection, VM/container lifecycle management, sandbox
orchestration, Mission Control runtime behavior, local model invocation, trusted-host promotion,
host writes, network expansion, API/MCP profile loading, SIEM adapter runtime behavior, production
identity, runtime Postgres, hosted telemetry, remote MCP, compliance automation,
shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem writes, plugin SDK
behavior, new governed tool powers, or public/security-product positioning.

Use this skeleton only after:

- `make sandbox-vm-live-poc-runtime-ticket-internal-review-check` passes;
- `make sandbox-vm-live-poc-runtime-implementation-gate-check` passes;
- `make sandbox-vm-live-poc-runtime-descriptor-contract-check` passes;
- `make sandbox-vm-live-poc-runtime-descriptor-contract-internal-review-check` passes;
- `make sandbox-vm-live-poc-runtime-gate-readiness-review-bundle-check` passes;
- `make sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run` passes;
- a future `EXT-LIVE-GATE-###` source/packet review explicitly says a descriptor-only runtime
  implementation sprint may be planned later;
- no critical/high `EXT-LIVE-GATE-###` finding is open;
- the reviewed packet hash and reviewed commit match the generated gate-readiness review bundle.

## Allowed Decision Outcome

The only outcome this skeleton may support is:

```text
approved_for_descriptor_only_runtime_implementation_planning
```

The only allowed lane movement is:

```text
ERG-004: ready_for_runtime_implementation_gate_review -> ready_for_descriptor_only_runtime_implementation_planning
```

That movement would mean a later implementation-planning sprint may draft a descriptor-only runtime
slice. It still does not approve runtime implementation.

## Decision Header

- Decision ID: `PRD-SANDBOX-LIVE-GATE-001`
- Date:
- Owner:
- Reviewer:
- Target lane: `ERG-004` live sandbox/VM worker proof of concept.
- Review stage: runtime gate-readiness.
- Related packet:
  `var/review-packets/v3/sandbox-vm-live-poc-runtime-gate-readiness-review`
- Related response intake:
  `sandbox-vm-live-poc-runtime-gate-readiness-response-intake.md`
- Related prompt:
  `var/review-packets/v3/sandbox-vm-live-poc-runtime-gate-readiness-review/01_SANDBOX_VM_LIVE_POC_RUNTIME_GATE_READINESS_PROMPT.md`
- Related findings: `EXT-LIVE-GATE-###` if present.

## Scope

Runtime behavior remains blocked.

- Allowed scope after a favorable disposition: plan a descriptor-only implementation sprint that
  validates operator-supplied descriptors, safe labels, hashes, timestamps, enums, and correlations
  with existing Agent Run, approval, audit, and signed-export evidence.
- Explicitly forbidden scope: runtime implementation, live VM/container inspection,
  VM/container lifecycle management, sandbox orchestration, Mission Control runtime behavior, local
  model invocation, trusted-host promotion, host writes or artifact promotion, network expansion,
  API/MCP profile loading, SIEM adapter runtime behavior, production identity, runtime Postgres,
  hosted telemetry, remote MCP, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP,
  broad filesystem writes, plugin SDK behavior, compliance automation, new governed tool powers, or
  public/security-product positioning.
- Runtime surfaces touched: none.
- Runtime surfaces not touched: Ithildin manifests, executors, policy/rules, API/MCP behavior,
  approval/audit logic, UI runtime behavior, Mission Control runtime behavior, sandbox/VM runtime
  behavior, local model invocation, trusted-host promotion, SIEM/telemetry, identity, storage, and
  remote services.
- Tool count impact: none; remains `24`.
- Manifest impact: none.
- Policy/rule impact: none.
- API/MCP impact: none.
- UI runtime impact: none.

## Required Evidence

- Required packet evidence:
  `var/review-packets/v3/sandbox-vm-live-poc-runtime-gate-readiness-review`.
- Required response intake:
  `sandbox-vm-live-poc-runtime-gate-readiness-response-intake.md`.
- Required response dry run:
  `sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run.md`.
- Required reviewed commit: the reviewed commit in the packet must match the current committed
  checkpoint being dispositioned.
- Required reviewed packet hash: artifact hashes must match the generated packet files.
- Required reviewer disposition: an `EXT-LIVE-GATE-###` review must explicitly approve planning a
  descriptor-only runtime implementation sprint later.
- Required negative finding state: no critical/high `EXT-LIVE-GATE-###` finding is open.
- Required command evidence:
  `make sandbox-vm-live-poc-runtime-gate-readiness-response-intake-check`,
  `make sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run`,
  `make sandbox-vm-live-poc-runtime-gate-readiness-review-bundle-check`,
  `make sandbox-vm-live-poc-runtime-implementation-gate-check`,
  `make sandbox-vm-live-poc-runtime-descriptor-contract-check`,
  `make sandbox-vm-live-poc-runtime-descriptor-contract-internal-review-check`,
  `make no-new-powers-guardrail`, `make tool-surface-invariant-gate`, and `make release-check`.
- Required future implementation plan: still required before any runtime implementation.
- Required source review: still required after any future descriptor-only implementation exists.

## Stop Conditions

Stop before any later planning or implementation if the proposed work requires VM/container
lifecycle authority, live VM/container inspection, local model invocation, Mission Control runtime
authority, trusted-host promotion, host writes, network expansion, API/MCP profile loading,
new governed powers, or stronger product claims.

Escalate to High review first if repeated gate failures or unclear implementation boundaries appear.
Escalate to XHigh or GPT 5.5 Pro / human review only if a critical/high finding appears or the
product boundary becomes ambiguous.

## Validation

Run:

```sh
make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton-check
make sandbox-vm-live-poc-runtime-gate-readiness-review-bundle-check
make sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run
```

These checks must remain green before `make release-check` can pass.
