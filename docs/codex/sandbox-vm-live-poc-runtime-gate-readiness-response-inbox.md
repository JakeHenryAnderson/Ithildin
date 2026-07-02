# Sandbox/VM Live POC Runtime Gate Readiness Response Inbox

Status: generated response inbox for the active ERG-004 runtime gate-readiness review.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Run:

```sh
make sandbox-vm-live-poc-runtime-gate-readiness-response-inbox
make sandbox-vm-live-poc-runtime-gate-readiness-response-inbox-check
```

This inbox creates ignored local artifacts under:

```text
var/review-runs/sandbox-vm-live-poc-runtime-gate-readiness-response-inbox/
```

It gives the active `EXT-LIVE-GATE-###` response path an exact raw-response placeholder, reviewed
packet hash, and normalization command for the current runtime gate-readiness packet:

```text
var/review-packets/v3/sandbox-vm-live-poc-runtime-gate-readiness-review
```

## What It Does

- Creates `RAW_RESPONSE_ERG-004-RUNTIME-GATE-READINESS.md`.
- Creates `ERG004_RUNTIME_GATE_READINESS_CHEATSHEET.md`.
- Creates `erg004-runtime-gate-readiness-response-inbox.json`.
- Creates `erg004-runtime-gate-readiness-response-inbox-artifact-hashes.json`.
- Records the exact `sandbox-vm-live-poc-runtime-gate-readiness` normalization area.
- Records the `EXT-LIVE-GATE-###` finding namespace.
- Records the reviewed packet hash for the generated gate-readiness review packet.

## What It Does Not Do

This inbox does not normalize responses, does not write normalized response files, does not mutate
findings, does not record external review, does not close `ERG-004`, approve descriptor-only
implementation planning, approve runtime
implementation, approve live VM/container inspection, approve VM/container lifecycle management,
approve sandbox orchestration, approve Mission Control runtime behavior, approve local model
invocation, approve trusted-host promotion, approve host writes, approve network expansion, approve
API/MCP profile loading, approve new governed tool powers, or approve public/security-product
positioning.

## Use Order

1. Run `make sandbox-vm-live-poc-runtime-gate-readiness-response-inbox`.
2. Paste a real `EXT-LIVE-GATE-###` reviewer response into the generated raw-response placeholder.
3. Use the generated cheat sheet's normalizer command so the reviewed packet hash is exact.
4. Run `make sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run`.
5. Run `make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton-check`.
6. Commit a later decision-record update only if the normalized response explicitly supports the
   allowed transition and no critical/high `EXT-LIVE-GATE-###` finding is open.

The only later transition this path can support is:

```text
ready_for_runtime_implementation_gate_review -> ready_for_descriptor_only_runtime_implementation_planning
```

That transition still does not approve runtime implementation.

## Validation

Run:

```sh
make sandbox-vm-live-poc-runtime-gate-readiness-response-inbox-check
make sandbox-vm-live-poc-runtime-gate-readiness-response-intake-check
make sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run
make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton-check
```
