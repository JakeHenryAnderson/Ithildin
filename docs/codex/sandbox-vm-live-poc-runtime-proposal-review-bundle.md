# Sandbox/VM Live POC Runtime Proposal Review Bundle

Status: checked external-review gate for the `ERG-004` runtime proposal.

Current `ERG-004` status: `ready_for_runtime_proposal_review`.

Commands:

```sh
make sandbox-vm-live-poc-runtime-proposal-review-bundle
make sandbox-vm-live-poc-runtime-proposal-review-bundle-check
```

Generated output:

```text
var/review-packets/v3/sandbox-vm-live-poc-runtime-proposal-review/
```

This bundle packages the runtime-proposal layer after the ERG-004 implementation-planning packet.
It asks whether a bounded runtime implementation ticket may be drafted for a later gate. It does not
approve runtime implementation, live VM/container inspection, VM/container lifecycle management,
sandbox orchestration, Mission Control runtime behavior, local model invocation, trusted-host
promotion, host writes, network expansion, API/MCP profile loading, SIEM adapter behavior, new
governed tool powers, or public/security-product positioning.

The generated packet includes:

- runtime proposal;
- implementation-planning packet;
- decision record and active-route clarity;
- evidence and precondition contracts;
- descriptor and negative-plan review summary;
- command evidence;
- artifact hashes.
