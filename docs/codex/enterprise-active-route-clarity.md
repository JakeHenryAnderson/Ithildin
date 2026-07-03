# Enterprise Active Route Clarity

Status: checked active-route clarification for the current enterprise review path.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Run:

```sh
make enterprise-active-route-clarity
```

## Active Route

The active post-disposition route is `ERG-004`.

Current expected action: `prepare_erg004_descriptor_only_runtime_planning`.

Current active packet: `sandbox-vm-live-poc-runtime-ticket-review`.

Current active send set: `ERG-004`.

Current runtime gate-readiness packet:
`var/review-packets/v3/sandbox-vm-live-poc-runtime-gate-readiness-review`.

The committed `sandbox-vm-live-poc-runtime-gate-readiness-decision-record.md` records an internal
High proxy disposition for descriptor-only implementation planning. It keeps runtime implementation
blocked until a separate implementation sprint and source-review gate exist.

The active route is reported by:

- `make enterprise-review-send-preflight`;
- `make enterprise-current-checkpoint`;
- `make enterprise-operator-next-action`;
- `make technical-mvp-execution-board`.

## Historical Dual-Send Lineage

Older ERG-003/ERG-002 generated packet surfaces remain in the repository for provenance and
lineage. They describe the earlier dual-send handoff, response placeholders, and historical review
packet machinery. They are not the current next action after the ERG-003/ERG-002 disposition record.

Historical dual-send route: `ERG-003`, then `ERG-002`.

The distinction is intentional:

- historical dual-send artifacts preserve evidence for prior review packets;
- active operator checkpoint artifacts point to `ERG-004`;
- current implementation planning remains external-review-gated before runtime.

## What This Does Not Approve

This clarification does not approve runtime implementation, live VM/container inspection,
VM/container lifecycle management, sandbox orchestration, Mission Control runtime behavior, local model invocation, trusted-host promotion, network expansion, API/MCP profile loading, SIEM adapter behavior, production identity, runtime Postgres, hosted telemetry, remote MCP, compliance automation, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem writes, plugin SDK behavior, new governed tool powers, or public/security-product positioning.
