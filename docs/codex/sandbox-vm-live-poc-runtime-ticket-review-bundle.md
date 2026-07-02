# Sandbox/VM Live POC Runtime Ticket Review Bundle

Status: focused review bundle for the draft-only `ERG-004` runtime ticket.

Current governed tool count: `24`.

Current `ERG-004` status: `ready_for_runtime_ticket_draft`.

Validation:

```sh
make sandbox-vm-live-poc-runtime-ticket-review-bundle
make sandbox-vm-live-poc-runtime-ticket-review-bundle-check
```

The bundle is generated under:

```text
var/review-packets/v3/sandbox-vm-live-poc-runtime-ticket-review/
```

It packages the runtime-ticket draft, runtime proposal, decision record, implementation plan,
evidence contract, negative-case requirements, and command evidence so a reviewer can decide
whether the ticket is coherent enough for a later implementation-gate sprint.

## What This Bundle Does Not Prove

This bundle does not approve runtime implementation. It does not close `ERG-004`, does not create a
runtime API, does not expose MCP behavior, and does not authorize live VM/container inspection,
VM/container lifecycle management, sandbox orchestration, Mission Control runtime behavior, local
model invocation, trusted-host promotion, host writes, network expansion, API/MCP profile loading,
SIEM adapter runtime behavior, new governed tool powers, or public/security-product positioning.

## Expected Reviewer Question

The reviewer should answer only whether the draft runtime ticket may remain as planning evidence for
a later explicit implementation gate. The reviewer must not approve runtime implementation from this
bundle alone.

## Required Outputs

The generated packet includes:

- `00_SANDBOX_VM_LIVE_POC_RUNTIME_TICKET_REVIEW_INDEX.md`
- `01_SANDBOX_VM_LIVE_POC_RUNTIME_TICKET_REVIEW_PROMPT.md`
- `02_ERG004_RUNTIME_TICKET.md`
- `03_ERG004_RUNTIME_CONTEXT.md`
- `04_ERG004_TICKET_EVIDENCE_AND_NEGATIVE_PLAN.md`
- `05_ERG004_RUNTIME_TICKET_COMMAND_EVIDENCE.md`
- `sandbox-vm-live-poc-runtime-ticket-review-artifact-hashes.json`

## Boundary

The packet is a handoff artifact only. It preserves the current local-preview boundary and keeps all
future runtime work blocked until a separate implementation gate is explicitly approved.
