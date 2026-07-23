# Enterprise Active Route Clarity

Status: checked active-route clarification for the current enterprise planning path.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Run:

```sh
make enterprise-active-route-clarity
```

## Active Route

The completed source-finding disposition route is `ERG-005`.

Current expected action: `await_external_operator_target_and_signed_receipt_inputs_before_separate_collection_action_authority`.

Current architecture decision:
`docs/codex/production-identity-storage-architecture-decision-record.md`.

Current active send set: none; external operator input is required.

Current valid PIS-002 continuation decision:
`docs/codex/production-identity-storage-pis-002-continuation-decision-record.md`.

Current PIS-003 posture: external-input wait; implementation remains blocked.

Current production identity/storage finding namespace: `EXT-PROD-IAM-STORAGE-###`.

The committed `sandbox-vm-live-poc-runtime-gate-readiness-decision-record.md` records an internal
High proxy disposition for descriptor-only implementation planning. The descriptor-only runtime
slice now exists as operator-attested descriptor storage only and has
`descriptor_only_local_preview_disposition_ready` recorded for continued local-development progress
only under the `EXT-LIVE-DESC-###` finding namespace.

The active route is reported by:

- `make enterprise-operator-next-action` as the canonical state reader;
- `make enterprise-current-checkpoint`;
- `make technical-mvp-execution-board`;
- `make v1-progress-assessment`;
- `make enterprise-readiness-gap-matrix-check`.

The historical review-send preflight remains a generic state check, not the instruction source for
the current PIS-003 external-input wait.

## Historical Dual-Send Lineage

Older ERG-003/ERG-002 generated packet surfaces remain in the repository for provenance and
lineage. They describe the earlier dual-send handoff, response placeholders, and historical review
packet machinery. They are not the current next action after the ERG-003/ERG-002 disposition record.

Historical dual-send route: `ERG-003`, then `ERG-002`.

The distinction is intentional:

- historical dual-send artifacts preserve evidence for prior review packets;
- completed local-development disposition artifacts preserve the `ERG-004` descriptor-only lane;
- the accepted source-finding disposition preserves the bounded `ERG-005` review result without
  closing ERG-005;
- active operator checkpoint artifacts now point to the PIS-003 external-input wait while
  `ERG-006`/`ERG-007` remain planning-only scope;
- dependency changes and PIS-003 implementation remain separately gated before runtime.

## What This Does Not Approve

This clarification does not approve runtime implementation, live VM/container inspection,
VM/container lifecycle management, sandbox orchestration, Mission Control runtime behavior, local model invocation, trusted-host promotion, network expansion, API/MCP profile loading, SIEM adapter behavior, production identity, runtime Postgres, hosted telemetry, remote MCP, compliance automation, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem writes, plugin SDK behavior, new governed tool powers, or public/security-product positioning.
