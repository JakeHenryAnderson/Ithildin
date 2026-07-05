# Enterprise Sandbox Control-Plane Readiness

Status: design-only readiness map for the post-v1.0 sandbox/control-plane path.

Current governed tool count: `24`.

Current selected capability: `not selected`.

This document connects the Mission Control display lane, sandbox/VM static preflight lane, live
sandbox/VM proof-of-concept lane, and trusted-host promotion lane into one enterprise-readiness
control-plane map. It does not approve live VM/container inspection, sandbox orchestration, local
model invocation, Mission Control runtime behavior, trusted-host promotion, SIEM adapter behavior,
production identity, runtime Postgres, compliance automation, public/security-product positioning,
or any new governed tool power.

It does not approve sandbox orchestration.

It does not approve local model invocation.

The live sandbox/VM proof-of-concept runtime remains blocked. `ERG-004` has moved through
implementation-planning, runtime-proposal, implementation-gate, and descriptor-only implementation
planning into a bounded descriptor-only runtime slice that is source-review pending. That slice
records operator-attested descriptors only; it still does not inspect, start, stop, pause, snapshot,
shell into, or verify a VM/container.

`ERG-003` is recorded as `closed_local_preview_static_preflight`; this records the CLI-only static
preflight local-preview disposition and does not approve `ERG-004` live VM/container inspection or
runtime implementation.

## Current Source Of Truth

| Lane | Current status | Current evidence | Next allowed action |
| --- | --- | --- | --- |
| `ERG-002` Mission Control display/importer | `planning_only` | `mission-control-display-disposition-packet.md`, `mission-control-display-disposition-closure-gate.md`, `mission-control-side-handoff-plan.md`, `mission-control-integration-implementation-ticket.md` | Mission Control-side display-only planning and source-review preparation |
| `ERG-003` Sandbox/VM static preflight | `closed_local_preview_static_preflight` | `enterprise-dual-response-disposition-record.md`, `sandbox-vm-static-preflight-disposition-packet.md`, `sandbox-vm-static-preflight-disposition-plan.md`, `sandbox-vm-static-preflight-external-response-intake.md`, `sandbox-vm-static-preflight-triage-update.md` | Recorded disposition for CLI-only static preflight local-preview evidence |
| `ERG-004` Live sandbox/VM worker proof of concept | `descriptor_only_runtime_implemented_source_review_pending` | `sandbox-vm-live-poc-decision-intake.md`, `sandbox-vm-live-poc-evidence-contract.md`, `sandbox-vm-live-poc-preconditions-ready-check.md`, `sandbox-vm-live-poc-decision-packet.md`, `sandbox-vm-live-poc-external-review-bundle.md`, `sandbox-vm-live-poc-response-kit.md`, `sandbox-vm-live-poc-decision-record-skeleton.md`, `sandbox-vm-live-poc-decision-record.md`, `sandbox-vm-live-poc-implementation-plan.md`, `sandbox-vm-live-poc-runtime-proposal.md`, `sandbox-vm-live-poc-runtime-descriptor-only-implementation.md`, `sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle.md`, `sandbox-vm-live-poc-runtime-descriptor-only-response-inbox.md`, `sandbox-vm-live-poc-runtime-descriptor-only-send-receipt.md`, `sandbox-vm-live-poc-decision-closure-gate.md`, `sandbox-vm-live-poc-response-dry-run.md`, `sandbox-vm-live-poc-prerequisite-disposition-dry-run.md` | Descriptor-only source-review response is pending; VM/container inspection, lifecycle control, local model invocation, host writes, network expansion, and runtime work beyond operator-attested descriptor storage remain blocked |
| `ERG-005` Trusted-host artifact promotion | `staging_only_runtime_source_review_ready` | `trusted-host-promotion-source-review.md`, `trusted-host-promotion-disposition-packet.md`, `trusted-host-promotion-response-kit.md`, `trusted-host-promotion-disposition-closure-gate.md`, `trusted-host-promotion-response-dry-run.md`, `v3-trusted-host-promotion-internal-review.md`, `trusted-host-promotion-decision-record.md`, `trusted-host-promotion-implementation-gate-decision.md`, `trusted-host-promotion-runtime-implementation-decision.md`, `trusted-host-promotion-runtime-implementation.md`, `v3-trusted-host-promotion-runtime-internal-review.md`, `trusted-host-promotion-runtime-source-review.md` | The staging-only single-artifact runtime slice is implemented and ready for focused source review; broad trusted-host promotion, approved-output publishing, direct arbitrary host writes, automatic promotion, and new powers remain blocked |

## Enterprise Claim Map

Allowed current claims:

- Ithildin can represent local-preview Agent Run, audit, approval, and packet evidence.
- Ithildin can generate static sandbox profile and preflight evidence for review.
- Ithildin can record operator-attested sandbox/VM descriptor evidence while preserving false
  authority flags for live inspection, lifecycle control, Mission Control runtime authority,
  trusted-host promotion, host writes, network expansion, and local model invocation.
- Mission Control may be discussed as a display/import planning surface only.
- Trusted-host promotion may be discussed as a blocked future lane with state-machine and
  negative-fixture evidence.

Blocked current claims:

- Ithildin manages or starts VMs, containers, local models, or sandboxes.
- Ithildin provides OS isolation, host-compromise resistance, or a sandbox guarantee.
- Mission Control executes, approves, audits, governs, or mutates Ithildin actions.
- Sandbox artifacts can be promoted into host staging or approved zones.
- Live VM/container inspection, local model invocation, shell, Docker socket, Kubernetes, browser
  automation, arbitrary HTTP, broad filesystem writes, or network expansion are approved.
- SIEM custody, compliance automation, production identity, runtime Postgres, hosted telemetry,
  remote MCP, or public/security-product positioning are approved.

## Required Future Promotion Path

The live sandbox/VM POC runtime lane beyond descriptor-only records must stay blocked until all of
these are true:

1. `ERG-003` remains recorded as `closed_local_preview_static_preflight` with no unresolved
   critical/high findings.
2. A post-RC decision record names the reviewed commit, evidence packet, allowed planning scope,
   forbidden runtime behavior, and stop conditions.
3. The descriptor-only source-review response is recorded, normalized, and dispositioned without
   critical/high findings.
4. Any future implementation-planning packet keeps the VM/container lifecycle operator-managed and
   does not add shell, Docker socket, Kubernetes, browser automation, arbitrary HTTP, broad writes,
   Mission Control runtime authority, trusted-host promotion, SIEM delivery, or compliance
   automation.

## Validation

Run:

```sh
make enterprise-sandbox-control-plane-readiness-check
make sandbox-vm-live-poc-decision-packet-check
make sandbox-vm-live-poc-decision-closure-check
make sandbox-vm-live-poc-decision-packet
```

These commands are review/evidence preparation only. They do not perform live sandbox inspection,
do not invoke local models, do not run governed tool calls, and do not create runtime authority.
