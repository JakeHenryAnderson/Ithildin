# Trusted-Host Promotion Source-Review Handoff

Status: design/source-review handoff for `ERG-005` and `PRD-TRUSTED-HOST-001`.

Current governed tool count: `24`.

Current `ERG-005` status: `blocked`.

Current selected capability: `not selected`.

This handoff is the `ERG-005` Goal B source-review/runtime-boundary packet. It packages the
design-only trusted-host promotion lane for focused review after the Goal A planning contract. The
review question is whether the hardened contract is precise enough for a later Goal C
implementation-gate decision to be considered. It does not approve runtime behavior, direct host writes,
overwrite/delete/move behavior, broad archive extraction, automatic promotion, promotion without
exact artifact hash binding, promotion without approval evidence, API/MCP behavior, Mission Control
runtime behavior, local model invocation, VM/container lifecycle management, sandbox orchestration,
SIEM adapters, production identity, runtime Postgres, hosted telemetry, shell,
Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem writes, compliance
automation, or public/security-product claims.
It does not implement promotion behavior.

Generate the handoff packet with:

```sh
make trusted-host-promotion-source-review-packet
```

Validate the packet wiring with:

```sh
make trusted-host-promotion-source-review-packet-check
```

Default output:

```text
var/review-packets/v3/trusted-host-promotion-source-review/
```

Finding namespace: `EXT-TRUSTED-HOST-###`.

## Review Scope

The reviewer should inspect whether the current evidence is coherent enough to continue toward a
future Goal C decision record, while keeping runtime promotion blocked. The packet includes:

- `sandbox-promotion-evidence-contract.md`;
- `trusted-host-descriptor-contract.md`;
- `trusted-host-promotion-decision-intake.md`;
- `trusted-host-promotion-state-machine.md`;
- `trusted-host-promotion-negative-fixtures.md`;
- `trusted-host-promotion-zone-contract.md`;
- `trusted-host-promotion-implementation-plan.md`;
- `v3-trusted-host-promotion-internal-review.md`;
- post-RC decision-gate and decision-register evidence;
- no-new-powers and tool-surface invariant evidence.

## Required Reviewer Questions

The focused reviewer should answer:

1. Is the trusted host descriptor contract strict enough to keep host posture evidence
   operator-reviewed, secret-free, descriptor-only, and unable to authorize host control?
2. Are the source/staging/approved zone labels precise enough for a future implementation plan?
3. Does the implementation-plan contract require exact artifact hash binding, approval binding,
   one-time scope evidence, and stale/replay/conflict denials before any runtime path?
4. Are approval consumption, one-time scope, and diagnostics requirements strict enough to prevent
   replay, ambiguous completion, and silent host-write state drift?
5. Are the stop conditions strict enough to block arbitrary host paths, overwrite/delete/move,
   automatic promotion, broad archive extraction, Mission Control runtime authority, sandbox
   orchestration, local model invocation, SIEM adapter behavior, and compliance claims?
6. What source-review artifacts, negative transcripts, or decision records are still missing before
   a future implementation proposal may be considered?
7. Can a later Goal C implementation-gate decision be prepared, or should `ERG-005` remain blocked
   before runtime-boundary planning proceeds?

## Required Disposition

The reviewer may only choose:

- `continue_design_only`: current evidence is coherent for further design and review packets.
- `prepare_goal_c_decision_gate`: current evidence is coherent enough to draft a later Goal C
  implementation-gate decision while runtime implementation remains blocked until that decision exists
  and passes.
- `revise_before_more_planning`: gaps or ambiguous claims must be fixed before more planning.
- `block_runtime_implementation`: a blocking risk prevents any implementation planning until a new
  decision record resolves it.

The reviewer must not approve runtime implementation, host promotion, direct host writes,
overwrite/delete/move, archive extraction, automatic promotion, Mission Control execution authority,
local model invocation, VM/container lifecycle control, sandbox orchestration, SIEM adapters,
production identity, runtime Postgres, hosted telemetry, remote MCP, shell/Docker/Kubernetes/browser
governed powers, arbitrary HTTP, broad filesystem writes, compliance automation, or
public/security-product positioning.

Reviewer responses should be captured through
[trusted-host-promotion-external-response-intake.md](trusted-host-promotion-external-response-intake.md),
which validates the `EXT-TRUSTED-HOST-###` finding namespace and keeps `ERG-005` blocked until a
later committed triage update changes the decision register.

## Current Boundary

Current runtime/demo evidence may only report `promotion_status: not_promoted`.

## Current Output Flags

Current outputs must continue to report:

- decision record required: `true`;
- implementation approved: `false`;
- runtime changes allowed: `false`;
- trusted-host promotion allowed: `false`;
- direct host writes allowed: `false`;
- overwrite/delete/move allowed: `false`;
- broad archive extraction allowed: `false`;
- automatic promotion allowed: `false`;
- promotion without exact artifact hash binding allowed: `false`;
- promotion without approval evidence allowed: `false`;
- Mission Control runtime allowed: `false`;
- local model invocation allowed: `false`;
- sandbox orchestration allowed: `false`;
- SIEM adapter allowed: `false`;
- new power classes allowed: `false`;
- public/security-product positioning allowed: `false`.
