# Ithildin Enterprise Readiness Runway

Status: design-only runway beyond the v1.0 local-preview RC.

This runway describes how Ithildin can evolve from a local-first governed MCP workbench into an
enterprise-ready governed agent platform. It does not add runtime behavior, tool manifests,
executors, policy rules, API endpoints, MCP transports, Mission Control runtime behavior, sandbox
orchestration, SIEM adapters, production identity, runtime Postgres, hosted telemetry, shell,
Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem writes, compliance
automation, or public/security-product claims.

## Current Baseline

- Current governed tool count: `24`.
- Current selected capability: `not selected`.
- Current release posture: v1.0 local-preview RC path.
- Current workbench posture: local review console, Agent Run evidence, approval evidence, audit
  evidence, locally signed exports, demo packets, and metadata-only Mission Control handoff.
- Current sandbox posture: bounded sandbox-labeled artifact writes exist; VM/container lifecycle
  management and trusted-host promotion remain future gated lanes.

## Enterprise Target Shape

The long-term product should become a governed control plane around agent work:

1. Mission Control remains the operator-facing mission/run dashboard.
2. Ithildin remains the policy, approval, execution, redaction, and evidence gateway.
3. Sandbox/VM workers remain isolated execution environments managed by an explicit sandbox layer.
4. Host-side movement uses staged zones: source/inbox, sandbox working area, host staging, approved
   output, and evidence.
5. Enterprise integrations remain adapters around the governed core, not replacements for policy,
   approval, or audit evidence.

This target is feasible only if the future implementation preserves the separation between
operator UI, governed gateway, sandbox runtime, identity provider, storage layer, and evidence
export layer.

## Phase E1: Local RC Freeze And Trusted User Trial

Goal: finish v1.0 as a local-preview release candidate and gather hands-on operator feedback.

Required evidence:

- `make release-check` passes from a clean tree.
- `make review-candidate` passes and packet redaction reports `findings: 0`.
- `make v1-rc-packet` includes the current status, workbench evidence, assurance map, artifact map,
  command list, and artifact hashes.
- External/source-review pending rows remain visible.

Exit criteria:

- no critical/high local-preview findings remain open;
- no next capability is selected;
- public/security-product positioning remains blocked;
- operator quickstart can be followed without reading historical packet archaeology.

## Phase E2: Mission Control Display Integration

Goal: let Mission Control display Ithildin evidence without controlling execution.

Allowed design scope:

- import/display of evidence labels, hashes, run IDs, approval IDs, warning chips, artifact links,
  and local-preview status;
- read-only cross-linking from Mission Control mission IDs to Ithildin Agent Run/evidence IDs;
- operator copy/paste or file-import workflow for generated handoff packets.

Required before implementation:

- Mission Control integration proposal;
- data contract for imported evidence fields;
- negative cases for stale evidence, mismatched hashes, unsupported packet versions, and missing
  warning state;
- source-review handoff for both Mission Control and Ithildin changes.

Blocked:

- Mission Control execution authority;
- Mission Control policy authority;
- approval bypass;
- sandbox/VM lifecycle control;
- trusted-host promotion.

## Phase E3: Sandbox/VM Worker Proof Of Concept

Goal: demonstrate a local agent working inside an operator-managed sandbox/VM while Ithildin records
governed evidence.

Allowed design scope:

- sandbox identity and posture evidence;
- operator-managed workspace mount labels;
- preflight checks for supported local sandbox profiles;
- Mission Control display of sandbox/run/evidence linkage.

Required before implementation:

- sandbox worker boundary charter;
- sandbox/VM profile contract;
- supported platform matrix;
- mount/root contract;
- network posture contract;
- artifact ingress/egress contract;
- failure and cleanup transcripts;
- sandbox/VM preflight contract tying the matrix, posture, ingress/egress, warning, and cleanup
  evidence into one go/no-go decision;
- external/source review before any claim of sandbox safety.

Blocked:

- Ithildin starting containers or VMs;
- Docker socket access;
- Kubernetes control;
- shell execution;
- browser automation;
- broad filesystem writes;
- OS-isolation or host-compromise-resistance claims.

## Phase E4: Trusted-Host Promotion Lane

Goal: move approved sandbox artifacts into a host staging/approved zone with strong evidence.

Required before implementation:

- explicit capability proposal;
- implementation plan;
- approval binding model;
- promotion state machine;
- source and destination zone contract;
- stale artifact, hash mismatch, replay, path escape, overwrite, and conflict negative transcripts;
- external/source review.

Current permitted state:

- current packets may record only `promotion_status: not_promoted`;
- future states such as `promotion_requested`, `promotion_approved`, and `promotion_completed`
  remain design-only until separately approved.

Blocked:

- direct trusted-host writes;
- overwrite/delete/move behavior;
- broad archive extraction;
- automatic promotion;
- promotion without exact artifact hash binding and approval evidence.

## Phase E5: Production IAM And Storage Architecture

Goal: decide the production-grade identity and persistence model before multi-user or remote use.

Required design decisions:

- identity provider and local principal mapping;
- workspace/team/tenant model;
- admin/session model;
- durable storage model;
- audit retention and export model;
- migration and backup/restore strategy;
- incident response and break-glass model.

Blocked until this phase is implemented and reviewed:

- production IAM;
- organization-grade role mapping;
- runtime Postgres;
- multi-user remote deployment;
- hosted MCP;
- managed control plane.

## Phase E6: Evidence Export And SIEM Adapter Lane

Goal: provide SIEM-shaped exports without claiming SIEM custody.

Required before implementation:

- stable event schema;
- redaction and sensitive-field policy;
- export signing story;
- delivery and retry model;
- backpressure/resource limits;
- field-level compatibility tests;
- external/source review.

Blocked:

- hosted telemetry by default;
- custody-grade audit claims;
- stronger audit guarantee claims;
- compliance automation claims;
- exporting prompts, file contents, diffs, response bodies, secrets, dependency names, package
  scripts, raw sensitive paths, or raw sandbox internals.

## Phase E7: Compliance Mapping Support

Goal: help operators map mediated actions to controls without claiming automatic compliance.

Allowed design scope:

- control mapping templates;
- evidence reconstruction guides;
- policy decision and approval evidence mapping;
- operator checklists;
- reviewer packets.

Blocked:

- claims of HIPAA, GLBA, SOX, GDPR, or other regulatory compliance;
- legal conclusions;
- automated certification;
- production security-product positioning.

## Stop Conditions

Stop enterprise-readiness work and reassess if:

- any critical/high trust-boundary finding opens;
- a future sprint requires shell, Docker socket, Kubernetes, browser automation, arbitrary HTTP, or
  broad filesystem powers;
- Mission Control, sandbox, identity, storage, SIEM, or compliance language starts implying current
  production readiness;
- a gate requires hiding or closing external-pending rows without review evidence;
- operator convenience conflicts with approval binding, audit evidence, redaction, or workspace
  confinement.

## Current Next Best Action

The Mission Control display proposal, handoff schema, negative fixtures, and focused display review
packet now exist on the Ithildin side. The sandbox/VM worker boundary charter, profile contract,
preflight contract, proof-of-concept review packet, static profile fixture contract, static preflight
CLI fixture runner, source-review packet, and internal source-review pass also now exist.
The current enterprise-path action is external/source review disposition of the static preflight
lane, followed by a separate post-RC decision before any live VM/container inspection, local-model
invocation, Mission Control runtime importer, sandbox orchestration, or trusted-host promotion work.
The current lane statuses are tracked in
[post-rc-decision-register.md](post-rc-decision-register.md), which keeps Mission Control display
planning separate from no-go runtime lanes.

Current status anchors:

- static preflight CLI fixture runner exists;
- static preflight lane remains local-preview fixture evidence only;
- external/source review disposition is still required before any live sandbox/VM lane.
- post-RC decision register validation is required before any frozen lane moves.

The sandbox/VM worker proof-of-concept boundary packet remains the boundary handoff lineage; it
prepared review of profile/preflight planning without enabling runtime sandbox control.

Use
[sandbox-vm-worker-boundary-charter.md](sandbox-vm-worker-boundary-charter.md) and validate it with
`make sandbox-vm-worker-boundary-charter-check`. The charter keeps Mission Control as the
evidence viewer, Ithildin as the governed mediation/evidence gateway, and the sandbox/VM layer as
operator-managed infrastructure.

Use [sandbox-vm-profile-contract.md](sandbox-vm-profile-contract.md) and validate it with
`make sandbox-vm-profile-contract-check`. The profile contract defines the future operator-supplied
sandbox metadata shape, forbidden fields, validation decisions, and `promotion_status:
not_promoted` posture before any live profile loader, local-model invocation, VM/container
lifecycle, or Mission Control importer is implemented.

Use [sandbox-vm-preflight-contract.md](sandbox-vm-preflight-contract.md) and validate it with
`make sandbox-vm-preflight-contract-check`. The preflight contract defines the future platform
matrix, mount/root posture, network posture, artifact ingress/egress posture, warning chips, and
failure/cleanup transcript requirements before any live sandbox preflight, local model action, or
Mission Control importer is implemented.

Generate the sandbox/VM proof-of-concept review packet with `make sandbox-vm-poc-review-packet`.
The packet bundles the boundary, profile, preflight, Mission Control handoff, Hello World observed
sandbox artifact evidence, artifact-write source-review handoff, promotion evidence contract,
command evidence, and artifact hashes. This is the review handoff for deciding whether a later
static operator-managed sandbox profile fixture and preflight runner may be planned.

The follow-on implementation-planning packet is
[sandbox-vm-static-profile-preflight-plan.md](sandbox-vm-static-profile-preflight-plan.md) and is
validated with `make sandbox-vm-static-profile-preflight-plan-check`. It defines the future static
profile fixture, read-only preflight runner, negative transcripts, output contract, and source
review requirements while keeping live VM control, Mission Control runtime behavior, local model
invocation, sandbox orchestration, and trusted-host promotion blocked.

The fixture contract is
[sandbox-vm-static-profile-fixture-contract.md](sandbox-vm-static-profile-fixture-contract.md) and
is validated with `make sandbox-vm-static-profile-fixture-contract-check`. It commits a
non-production static profile example with coarse labels, required warnings, and false authority
flags only. It does not add a runtime profile loader, preflight runner, VM/container lifecycle
control, Mission Control execution, local model invocation, trusted-host promotion, or network
expansion.

The negative fixture plan is
[sandbox-vm-static-profile-negative-fixtures.md](sandbox-vm-static-profile-negative-fixtures.md) and
is validated with `make sandbox-vm-static-profile-negative-fixtures-check`. It mutates the static
profile example in memory and requires unsupported schemas, raw path-shaped labels, network
overclaims, promotion claims, missing warnings, and authority-flag overclaims to fail closed with
safe reason labels only.

The implementation decision is
[sandbox-vm-static-preflight-implementation-decision.md](sandbox-vm-static-preflight-implementation-decision.md)
and is validated with `make sandbox-vm-static-preflight-implementation-gate`. It approves only the
CLI-only fixture preflight runner that reads static profile metadata and emits safe labels; it does
not approve API/MCP behavior, sandbox orchestration, local model invocation, Mission Control runtime
behavior, trusted-host promotion, or network expansion.

The source-review handoff is
[sandbox-vm-static-preflight-source-review.md](sandbox-vm-static-preflight-source-review.md) and is
generated with `make sandbox-vm-static-preflight-source-review-packet`. It packages the CLI-only
fixture preflight runner, static profile plan, fixture contract, negative fixtures, command
evidence, POC packet pointer, and artifact hashes so a reviewer can inspect the static preflight
lane. It does not approve live sandbox orchestration, local model invocation, Mission Control
runtime behavior, trusted-host promotion, or any new governed tool power.

The internal source-review pass is
[v3-sandbox-vm-static-preflight-internal-review.md](v3-sandbox-vm-static-preflight-internal-review.md).
It records the CLI-only fixture preflight runner as locally reviewed after tightening raw
path-shaped label suppression, while leaving external/source disposition, live VM inspection,
Mission Control runtime behavior, local model invocation, and sandbox orchestration blocked.

Until that external/source disposition is recorded, the static preflight lane remains local-preview
fixture evidence only. It does not approve real VM/container lifecycle control, Mission Control
execution, local model invocation, network expansion, trusted-host promotion, public/security-product
positioning, or enterprise deployment claims.
