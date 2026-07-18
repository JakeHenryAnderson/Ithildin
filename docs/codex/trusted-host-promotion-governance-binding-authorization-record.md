# Trusted-Host Promotion Governance-Binding Authorization Record

Status: approved bounded implementation authorization for `PRD-TRUSTED-HOST-BINDING-001`.

Decision ID: `PRD-TRUSTED-HOST-BINDING-001`.

Decision status: `approved_for_bounded_implementation`.

Approval recorded: `true`.

Authorization date: `2026-07-18`.

Authorized architecture baseline commit: `250e6d8947972de28de134b72e0561bf39c62f5f`.

Frozen version-1 writer source hashes used by the downgrade proof:

- `apps/api/src/ithildin_api/approvals.py`:
  `sha256:214bd207ac5208ecbfd6fbd5ba5ec024485edc11f88e133a5e5e699821dfec48`.
- `apps/api/src/ithildin_api/trusted_host_promotions.py`:
  `sha256:5361ac1ec20098bff482def23cbd26e3d86e5201a6f64cc03a031853b1df5eeb`.

Current governed tool count: `24`.

Run:

```sh
make trusted-host-promotion-governance-binding-authorization-record-check
```

This is the durable authorization record for the governance-binding architecture and its six-ticket
implementation packet. It separates permission to implement bounded technical changes from
permission to enable a live route, close findings, release a candidate, or claim production
readiness.

## Direct User Source

In the active Codex task on `2026-07-18`, the user asked that the repository permission settings be
changed and directed the main agent: "if something is broken and you know how to fix it, please,
just fix it." In the surrounding project context, this directly delegates implementation-level
technical decisions to the main agent instead of requiring the user to reproduce an agent-authored
API and migration approval formula.

The standing delegation is made concrete here for `PRD-TRUSTED-HOST-BINDING-001`. It authorizes the
version-2 public request contracts, SQLite table-rebuild migration, policy and approval binding,
persistence, and descriptor-relative placement work expressly defined by the architecture and
`TGB-001` through `TGB-006`.

## Bound Inputs

- Architecture:
  `docs/codex/trusted-host-promotion-governance-binding-architecture.md`.
- Implementation tickets:
  `docs/codex/trusted-host-promotion-governance-binding-implementation-tickets.md`.
- Authorized architecture baseline commit: `250e6d8947972de28de134b72e0561bf39c62f5f`.
- Architecture decision status: `approved_for_bounded_implementation`.
- Ticket sequence: `TGB-001` through `TGB-006`, in order.
- Governed tool count: `24`.
- Placement boundary: one artifact, create-exclusive, staging-only, Manager-local.
- No-new-powers boundary: no new MCP tool or governed power class.
- Review boundary: Sol Ultra is not used without the user's prior approval.

Material expansion outside those inputs requires a separate product-boundary decision. Normal
implementation detail changes that remain within them do not require another user permission
round-trip.

## Checked Permission State

```text
implementation_authorized: true
runtime_changes_allowed: true
public_contract_changes_allowed: true
database_migration_allowed: true
policy_changes_allowed: true
placement_changes_allowed: true
trusted_host_promotion_allowed: false
node_side_placement_allowed: false
new_power_classes_allowed: false
uat_required_now: false
```

`trusted_host_promotion_allowed: false` means authorization to build the control is not permission
to expose or use the live route now. Promotion remains unavailable through `TGB-004`; the route may
be enabled only after the `TGB-005` implementation, evidence, diagnostics, UI, accessibility, and
independent read-only review gates pass.

## Excluded Authority

This authorization does not permit a new MCP tool, a governed tool-count change, Node-side
placement, runner launch/control, arbitrary host writes, overwrite/delete/move behavior, Docker or
Kubernetes control, browser automation, production identity, enterprise RBAC, runtime Postgres,
hosted telemetry, remote MCP, SIEM delivery, compliance automation, public security-product claims,
or Sol Ultra review.

It also does not approve release, production promotion, external finding closure, or human UAT.
Those states remain controlled by their own exact-candidate evidence and human gates.

## Execution And Review Boundary

- One Sol implementation owner holds runtime and integration edits.
- Each ticket is a separately reviewable commit with focused tests before broader gates.
- `TGB-006` may record only
  `implementation_candidate_ready_for_independent_re_review` internally.
- Independent exact-candidate response intake, not internal review or packet creation, controls
  external finding disposition.
- Tests and generated evidence do not authorize production promotion, release, closure, or UAT
  acceptance.

No human UAT is required to execute `TGB-001` through `TGB-006`. UAT remains a later exact-candidate
operator-feel gate.
