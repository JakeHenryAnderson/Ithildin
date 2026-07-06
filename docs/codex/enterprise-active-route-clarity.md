# Enterprise Active Route Clarity

Status: checked active-route clarification for the current enterprise review path.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Run:

```sh
make enterprise-active-route-clarity
```

## Active Route

The completed local-development disposition route is `ERG-004`.

Current expected action: `prepare_erg005_trusted_host_promotion_review`.

Current active packet:
`var/review-packets/v3/trusted-host-promotion-external-review/`.

Current active send set: `ERG-005`.

Current response kit:
`var/review-packets/v3/trusted-host-promotion-response-kit/`.

Current trusted-host finding namespace: `EXT-TRUSTED-HOST-###`.

The committed `sandbox-vm-live-poc-runtime-gate-readiness-decision-record.md` records an internal
High proxy disposition for descriptor-only implementation planning. The descriptor-only runtime
slice now exists as operator-attested descriptor storage only and has
`descriptor_only_local_preview_disposition_ready` recorded for continued local-development progress
only under the `EXT-LIVE-DESC-###` finding namespace.

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
- completed local-development disposition artifacts preserve the `ERG-004` descriptor-only lane;
- active operator checkpoint artifacts now point to `ERG-005`;
- current implementation planning remains external-review-gated before runtime.

## What This Does Not Approve

This clarification does not approve runtime implementation, live VM/container inspection,
VM/container lifecycle management, sandbox orchestration, Mission Control runtime behavior, local model invocation, trusted-host promotion, network expansion, API/MCP profile loading, SIEM adapter behavior, production identity, runtime Postgres, hosted telemetry, remote MCP, compliance automation, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem writes, plugin SDK behavior, new governed tool powers, or public/security-product positioning.
