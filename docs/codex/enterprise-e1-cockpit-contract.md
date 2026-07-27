# Enterprise E1 Command Center Cockpit Contract

Status: `E1-M4` operator-view contract. Command Center is an authenticated presentation and
workflow-initiation client for existing Gateway APIs. It is not a second policy, approval,
execution, audit, runner, model-provider, or host-control authority.

## Operator view

The E1 cockpit presents:

- Gateway mission admission and lifecycle, Node delivery, runner-reported observations, and exact
  governed-run correlation;
- Gateway-derived Node identity and governed-access posture;
- Gateway-accepted signed-heartbeat connectivity, with runner, model, and host-process health left
  unknown;
- desired and observed software-version posture;
- signed desired configuration compared with Node-attested storage, without claiming Node-side
  enforcement;
- deterministic Attention states derived from loaded Gateway records;
- Gateway-recorded approvals and bounded evidence closeout.

The machine-readable source and wording bindings live in
[`enterprise-e1-cockpit-contract.json`](enterprise-e1-cockpit-contract.json).

## Authority and actions

Command Center may submit only already-governed Gateway workflows. Mission admission uses a
server-owned template and an eligible Node; it does not accept a free-form runner objective.
Cancellation records a Gateway decision and does not prove runner-process termination. Node
configuration, trust transition, revocation, enrollment, and approval controls call their existing
authenticated Gateway endpoints and retain the server's validation and evidence requirements.

The UI does not call a runner or model provider directly, execute shell commands, manage Docker or
Kubernetes, or infer success from browser-local state.

## Accessibility evidence and stop line

The focused interaction harness verifies semantic destination regions, the keyboard skip path,
focus transfer for navigation and remediation, descriptive labels, non-color state, and announced
asynchronous status/error text. Production build and TypeScript checks verify the integrated UI
surface.

This engineering evidence is not a WCAG conformance claim, screen-reader certification, or fresh
human acceptance. Representative keyboard-only, high-zoom, narrow-viewport, and assistive-
technology behavior remains part of genuine human UAT and is not marked complete here.

## Validation

```sh
make enterprise-e1-cockpit-check
```

The gate checks the closed machine contract, implementation/source labels, existing governed API
bindings, focused UI behavior, type safety, and production build. It does not authorize release,
production promotion, or human-UAT completion.
