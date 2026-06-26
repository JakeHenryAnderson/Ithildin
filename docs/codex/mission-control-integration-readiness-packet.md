# Mission Control Integration Readiness Packet

Status: planning-only cross-repo readiness packet for the future Mission Control display/importer
lane.

Current governed tool count: `24`.

Current selected capability: `not selected`.

This packet consolidates Ithildin's existing Mission Control display/importer evidence into one
handoff-oriented review artifact. It is meant to help decide whether the Mission Control-side
display/import implementation can continue planning and repository-local implementation work while
Ithildin remains the governed gateway.

It does not approve runtime behavior in Ithildin, Mission Control execution authority, policy
authority, approval authority, audit authority, local model invocation, VM/container lifecycle
control, sandbox orchestration, trusted-host promotion, SIEM adapter behavior, production identity,
runtime Postgres, hosted telemetry, remote MCP, compliance automation, or public/security-product
positioning.

## Purpose

The readiness packet gathers the materials a Mission Control implementer or reviewer needs before
touching that repository:

- the display-only integration proposal;
- the importer implementation plan;
- the decision-intake and disposition packet;
- the side handoff plan and concrete implementation ticket;
- the metadata-only handoff schema contract;
- the negative fixture expectations;
- the observed hello-world Mission Control handoff seed;
- command evidence proving the Ithildin-side planning checks still pass.

## Generated Packet

Generate the packet from the Ithildin repository:

```sh
make mission-control-integration-readiness-packet
```

Validate the packet wiring without running the full command transcript:

```sh
make mission-control-integration-readiness-packet-check
```

The generated packet is written under:

```text
var/review-packets/v3/mission-control-integration-readiness/
```

## Boundary Flags

The generated evidence must continue to report:

- `tool_count: 24`;
- `erg_002_status: planning_only`;
- `prd_id: PRD-MC-DISPLAY-001`;
- `runtime_changes_allowed: false`;
- `mission_control_runtime_allowed: false`;
- `mission_control_execution_authority_allowed: false`;
- `mission_control_policy_authority_allowed: false`;
- `mission_control_approval_authority_allowed: false`;
- `mission_control_audit_authority_allowed: false`;
- `local_model_invocation_allowed: false`;
- `sandbox_orchestration_allowed: false`;
- `trusted_host_promotion_allowed: false`;
- `siem_adapter_allowed: false`;
- `new_power_classes_allowed: false`;
- `closes_erg_002: false`.

## Review Question

The readiness packet asks whether the Mission Control-side display/importer work order is complete
enough to hand to the Mission Control repository as a display-only implementation task.

It does not ask a reviewer to approve runtime integration, callbacks, execution controls,
approval/replay/repair flows, local model invocation, VM/container management, sandbox controls,
trusted-host promotion, SIEM export, compliance automation, or production/security-product claims.

## Done When

This readiness artifact is complete when:

- the generated packet includes the Mission Control display, handoff, schema, fixture, and ticket
  docs;
- command evidence is available or explicitly marked skipped in check mode;
- artifact hashes cover generated markdown files;
- release/readiness gates include the packet check;
- `review-candidate` regenerates the packet;
- the packet still states that `ERG-002` is planning-only and not closed.
