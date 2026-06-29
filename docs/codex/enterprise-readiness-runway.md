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
- Mission Control repository implementation ticket;
- Mission Control integration readiness packet;
- Mission Control display external-review launch bundle
  (`mission-control-display-external-review-bundle.md`);
- Mission Control display decision-record skeleton
  (`mission-control-display-decision-record-skeleton.md`);
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

Current readiness evidence:

- the sandbox/control-plane readiness map in
  [enterprise-sandbox-control-plane-readiness.md](enterprise-sandbox-control-plane-readiness.md),
  validated with `make enterprise-sandbox-control-plane-readiness-check`;
- the live POC decision intake in
  [sandbox-vm-live-poc-decision-intake.md](sandbox-vm-live-poc-decision-intake.md);
- the live POC evidence contract in
  [sandbox-vm-live-poc-evidence-contract.md](sandbox-vm-live-poc-evidence-contract.md);
- the live POC preconditions map in
  [sandbox-vm-live-poc-preconditions-map.md](sandbox-vm-live-poc-preconditions-map.md);
- the live POC prerequisite disposition dry run in
  [sandbox-vm-live-poc-prerequisite-disposition-dry-run.md](sandbox-vm-live-poc-prerequisite-disposition-dry-run.md),
  validated with `make sandbox-vm-live-poc-prerequisite-disposition-dry-run`;
- the blocked live POC decision packet in
  [sandbox-vm-live-poc-decision-packet.md](sandbox-vm-live-poc-decision-packet.md), generated with
  `make sandbox-vm-live-poc-decision-packet`;
- the blocked live POC external-review launch bundle in
  [sandbox-vm-live-poc-external-review-bundle.md](sandbox-vm-live-poc-external-review-bundle.md),
  generated with `make sandbox-vm-live-poc-external-review-bundle`;
- the live POC response kit in
  [sandbox-vm-live-poc-response-kit.md](sandbox-vm-live-poc-response-kit.md), generated with
  `make sandbox-vm-live-poc-response-kit`;
- the blocked live POC decision-record skeleton in
  [sandbox-vm-live-poc-decision-record-skeleton.md](sandbox-vm-live-poc-decision-record-skeleton.md),
  validated with `make sandbox-vm-live-poc-decision-record-skeleton-check`;
- the live POC external response intake template in
  [sandbox-vm-live-poc-external-response-intake.md](sandbox-vm-live-poc-external-response-intake.md),
  validated with `make sandbox-vm-live-poc-external-response-intake-check`.

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
- implementation-plan skeleton and later exact implementation plan;
- approval binding model;
- promotion state machine;
- source and destination zone contract;
- stale artifact, hash mismatch, replay, path escape, overwrite, and conflict negative transcripts;
- external/source review.

The decision-intake checklist for this lane is
[trusted-host-promotion-decision-intake.md](trusted-host-promotion-decision-intake.md) and is
validated with `make trusted-host-promotion-decision-intake-check`. It records the allowed
design-only outcomes and the evidence required before any promotion implementation decision.
The design-only state machine for the lane is
[trusted-host-promotion-state-machine.md](trusted-host-promotion-state-machine.md) and is validated
with `make trusted-host-promotion-state-machine-check`.
The design-only negative fixture contract is
[trusted-host-promotion-negative-fixtures.md](trusted-host-promotion-negative-fixtures.md) and is
validated with `make trusted-host-promotion-negative-fixtures-check`.
The design-only zone contract is
[trusted-host-promotion-zone-contract.md](trusted-host-promotion-zone-contract.md) and is validated
with `make trusted-host-promotion-zone-contract-check`.
The design-only implementation-plan skeleton is
[trusted-host-promotion-implementation-plan.md](trusted-host-promotion-implementation-plan.md) and is
validated with `make trusted-host-promotion-implementation-plan-check`.
The focused design/source-review handoff is
[trusted-host-promotion-source-review.md](trusted-host-promotion-source-review.md) and is generated
with `make trusted-host-promotion-source-review-packet`; it packages the promotion evidence
contracts for reviewer disposition while keeping trusted-host promotion blocked.
The external disposition packet is
[trusted-host-promotion-disposition-packet.md](trusted-host-promotion-disposition-packet.md) and is
generated with `make trusted-host-promotion-disposition-packet`; it packages the source-review
pointer, disposition question set, command evidence, and artifact hashes for reviewer handoff
without approving trusted-host promotion, direct host writes, or runtime implementation planning.
The external-review launch bundle is
[trusted-host-promotion-external-review-bundle.md](trusted-host-promotion-external-review-bundle.md)
and is generated with `make trusted-host-promotion-external-review-bundle`; it consolidates the
source packet, disposition packet, promotion contracts, negative fixtures, response intake, closure
gate, response dry run, queue status, command evidence, and artifact hashes for reviewer handoff
without closing `ERG-005` or approving host promotion.
The trusted-host promotion response kit is
[trusted-host-promotion-response-kit.md](trusted-host-promotion-response-kit.md) and is generated
with `make trusted-host-promotion-response-kit`; it packages response-intake guidance,
normalized-response examples, closure commands, queue status, command evidence, and artifact hashes
for real reviewer feedback without closing `ERG-005`, approving implementation planning, or
approving trusted-host promotion.
The external response intake template is
[trusted-host-promotion-external-response-intake.md](trusted-host-promotion-external-response-intake.md)
and is validated with `make trusted-host-promotion-external-response-intake-check`; it defines the
`EXT-TRUSTED-HOST-###` finding namespace and `trusted-host-promotion` normalizer command for
recording reviewer responses without mutating findings, closing `ERG-005`, or approving runtime
host promotion.
The trusted-host promotion disposition closure gate is in
[trusted-host-promotion-disposition-closure-gate.md](trusted-host-promotion-disposition-closure-gate.md)
and is validated with `make trusted-host-promotion-disposition-closure-check`; it keeps `ERG-005`
blocked unless normalized source-level response evidence supports design-only continuation and has
no critical/high findings.
The trusted-host promotion response dry run is in
[trusted-host-promotion-response-dry-run.md](trusted-host-promotion-response-dry-run.md) and is
validated with `make trusted-host-promotion-response-dry-run`; it exercises favorable and
unfavorable temporary normalized-response fixtures while restoring the ignored response path and
without closing `ERG-005` or approving implementation planning.
The internal design/source-review pass is
[v3-trusted-host-promotion-internal-review.md](v3-trusted-host-promotion-internal-review.md) and is
validated with `make trusted-host-promotion-internal-review-check`; it records
`continue_design_only` posture and keeps runtime implementation blocked.

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

The design-only architecture packet for this phase is
[production-identity-storage-architecture.md](production-identity-storage-architecture.md) and is
validated with `make production-identity-storage-architecture-check`. It records the future
identity, tenancy, storage, migration, backup/restore, retention, and evidence questions while
keeping production IAM, runtime Postgres, remote admin use, and custody-grade audit claims blocked.
The focused architecture disposition packet is
[production-identity-storage-disposition-packet.md](production-identity-storage-disposition-packet.md)
and is generated with `make production-identity-storage-disposition-packet`. It asks whether
`ERG-006`/`ERG-007` may continue architecture planning while production identity, runtime Postgres,
database migrations, retention enforcement, hosted control plane, custody claims, and
public/security-product positioning remain blocked.
The production identity/storage external-review launch bundle is
[production-identity-storage-external-review-bundle.md](production-identity-storage-external-review-bundle.md)
and is generated with `make production-identity-storage-external-review-bundle`; it consolidates
the architecture/disposition packet, response-intake template, fail-closed closure gate,
response-dry-run evidence, queue status, and command evidence into one reviewer handoff without
closing `ERG-006`/`ERG-007` or approving identity/storage runtime behavior.
The production identity/storage external response intake template is
[production-identity-storage-external-response-intake.md](production-identity-storage-external-response-intake.md)
and is validated with `make production-identity-storage-external-response-intake-check`; it defines
the `EXT-PROD-IAM-STORAGE-###` finding namespace and `production-identity-storage` normalizer
command for recording reviewer responses without mutating findings, closing `ERG-006`/`ERG-007`,
or approving runtime identity/storage behavior.
The fail-closed disposition closure gate is
[production-identity-storage-disposition-closure-gate.md](production-identity-storage-disposition-closure-gate.md)
and is validated with `make production-identity-storage-disposition-closure-check`; it keeps
`ERG-006`/`ERG-007` planning-only unless normalized source-level response evidence supports
continued architecture planning and contains no critical/high findings.
The production identity/storage response dry run is in
[production-identity-storage-response-dry-run.md](production-identity-storage-response-dry-run.md)
and is validated with `make production-identity-storage-response-dry-run`; it exercises favorable
and unfavorable temporary normalized-response fixtures while restoring the ignored response path and
without closing `ERG-006`/`ERG-007` or approving implementation planning.
The production identity/storage response kit is in
[production-identity-storage-response-kit.md](production-identity-storage-response-kit.md) and is
generated with `make production-identity-storage-response-kit`. It packages response-intake
guidance, normalized-response examples, closure commands, command evidence, and artifact hashes for
real reviewer feedback without closing `ERG-006` or `ERG-007`, approving implementation planning,
or approving runtime identity/storage behavior.

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

The design-only adapter architecture packet for this phase is
[siem-export-adapter-architecture.md](siem-export-adapter-architecture.md) and is validated with
`make siem-export-adapter-architecture-check`. It extends the SIEM-shaped evidence design with
delivery-profile, compatibility, retry, backpressure, signing, diagnostics, and review requirements
while keeping SIEM adapter runtime behavior, hosted telemetry, remote delivery, and custody-grade
audit claims blocked.
The focused adapter disposition packet is
[siem-export-adapter-disposition-packet.md](siem-export-adapter-disposition-packet.md) and is
generated with `make siem-export-adapter-disposition-packet`. It asks whether `ERG-008` may
continue architecture planning while adapter runtime behavior, hosted telemetry, remote delivery,
custody claims, external notarization, immutable storage, and compliance automation remain blocked.
The consolidated SIEM export adapter external-review launch bundle is
[siem-export-adapter-external-review-bundle.md](siem-export-adapter-external-review-bundle.md) and
is generated with `make siem-export-adapter-external-review-bundle`. It packages the disposition
packet, architecture evidence, response intake, closure gate, response dry run, queue status, and
command evidence for reviewer handoff while keeping SIEM adapter runtime behavior blocked.
The SIEM export adapter external response intake template is
[siem-export-adapter-external-response-intake.md](siem-export-adapter-external-response-intake.md)
and is validated with `make siem-export-adapter-external-response-intake-check`. It defines the
`EXT-SIEM-ADAPTER-###` finding namespace and `siem-export-adapter` normalizer command for recording
reviewer responses without mutating findings, closing `ERG-008`, or approving adapter runtime
behavior.
The fail-closed disposition closure gate is
[siem-export-adapter-disposition-closure-gate.md](siem-export-adapter-disposition-closure-gate.md)
and is validated with `make siem-export-adapter-disposition-closure-check`; it keeps `ERG-008`
planning-only unless normalized source-level response evidence supports continued architecture
planning and contains no critical/high findings.
The SIEM export adapter response dry run is in
[siem-export-adapter-response-dry-run.md](siem-export-adapter-response-dry-run.md) and is validated
with `make siem-export-adapter-response-dry-run`; it exercises favorable and unfavorable temporary
normalized-response fixtures while restoring the ignored response path and without closing
`ERG-008` or approving implementation planning.
The SIEM export adapter response kit is in
[siem-export-adapter-response-kit.md](siem-export-adapter-response-kit.md) and is generated with
`make siem-export-adapter-response-kit`. It packages response-intake guidance,
normalized-response examples, closure commands, command evidence, and artifact hashes for real
reviewer feedback without closing `ERG-008`, approving implementation planning, or approving
runtime SIEM adapter behavior.

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
- the design-only architecture packet in `compliance-mapping-architecture.md`;
- the focused disposition packet in `compliance-mapping-disposition-packet.md`;
- the external response intake template in `compliance-mapping-external-response-intake.md`.

Blocked:

- claims of HIPAA, GLBA, SOX, GDPR, or other regulatory compliance;
- legal conclusions;
- automated certification;
- production security-product positioning.

Current evidence:

- `compliance-mapping-architecture.md` defines future mapping template requirements, legal-review
  boundary, operator responsibility language, evidence-field boundaries, and required review before
  any compliance mapping implementation or regulated-industry artifact is shipped.
- `make compliance-mapping-architecture-check` validates the planning-only posture and confirms
  compliance mapping runtime behavior, legal advice, automated certification, custody-grade audit
  claims, and new power classes remain blocked.
- `make compliance-mapping-disposition-packet` generates the focused handoff asking whether
  `ERG-009` may continue architecture planning while runtime compliance mapping, legal advice,
  automated certification, regulated-industry compliance claims, custody claims, and
  public/security-product positioning remain blocked.
- `compliance-mapping-external-review-bundle.md` consolidates the disposition packet,
  architecture contracts, response-intake and closure gates, dry-run evidence, queue status,
  command evidence, and artifact hashes for the ERG-009 external-review launch handoff without
  closing the lane or approving runtime compliance mapping.
- `compliance-mapping-external-response-intake.md` defines the `EXT-COMPLIANCE-MAPPING-###`
  finding namespace and `compliance-mapping` normalizer command for recording reviewer responses
  without mutating findings, closing `ERG-009`, or approving runtime compliance mapping,
  compliance automation, legal advice, automated certification, regulated-industry compliance
  claims, or public/security-product positioning.
- `compliance-mapping-disposition-closure-gate.md` validates normalized source-level response
  evidence before any later triage update may move `ERG-009` toward an architecture decision record;
  absent or unfavorable evidence keeps `ERG-009` planning-only.
- `compliance-mapping-response-dry-run.md` is validated with
  `make compliance-mapping-response-dry-run`; it exercises favorable and unfavorable temporary
  normalized-response fixtures, restores the ignored response path, and does not record external
  review, mutate findings, close `ERG-009`, or approve implementation/runtime compliance mapping.
- `compliance-mapping-response-kit.md` is generated with
  `make compliance-mapping-response-kit`; it packages response-intake guidance,
  normalized-response examples, closure commands, command evidence, and artifact hashes for real
  reviewer feedback while keeping `ERG-009` planning-only and keeping implementation planning,
  runtime compliance mapping, compliance automation, legal advice, automated certification,
  regulated-industry compliance claims, and custody-grade audit claims blocked.

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
packet now exist on the Ithildin side. The
[mission-control-integration-implementation-ticket.md](mission-control-integration-implementation-ticket.md)
also now exists as a concrete Mission Control repository ticket for the display-only importer. The
Mission Control display post-RC decision intake now also exists as planning-only evidence. The
Mission Control display importer implementation plan now also exists as planning-only evidence. The
Mission Control integration readiness packet now also exists as a consolidated handoff packet for
the display-only Mission Control-side file/import task. The fail-closed disposition closure gate in
[mission-control-display-disposition-closure-gate.md](mission-control-display-disposition-closure-gate.md)
keeps `ERG-002` planning-only unless normalized source-level response evidence explicitly supports
design-only continuation and contains no critical/high findings. The response dry run in
[mission-control-display-response-dry-run.md](mission-control-display-response-dry-run.md)
temporarily verifies favorable and unfavorable normalized-response fixtures while restoring the
ignored response path and not closing `ERG-002`. The response kit in
[mission-control-display-response-kit.md](mission-control-display-response-kit.md) packages the
response-intake guide, normalized-response examples, closure commands, boundary status, command
evidence, and artifact hashes for the real response path without recording review, closing
`ERG-002`, or approving runtime importer behavior. The
sandbox/VM worker boundary charter, profile contract, preflight contract, proof-of-concept review
packet, static profile fixture contract, static preflight CLI fixture runner, source-review packet,
and internal source-review pass also now exist.
The current enterprise-path action is external/source review disposition of the static preflight
lane, followed by a separate post-RC decision before any live VM/container inspection, local-model
invocation, Mission Control runtime importer, sandbox orchestration, or trusted-host promotion work.
The current lane statuses are tracked in
[post-rc-decision-register.md](post-rc-decision-register.md), which keeps Mission Control display
planning separate from no-go runtime lanes.
The enterprise gap and claim blockers are tracked in
[enterprise-readiness-gap-matrix.md](enterprise-readiness-gap-matrix.md), validated with
`make enterprise-readiness-gap-matrix-check`.
The enterprise external-review queue is tracked in
[enterprise-external-review-queue.md](enterprise-external-review-queue.md), validated with
`make enterprise-external-review-queue-check`; it names the current packet/intake path for each
post-RC enterprise lane and recommends `ERG-003` static sandbox/VM preflight disposition as the next
review before live sandbox/VM worker planning. The `ERG-003` fail-closed closure gate in
`sandbox-vm-static-preflight-disposition-closure-gate.md` keeps the lane open until normalized
source-level response evidence is present.
Public/security-product positioning is tracked as an explicit no-go lane in
[public-security-product-positioning-decision-intake.md](public-security-product-positioning-decision-intake.md),
validated with `make public-security-product-positioning-decision-intake-check`; it allows
claim-review and evidence-mapping preparation only while broad public/security-product,
production/security/compliance positioning, and other claim expansion remain blocked. The
consolidated public positioning external-review bundle is
[public-positioning-external-review-bundle.md](public-positioning-external-review-bundle.md),
generated with `make public-positioning-external-review-bundle`; it packages the intake, closure
gates, current no-go decision evidence, accepted-risk context, enterprise queue status, command
evidence, and artifact hashes without closing `ERG-010` or approving public/security-product
positioning. The response-intake kit is
[public-security-product-positioning-response-kit.md](public-security-product-positioning-response-kit.md),
generated with `make public-security-product-positioning-response-kit`; it packages normalized
response examples, closure triage commands, queue and boundary status, and command evidence for
real reviewer feedback without closing `ERG-010` or approving public/security-product positioning.
The
fail-closed public/security-product positioning decision closure gate is in
[public-security-product-positioning-decision-closure-gate.md](public-security-product-positioning-decision-closure-gate.md)
and is checked with `make public-security-product-positioning-decision-closure-check`; it keeps
`ERG-010` blocked unless normalized source-level or packet-and-source response evidence supports a
future claim-specific decision record and contains no critical/high findings. Even favorable closure
evidence does not approve public/security-product positioning, production/security/compliance
positioning, runtime behavior, or new tool powers.
production/security/compliance, sandbox, EDR/MDM, SIEM custody, compliance automation, hosted trust,
and enterprise-grade identity claims remain blocked.

Current status anchors:

- static preflight CLI fixture runner exists;
- enterprise readiness gap status is matrixed before implementation claims;
- Mission Control display importer planning remains file/import display only;
- Mission Control display implementation decisions must pass
  `mission-control-display-decision-intake.md`;
- Mission Control display disposition must pass
  `mission-control-display-disposition-packet.md`;
- Mission Control display external response intake must pass
  `mission-control-display-external-response-intake.md`;
- Mission Control display disposition closure must pass
  `mission-control-display-disposition-closure-gate.md`;
- Mission Control integration readiness must pass
  `mission-control-integration-readiness-packet.md`;
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

The external disposition packet is
[sandbox-vm-static-preflight-disposition-packet.md](sandbox-vm-static-preflight-disposition-packet.md)
and is generated with `make sandbox-vm-static-preflight-disposition-packet`. It packages the
source-review packet pointer, `ERG-003` disposition question set, response-intake guidance, command
evidence, and artifact hashes for reviewer handoff. It does not close `ERG-003` or approve live
sandbox/VM runtime work.

The static preflight external-review launch bundle is
[sandbox-vm-static-preflight-external-review-bundle.md](sandbox-vm-static-preflight-external-review-bundle.md)
and is generated with `make sandbox-vm-static-preflight-external-review-bundle`. It consolidates the
source-review packet, disposition packet, response/closure/triage path, reproduction map, queue
status, and command evidence into one 10-file handoff for the recommended `ERG-003` external/source
review without closing `ERG-003` or approving live sandbox/VM runtime work.

The static preflight response kit is
[sandbox-vm-static-preflight-response-kit.md](sandbox-vm-static-preflight-response-kit.md) and is
generated with `make sandbox-vm-static-preflight-response-kit`. It packages the response-intake
guide, normalized-response examples, closure and triage commands, queue/precondition status,
command evidence, and artifact hashes for converting real reviewer feedback into normalized
evidence without closing `ERG-003`, unblocking `ERG-004`, or approving live sandbox/VM runtime work.

The external disposition plan is
[sandbox-vm-static-preflight-disposition-plan.md](sandbox-vm-static-preflight-disposition-plan.md)
and is validated with `make sandbox-vm-static-preflight-disposition-plan-check`. It defines the
questions and allowed outcomes for recording an external/source-review response to `ERG-003` without
turning static fixture evidence into live VM/container control, sandbox orchestration, local model
invocation, Mission Control runtime behavior, or trusted-host promotion.

The fail-closed disposition closure gate is
[sandbox-vm-static-preflight-disposition-closure-gate.md](sandbox-vm-static-preflight-disposition-closure-gate.md)
and is validated with `make sandbox-vm-static-preflight-disposition-closure-check`. It reports
`closure_ready: false` until normalized source-level response evidence exists, and it still does not
close `ERG-003` or approve live sandbox/VM runtime work.

The external response intake template is
[sandbox-vm-static-preflight-external-response-intake.md](sandbox-vm-static-preflight-external-response-intake.md)
and is validated with `make sandbox-vm-static-preflight-external-response-intake-check`. It defines
the `EXT-SVP-###` finding namespace and normalizer command for recording a reviewer response without
mutating findings, closing `ERG-003`, or approving live sandbox/VM runtime work.
The static preflight response dry run is
[sandbox-vm-static-preflight-response-dry-run.md](sandbox-vm-static-preflight-response-dry-run.md)
and is validated with `make sandbox-vm-static-preflight-response-dry-run`. It exercises temporary
favorable and unfavorable normalized-response fixtures against the fail-closed closure gate, then
restores the ignored response path without recording external review.
The static preflight triage-update checklist is
[sandbox-vm-static-preflight-triage-update.md](sandbox-vm-static-preflight-triage-update.md)
and is validated with `make sandbox-vm-static-preflight-triage-update-check`. It defines the safe
committed update path after real favorable `ERG-003` evidence while keeping `ERG-004`, live
sandbox/VM runtime work, local model invocation, Mission Control runtime behavior, and trusted-host
promotion blocked.
The reviewer reproduction map is
[sandbox-vm-static-preflight-reviewer-reproduction-map.md](sandbox-vm-static-preflight-reviewer-reproduction-map.md)
and is validated with `make sandbox-vm-static-preflight-reviewer-reproduction-map-check`. It gives
reviewers the exact static preflight command sequence and evidence pointers while keeping
`ERG-003` external-review-required and live sandbox/VM runtime work blocked.

The live sandbox/VM POC decision intake is
[sandbox-vm-live-poc-decision-intake.md](sandbox-vm-live-poc-decision-intake.md) and is validated
with `make sandbox-vm-live-poc-decision-intake-check`. It defines the evidence required before a
future post-RC decision record may even consider moving `ERG-004` out of `blocked`; it does not
approve live VM/container inspection, Mission Control runtime behavior, local model invocation,
sandbox orchestration, trusted-host promotion, or public/security-product positioning.

The live sandbox/VM POC evidence contract is
[sandbox-vm-live-poc-evidence-contract.md](sandbox-vm-live-poc-evidence-contract.md) and is
validated with `make sandbox-vm-live-poc-evidence-contract-check`. It defines the future
cross-source evidence bundle that would have to correlate operator intent, Ithildin run/audit
evidence, operator-managed sandbox evidence, local model/client evidence, and optional Mission
Control display evidence without approving live VM/container inspection, Mission Control runtime
behavior, local model invocation, sandbox orchestration, trusted-host promotion, SIEM delivery, or
public/security-product positioning.

The live sandbox/VM POC preconditions map is
[sandbox-vm-live-poc-preconditions-map.md](sandbox-vm-live-poc-preconditions-map.md) and is
validated with `make sandbox-vm-live-poc-preconditions-map-check`. It consolidates the required
favorable `ERG-003` disposition, post-RC decision-record path, operator-managed VM/container
assumptions, cleanup/failure transcript requirements, role separation, and cross-source evidence
before any later implementation-planning decision. It keeps `ERG-004` blocked and does not approve
live VM/container inspection, Mission Control runtime behavior, local model invocation, sandbox
orchestration, trusted-host promotion, network expansion, or public/security-product positioning.

The live sandbox/VM POC preconditions ready check is
[sandbox-vm-live-poc-preconditions-ready-check.md](sandbox-vm-live-poc-preconditions-ready-check.md)
and is validated with `make sandbox-vm-live-poc-preconditions-ready-check`. It aggregates the
blocked-lane `ERG-004` checks, confirms the decision/intake/packet/response-kit/closure wiring is
valid, and still reports `ready_for_implementation_planning: false` until favorable `ERG-003`
disposition and normalized `ERG-004` response evidence exist.

The live sandbox/VM POC post-`ERG-003` handoff is
[sandbox-vm-live-poc-post-erg003-handoff.md](sandbox-vm-live-poc-post-erg003-handoff.md) and is
validated with `make sandbox-vm-live-poc-post-erg003-handoff-check`. It explains the still-blocked
sequence to run after a favorable static-preflight disposition is recorded, while keeping `ERG-004`,
live VM/container inspection, local model invocation, Mission Control runtime behavior, sandbox
orchestration, trusted-host promotion, network expansion, and runtime implementation blocked until a
separate committed decision record exists.

The live sandbox/VM POC external response intake template is
[sandbox-vm-live-poc-external-response-intake.md](sandbox-vm-live-poc-external-response-intake.md)
and is validated with `make sandbox-vm-live-poc-external-response-intake-check`. It defines the
`EXT-LIVE-POC-###` finding namespace and `sandbox-vm-live-poc` normalizer command for recording a
reviewer response without mutating findings, closing `ERG-004`, approving implementation planning,
or approving live sandbox/VM runtime work.

The live sandbox/VM POC decision closure gate is
[sandbox-vm-live-poc-decision-closure-gate.md](sandbox-vm-live-poc-decision-closure-gate.md) and is
validated with `make sandbox-vm-live-poc-decision-closure-check`. It reports
`closure_ready: false` until normalized source-level response evidence exists, favorable `ERG-003`
disposition is recorded, and the reviewer outcome can support only a later committed decision
record. It keeps live VM/container inspection, local model invocation, sandbox orchestration,
Mission Control runtime behavior, trusted-host promotion, and runtime implementation blocked.

The live sandbox/VM POC decision-record skeleton is
[sandbox-vm-live-poc-decision-record-skeleton.md](sandbox-vm-live-poc-decision-record-skeleton.md)
and is validated with `make sandbox-vm-live-poc-decision-record-skeleton-check`. It defines the only
implementation-planning-only decision shape a favorable normalized `ERG-004` response may support
while keeping runtime implementation, live VM/container inspection, sandbox orchestration, Mission
Control runtime behavior, local model invocation, trusted-host promotion, and new tool powers
blocked.

The live sandbox/VM POC response kit is
[sandbox-vm-live-poc-response-kit.md](sandbox-vm-live-poc-response-kit.md) and is generated with
`make sandbox-vm-live-poc-response-kit`. It packages response-intake guidance,
normalized-response examples, closure and decision-record commands, queue/precondition status,
command evidence, and artifact hashes for real `ERG-004` decision-packet feedback without closing
`ERG-004`, approving implementation planning, or approving live sandbox/VM runtime work.

The live sandbox/VM POC external-review launch bundle is
[sandbox-vm-live-poc-external-review-bundle.md](sandbox-vm-live-poc-external-review-bundle.md) and
is generated with `make sandbox-vm-live-poc-external-review-bundle`. It consolidates the blocked
`ERG-004` decision packet, contracts, preconditions, response/closure dry runs, queue status,
command evidence, and artifact hashes without closing `ERG-004`, approving implementation planning,
or approving live sandbox/VM runtime work.

The live sandbox/VM POC response dry run is
[sandbox-vm-live-poc-response-dry-run.md](sandbox-vm-live-poc-response-dry-run.md) and is validated
with `make sandbox-vm-live-poc-response-dry-run`. It exercises favorable and unfavorable temporary
normalized-response fixtures, including a missing favorable `ERG-003` disposition, then restores
the ignored response path without recording external review or approving live sandbox/VM runtime
work.

The internal source-review pass is
[v3-sandbox-vm-static-preflight-internal-review.md](v3-sandbox-vm-static-preflight-internal-review.md).
It records the CLI-only fixture preflight runner as locally reviewed after tightening raw
path-shaped label suppression, while leaving external/source disposition, live VM inspection,
Mission Control runtime behavior, local model invocation, and sandbox orchestration blocked.

Until that external/source disposition is recorded, the static preflight lane remains local-preview
fixture evidence only. It does not approve real VM/container lifecycle control, Mission Control
execution, local model invocation, network expansion, trusted-host promotion, public/security-product
positioning, or enterprise deployment claims.

The future committed disposition shape is defined in
`sandbox-vm-static-preflight-disposition-record-skeleton.md`. That skeleton is only for a favorable
source-level `ERG-003` static preflight disposition and keeps `ERG-004`, live POC planning, runtime
implementation, Mission Control runtime behavior, local model invocation, trusted-host promotion,
and new governed tool powers blocked.
