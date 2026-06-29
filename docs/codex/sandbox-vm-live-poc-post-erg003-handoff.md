# Sandbox/VM Live POC Post-ERG-003 Handoff

Status: post-`ERG-003` handoff map for still-blocked `ERG-004`.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Current `ERG-004` status: `blocked`.

This handoff explains what to do after a favorable `ERG-003` static sandbox/VM preflight
disposition is recorded. It is a planning bridge only. It does not approve live VM/container
inspection, VM/container lifecycle management, sandbox orchestration, Mission Control runtime
behavior, local model invocation, trusted-host promotion, network expansion, API/MCP profile
loading, SIEM adapter behavior, production identity, runtime Postgres, hosted telemetry, remote MCP,
compliance automation, public/security-product positioning, or new governed tool powers.

## When This Applies

Use this handoff only after all of these are true:

- the `ERG-003` external/source reviewer response has been normalized through the static preflight
  response path;
- `make sandbox-vm-static-preflight-disposition-closure-check` reports favorable closure evidence;
- the committed static-preflight disposition record follows
  `sandbox-vm-static-preflight-disposition-record-skeleton.md`;
- all critical/high static-preflight findings are closed or explicitly stop the lane;
- `make sandbox-vm-live-poc-preconditions-ready-check` still reports `ERG-004` as blocked until a
  separate decision record exists.

If any item is false, keep `ERG-004` blocked and return to the relevant response kit or static
preflight closure gate.

## Post-ERG-003 Sequence

After favorable `ERG-003` evidence is committed, use this sequence:

```sh
make sandbox-vm-live-poc-preconditions-map-check
make sandbox-vm-live-poc-preconditions-ready-check
make sandbox-vm-live-poc-decision-packet
make sandbox-vm-live-poc-decision-packet-check
make sandbox-vm-live-poc-external-review-bundle
make sandbox-vm-live-poc-external-review-bundle-check
make sandbox-vm-live-poc-response-kit
make sandbox-vm-live-poc-response-kit-check
make no-new-powers-guardrail
make tool-surface-invariant-gate
```

The expected safe state after this sequence is still:

- `ERG-004` remains `blocked`;
- `ready_for_implementation_planning: false` until a later committed decision record exists;
- live VM/container inspection remains blocked;
- local model invocation remains blocked;
- Mission Control runtime behavior remains blocked;
- sandbox orchestration remains blocked;
- trusted-host promotion remains blocked;
- network expansion remains blocked;
- tool count remains `24`.

## Decision Record Boundary

Only a later committed `PRD-SANDBOX-LIVE-POC-001` decision record may move `ERG-004` from
`blocked` to an implementation-planning state. That decision record must reference:

- the favorable `ERG-003` disposition record;
- the current live POC preconditions-ready report;
- the live POC decision packet;
- the live POC external response intake or reviewer disposition;
- unresolved-finding status;
- no-new-powers and tool-surface evidence.

Even a favorable decision record may approve only implementation planning unless it explicitly
authorizes a later implementation gate. Runtime implementation remains separate.

## What This Handoff Does Not Prove

This handoff does not prove `ERG-003` is closed, does not prove `ERG-004` is ready, does not prove a
sandbox is safe, and does not prove a local model may be invoked. It is a deterministic operator
bridge so the project can resume cleanly after `ERG-003` without accidentally skipping the blocked
`ERG-004` decision gate.

Validate this handoff with:

```sh
make sandbox-vm-live-poc-post-erg003-handoff-check
```
