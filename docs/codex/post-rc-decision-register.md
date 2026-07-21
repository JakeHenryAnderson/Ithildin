# Post-RC Decision Register

Status: current register for post-v1.0 RC boundary decisions.

This register records the active post-RC lane decisions that govern the next enterprise-readiness
steps. It is a status source of truth, not an approval to add runtime behavior. Any entry that moves
from planning to implementation still requires a dedicated decision record, implementation plan,
source-review or external-review evidence, tests, gates, packet artifacts, and an explicit go/no-go
outcome.

The broader enterprise gap map is
[enterprise-readiness-gap-matrix.md](enterprise-readiness-gap-matrix.md). This register records the
current lane decision status; the matrix records the claim/capability each unresolved gap blocks.
The enterprise external-review queue is
[enterprise-external-review-queue.md](enterprise-external-review-queue.md). It records the current
review order, packet pointers, response-intake paths, and runtime-disabled posture for post-RC
enterprise lanes.

Current governed tool count: `24`.

Current selected capability: `not selected`.

## Register Rules

- `approved_for_planning` allows documentation, schema sketches, static fixtures, review packets,
  and source-review preparation only.
- `no_go` blocks runtime behavior and may allow design cleanup or packet preparation only when the
  allowed scope says so.
- No entry in this register approves manifests, executors, policy/rule changes, API/MCP behavior,
  approval/audit behavior, UI runtime behavior, Mission Control runtime behavior, sandbox
  orchestration, local model invocation, trusted-host promotion, SIEM adapters, production identity,
  runtime Postgres, hosted telemetry, remote MCP, plugin SDK behavior, compliance automation,
  public/security-product positioning, broad filesystem writes, or arbitrary network expansion.
- A lane must stay blocked if its allowed scope, forbidden scope, required evidence, accepted-risk
  impact, and operator warning language are incomplete.

## Current Decisions

| Decision ID | Lane | Status | Allowed next action | Runtime allowed | Required next evidence |
| --- | --- | --- | --- | --- | --- |
| `PRD-MC-DISPLAY-001` | Mission Control display importer continuation | `approved_for_planning` | Prepare display-only schema, packet, static fixtures, and source-review handoff; include `mission-control-integration-readiness-packet.md` and `mission-control-integration-implementation-ticket.md` before Mission Control-side implementation | `false` | Mission Control-side review packet, `mission-control-integration-readiness-packet.md`, `mission-control-integration-implementation-ticket.md`, and implementation plan before runtime importer work |
| `PRD-SANDBOX-PREFLIGHT-001` | Live sandbox/VM preflight | `no_go` | Continue static fixture evidence and source-review disposition only | `false` | Separate live-preflight decision record, implementation plan, and external/source review |
| `PRD-SANDBOX-LIVE-POC-001` | Live sandbox/VM worker proof of concept | `approved_for_runtime_proposal_review_only` | Prepare VM-first operator-managed planning docs, runtime proposal, descriptor/correlation contract, cleanup/failure transcript plans, and source-review handoff; container profiles remain deferred | `false` | `sandbox-vm-live-poc-decision-record.md`, `sandbox-vm-live-poc-implementation-plan.md`, `sandbox-vm-live-poc-runtime-proposal.md`, cleanup/failure transcripts, explicit implementation gate, and external/source review before runtime |
| `PRD-CAPABILITY-001` | New governed tool after RC freeze | `no_go` | Candidate selection and design packet only | `false` | Capability proposal, implementation plan, source-review handoff, negative transcripts, and accepted-risk update |
| `PRD-TRUSTED-HOST-001` | Trusted-host promotion lane | `ready_for_limited_runtime_implementation_plan` | A future limited runtime implementation plan may be drafted; runtime implementation remains blocked. Earlier `ready_for_implementation_planning_only` posture allowed Promotion state-machine design, decision-intake, implementation-plan refinement, and evidence contract discussion only. | `false` | Artifact hash-binding model, approval model, state-machine evidence, negative transcripts, zone contract, implementation-plan contract, decision-intake evidence, `trusted-host-promotion-decision-record.md`, Goal B source-review/runtime-boundary packet, Goal C implementation-gate decision in `trusted-host-promotion-implementation-gate-decision.md`, and external/source review |
| `PRD-SIEM-EXPORT-001` | SIEM-shaped export adapter lane | `no_go` | Stable schema, adapter architecture, compatibility tests, and offline export design only | `false` | The architecture packet in `siem-export-adapter-architecture.md`, the disposition packet in `siem-export-adapter-disposition-packet.md`, the response intake template in `siem-export-adapter-external-response-intake.md`, the fail-closed closure gate in `siem-export-adapter-disposition-closure-gate.md`, delivery model, redaction policy, compatibility tests, signing/verification story, post-RC decision record, and external/source review |
| `PRD-COMPLIANCE-MAPPING-001` | Compliance mapping support lane | `approved_for_planning` | Mapping-template architecture, operator responsibility language, legal-review boundary, and evidence-field planning only | `false` | The architecture packet in `compliance-mapping-architecture.md`, the disposition packet in `compliance-mapping-disposition-packet.md`, the response intake template in `compliance-mapping-external-response-intake.md`, the fail-closed closure gate in `compliance-mapping-disposition-closure-gate.md`, the response dry-run fixture checker in `compliance-mapping-response-dry-run.md`, exact framework scope, template schema, evidence allowlist/denylist, accepted-risk impact review, post-RC decision record, and external/source review before runtime work |
| `PRD-PROD-IAM-STORAGE-001` | Production identity and durable storage architecture | `approved_for_planning` | Maintain the architecture packet, threat model questions, migration/retention/backup planning, and external architecture review preparation | `false` | Post-RC decision record, identity provider design, tenant/workspace model, storage/migration plan, backup/restore plan, failure-mode tests, and external architecture review before runtime work |
| `PRD-PUBLIC-POSITIONING-001` | Public/security-product positioning | `no_go` | Claim-review documentation, warning-packet review, operator support/deployment model planning, evidence mapping, and external review preparation only | `false` | `public-security-product-positioning-decision-intake.md`, `public-positioning-external-review-bundle.md`, `public-security-product-positioning-response-kit.md`, `public-security-product-positioning-decision-closure-gate.md`, resolved claim-dependent external/source review rows, accepted-risk disposition, support/deployment/update/incident-response model, explicit claim wording review, and a later committed go/no-go decision before any broader public/security-product positioning |

## Decision Details

### PRD-MC-DISPLAY-001

- Status: `approved_for_planning`.
- Current allowed scope: display-only import planning for labels, hashes, warnings, links, run IDs,
  approval IDs, local-preview status, and packet versions.
- Current forbidden scope: Mission Control execution authority, policy authority, approval authority,
  audit authority, local-model runner behavior, VM/container management, sandbox orchestration,
  trusted-host promotion, file mutation, runtime importer behavior, and production identity.
- Current implementation posture: runtime behavior remains blocked.
- Current warning language: Mission Control remains an evidence display/import planning surface only.
- Current decision-intake evidence:
  `mission-control-display-decision-intake.md` defines the preconditions, allowed outcomes, negative
  evidence, and forbidden authority claims before any runtime importer decision can be recorded.
- Current response-intake evidence:
  `mission-control-display-external-response-intake.md` defines the `EXT-MC-DISPLAY-###` finding
  namespace, allowed reviewer-response outcomes, and the rule that a favorable response is intake
  evidence only, not runtime importer approval.
- Current disposition closure evidence:
  `mission-control-display-disposition-closure-gate.md` keeps `ERG-002` planning-only unless
  normalized source-level response evidence supports design-only continuation and contains no
  critical/high findings.
- Current response dry-run evidence:
  `mission-control-display-response-dry-run.md` exercises favorable and unfavorable normalized
  response fixtures while restoring ignored local evidence and without closing `ERG-002`.
- Current response-kit evidence:
  `mission-control-display-response-kit.md` packages response-intake guidance,
  normalized-response examples, closure commands, boundary status, command evidence, and artifact
  hashes for the real reviewer-response path without recording review, closing `ERG-002`, or
  approving runtime importer behavior.
- Current decision-record skeleton evidence:
  `mission-control-display-decision-record-skeleton.md` defines the only design-only decision
  record shape a favorable normalized response may support. It can move `ERG-002` only toward
  `ready_for_design_only_decision_record` and does not approve runtime importer behavior or Mission
  Control execution, policy, approval, or audit authority.

### PRD-SANDBOX-PREFLIGHT-001

- Status: `ready_for_limited_runtime_implementation_plan`.
- Current allowed scope: static fixture evidence, source-review disposition, docs, review packets,
  negative fixture planning, reviewer reproduction mapping, and operator warnings.
- Current forbidden scope: live VM/container inspection, SSH, shell, Docker socket access,
  Kubernetes tools, local model invocation, sandbox orchestration, trusted-host promotion, runtime
  preflight runner behavior, production identity, and remote control-plane behavior.
- Current implementation posture: live runtime behavior remains blocked.
- Current warning language: Ithildin does not start, inspect, or manage VMs/containers in this lane.
- Current reproduction-map evidence:
  `sandbox-vm-static-preflight-reviewer-reproduction-map.md` gives reviewers the exact static
  preflight command sequence and evidence pointers without closing `ERG-003` or approving live
  sandbox/VM runtime work.
- Current closure-gate evidence:
  `sandbox-vm-static-preflight-disposition-closure-gate.md` keeps `ERG-003` open until normalized
  source-level response evidence exists and still does not approve live sandbox/VM runtime work.
- Current response-kit evidence:
  `sandbox-vm-static-preflight-response-kit.md` packages response-intake guidance,
  normalized-response examples, closure/triage commands, queue status, command evidence, and
  artifact hashes for real reviewer feedback while keeping `ERG-003` open and `ERG-004` blocked.
- Current triage-update evidence:
  `sandbox-vm-static-preflight-triage-update.md` defines the safe committed update checklist after
  real favorable `ERG-003` evidence while keeping `ERG-004`, live sandbox/VM runtime work, local
  model invocation, Mission Control runtime behavior, and trusted-host promotion blocked.

### PRD-SANDBOX-LIVE-POC-001

- Status: `approved_for_runtime_proposal_review_only`.
- Current allowed scope: decision-intake evidence in
  `sandbox-vm-live-poc-decision-intake.md`, favorable `ERG-003` disposition tracking,
  decision-record drafting, docs, review packets, the readiness map in
  `enterprise-sandbox-control-plane-readiness.md`, the preconditions map in
  `sandbox-vm-live-poc-preconditions-map.md`, the preconditions ready check in
  `sandbox-vm-live-poc-preconditions-ready-check.md`, the post-`ERG-003` handoff in
  `sandbox-vm-live-poc-post-erg003-handoff.md`, the decision packet in
  `sandbox-vm-live-poc-decision-packet.md`, the launch bundle in
  `sandbox-vm-live-poc-external-review-bundle.md`, the response kit in
  `sandbox-vm-live-poc-response-kit.md`, the external response intake template in
  `sandbox-vm-live-poc-external-response-intake.md`, the fail-closed closure gate in
  `sandbox-vm-live-poc-decision-closure-gate.md`, the decision-record skeleton in
  `sandbox-vm-live-poc-decision-record-skeleton.md`, the response dry-run fixture checker in
  `sandbox-vm-live-poc-response-dry-run.md`, the implementation plan in
  `sandbox-vm-live-poc-implementation-plan.md`, the runtime proposal in
  `sandbox-vm-live-poc-runtime-proposal.md`, the runtime-proposal review bundle in
  `sandbox-vm-live-poc-runtime-proposal-review-bundle.md`, and operator warnings.
- Current forbidden scope: live VM/container inspection, local model invocation, Mission Control
  runtime behavior, sandbox orchestration, SSH, shell, Docker socket access, Kubernetes tools,
  browser automation, arbitrary HTTP, broad filesystem writes, trusted-host promotion, runtime
  profile loading, production identity, SIEM adapters, and public/security-product positioning.
- Current implementation posture: live worker runtime behavior remains blocked.
- Current warning language: Ithildin does not run a local model, inspect a live VM/container,
  orchestrate a sandbox, or promote sandbox artifacts in this lane.
- Current decision-record skeleton evidence:
  `sandbox-vm-live-poc-decision-record-skeleton.md` defines the only implementation-planning-only
  decision shape a favorable normalized response may support. It can move `ERG-004` only toward
  `ready_for_implementation_planning_only` and does not approve runtime implementation, live
  VM/container inspection, sandbox orchestration, Mission Control runtime behavior, local model
  invocation, trusted-host promotion, SIEM adapter behavior, or new governed tool powers.
- Current committed decision evidence:
  `sandbox-vm-live-poc-decision-record.md` records the favorable GPT 5.5 Pro packet/source
  disposition and moves `ERG-004` to `ready_for_implementation_planning_only`.
  `sandbox-vm-live-poc-implementation-plan.md` is the VM-first planning packet. Runtime
  implementation, live VM/container inspection, Mission Control runtime behavior, local model
  invocation, sandbox orchestration, trusted-host promotion, SIEM adapter behavior, and new governed
  tool powers remain blocked until a later explicit implementation gate and external/source review.
  `sandbox-vm-live-poc-runtime-proposal.md` is the next runtime-proposal packet; it may be reviewed
  to decide whether a bounded runtime implementation ticket can be drafted for a later gate, but it
  does not approve runtime implementation.
- Historical pre-decision action: Maintain the decision-intake packet and wait for favorable
  `ERG-003` disposition. That condition is now satisfied only for planning; it does not approve
  runtime behavior.
- Historical prerequisite evidence remains in `sandbox-vm-live-poc-prerequisite-disposition-dry-run.md`
  for packet compatibility and to show that favorable `ERG-003` evidence was only a prerequisite,
  not runtime approval.

### PRD-CAPABILITY-001

- Status: `no_go`.
- Current allowed scope: candidate selection, design packet, proposal, risk analysis, source-review
  request, and implementation plan draft.
- Current forbidden scope: manifest addition, executor code, policy/rule semantics, MCP/API
  behavior, approval behavior, audit behavior, UI runtime behavior, runtime storage changes, local
  model invocation, sandbox orchestration, and trusted-host promotion.
- Current implementation posture: no new governed tool is approved by this register.
- Current warning language: post-RC capability work remains design-only until a separate record
  approves implementation.

### PRD-PUBLIC-POSITIONING-001

- Status: `no_go`.
- Current allowed scope: claim-review documentation, warning-packet review, operator support and
  deployment model planning, evidence mapping, wording cleanup, and external/source review
  preparation.
- Current forbidden scope: broader public/security-product positioning, production deployment
  readiness, production/security/compliance claims, sandbox guarantee claims, EDR/MDM claims, SIEM
  custody claims, compliance automation claims, legal conclusions, hosted MCP, remote MCP gateway,
  managed model serving, production identity, runtime Postgres, hosted telemetry, plugin SDK
  behavior, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad writes, and
  stronger claims based only on internal evidence.
- Current implementation posture: public/security-product positioning remains blocked.
- Current warning language: Ithildin may continue local-preview development and limited
  technical-preview sharing with the warning packet, but broad public/security-product,
  production/security/compliance, sandbox, EDR/MDM, SIEM custody, compliance automation, hosted
  trust, and enterprise identity claims remain unavailable.
- Current decision-intake evidence:
  `public-security-product-positioning-decision-intake.md` defines the blocked `ERG-010` lane,
  required preconditions, allowed no-go evidence work, forbidden claims, and validation command
  before any later public/security-product positioning decision can be recorded.
- Current external-review launch evidence:
  `public-positioning-external-review-bundle.md` consolidates the intake, closure gates, current
  no-go decision evidence, accepted-risk context, enterprise queue status, command evidence, and
  artifact hashes without closing `ERG-010` or approving public/security-product positioning.
- Current response-intake evidence:
  `public-security-product-positioning-response-kit.md` packages normalized response examples,
  closure triage commands, queue and boundary status, and command evidence for reviewer feedback
  while preserving the blocked posture for `ERG-010`.

### PRD-TRUSTED-HOST-001

- Status: `no_go`.
- Current allowed scope: design-only discussion of source/destination zones, artifact hashes,
  approval binding, replay denial, conflict handling, and operator warnings.
- Current forbidden scope: direct host writes, overwrite/delete/move behavior, broad archive
  extraction, automatic promotion, promotion without exact artifact hash binding, and promotion
  without approval evidence.
- Current implementation posture: trusted-host promotion remains blocked; `ERG-005` may now prepare
  a limited runtime implementation plan under
  `trusted-host-promotion-implementation-gate-decision.md`.
- Current warning language: sandbox outputs may be described as staged evidence only, not promoted
  host artifacts.
- Current decision-intake evidence:
  `trusted-host-promotion-decision-intake.md` defines the preconditions, allowed outcomes, negative
  evidence, and forbidden authority claims before any trusted-host promotion decision can be
  recorded.
- Current state-machine evidence:
  `trusted-host-promotion-state-machine.md` defines future state labels, allowed transitions, safe
  evidence fields, and transition-denial cases while keeping current runtime evidence at
  `not_promoted`.
- Current negative-fixture evidence:
  `trusted-host-promotion-negative-fixtures.md` defines future denial fixture IDs, transcript shape,
  safe reason labels, and product-boundary overclaim cases while keeping trusted-host promotion
  blocked.
- Current trusted host descriptor evidence:
  `trusted-host-descriptor-contract.md` defines operator-reviewed, secret-free host posture
  evidence while keeping host control, host writes, runtime promotion, and automatic enrollment
  blocked.
- Current zone-contract evidence:
  `trusted-host-promotion-zone-contract.md` defines future `sandbox://`, `host-staging://`,
  `approved://`, and `evidence://` labels while keeping those labels as evidence identifiers only.
- Current implementation-plan evidence:
  `trusted-host-promotion-implementation-plan.md` gathers the evidence contract, decision intake,
  state machine, negative fixtures, and zone contract into the minimum future runtime-plan checklist
  while keeping trusted-host promotion blocked.
- Current source-review handoff evidence:
  `trusted-host-promotion-source-review.md` packages the design-only trusted-host promotion lane for
  reviewer disposition while keeping runtime promotion, host writes, and automatic promotion blocked.
- Current external response intake evidence:
  `trusted-host-promotion-external-response-intake.md` defines the `EXT-TRUSTED-HOST-###` finding
  namespace and `trusted-host-promotion` normalizer command for recording reviewer responses without
  mutating findings, closing `ERG-005`, or approving runtime promotion.
- Current response-kit evidence:
  `trusted-host-promotion-response-kit.md` packages response-intake guidance, normalized-response
  examples, closure commands, queue status, command evidence, and artifact hashes for real reviewer
  feedback while keeping `ERG-005`, implementation planning, runtime promotion, host writes, and
  automatic promotion blocked.
- Current disposition closure evidence:
  `trusted-host-promotion-disposition-closure-gate.md` keeps `ERG-005` blocked unless normalized
  source-level response evidence supports design-only continuation and contains no critical/high
  findings.
- Current response dry-run evidence:
  `trusted-host-promotion-response-dry-run.md` exercises temporary favorable and unfavorable
  normalized-response fixtures while restoring the ignored response path and without closing
  `ERG-005` or approving implementation planning.
- Current decision-record evidence:
  `trusted-host-promotion-decision-record.md` records
  `ready_for_implementation_planning_only` for `ERG-005` while keeping runtime implementation,
  trusted-host promotion, direct host writes, automatic promotion, Mission Control runtime behavior,
  local model invocation, sandbox orchestration, SIEM adapter behavior, public/security-product
  positioning, and new governed tool powers blocked.

### PRD-SIEM-EXPORT-001

- Status: `no_go`.
- Current allowed scope: stable event schema design, adapter architecture documentation, redaction
  policy design, offline export shape, compatibility tests, and source-review preparation.
- Current forbidden scope: hosted telemetry by default, custody-grade audit claims, stronger audit
  guarantee claims, compliance automation claims, and exporting prompts, file contents, diffs,
  response bodies, secrets, dependency names, package scripts, raw sensitive paths, or raw sandbox
  internals.
- Current implementation posture: SIEM adapter work remains blocked.
- Current warning language: Ithildin may support control mapping and evidence export design, not
  SIEM custody or automated compliance.
- Current architecture evidence:
  `siem-export-adapter-architecture.md` defines the future adapter profile, delivery, retry,
  backpressure, compatibility, signing, diagnostics, and review questions before any future runtime
  decision.
- Current disposition evidence:
  `siem-export-adapter-disposition-packet.md` asks whether the current adapter architecture
  evidence is coherent enough for continued planning while SIEM adapter runtime behavior remains
  blocked.
- Current launch-bundle evidence:
  `siem-export-adapter-external-review-bundle.md` consolidates the disposition packet,
  architecture evidence, response intake, closure gate, dry-run fixtures, queue status, and command
  evidence for reviewer handoff while keeping runtime adapter behavior blocked.
- Current external response intake evidence:
  `siem-export-adapter-external-response-intake.md` defines allowed reviewer-response outcomes and
  the `EXT-SIEM-ADAPTER-###` normalization path without mutating findings, closing `ERG-008`, or
  approving runtime adapter behavior.
- Current disposition closure evidence:
  `siem-export-adapter-disposition-closure-gate.md` validates normalized source-level response
  evidence before any later triage update may move `ERG-008` toward an architecture decision
  record; absent or unfavorable evidence keeps the row planning-only.
- Current response dry-run evidence:
  `siem-export-adapter-response-dry-run.md` exercises temporary favorable and unfavorable
  normalized-response fixtures while restoring the ignored response path and without closing
  `ERG-008` or approving implementation planning.
- Current response-kit evidence:
  `siem-export-adapter-response-kit.md` packages response-intake guidance, normalized-response
  examples, closure commands, command evidence, and artifact hashes for real reviewer feedback
  while keeping `ERG-008` planning-only and keeping implementation planning, runtime SIEM adapter
  behavior, hosted telemetry, remote delivery, and custody-grade audit claims blocked.

### PRD-COMPLIANCE-MAPPING-001

- Status: `approved_for_planning`.
- Current allowed scope: compliance mapping architecture documentation, framework/control taxonomy
  design, mapping-template schema design, operator responsibility language, legal-review boundary
  drafting, evidence-field allowlist/denylist planning, and external architecture review
  preparation.
- Current forbidden scope: compliance automation, HIPAA/GLBA/SOX/GDPR/SOC 2/NIST/CIS compliance
  claims, legal advice, automated certification, production security-product positioning,
  custody-grade audit claims, production identity, runtime Postgres, SIEM adapter runtime behavior,
  sandbox orchestration, and public/security-product positioning.
- Current implementation posture: runtime compliance mapping behavior remains blocked.
- Current warning language: Ithildin may support operator control mapping and evidence-field
  planning, not legal conclusions or claims that an organization satisfies a regulatory framework.
- Current architecture evidence:
  `compliance-mapping-architecture.md` defines future mapping template requirements, legal-review
  boundary, operator responsibility model, evidence non-goals, and review requirements before any
  future runtime decision.
- Current disposition evidence:
  `compliance-mapping-disposition-packet.md` packages the architecture, control-mapping,
  incident-reconstruction, accepted-risk, and post-RC decision evidence for reviewer disposition
  while keeping runtime compliance mapping, legal advice, automated certification, regulated-industry
  compliance claims, and public/security-product positioning blocked.
- Current external-review launch evidence:
  `compliance-mapping-external-review-bundle.md` consolidates the disposition packet,
  architecture contracts, response-intake and closure gates, dry-run evidence, queue status,
  command evidence, and artifact hashes without closing `ERG-009` or approving runtime compliance
  mapping.
- Current external response intake evidence:
  `compliance-mapping-external-response-intake.md` defines allowed reviewer-response outcomes and
  the `EXT-COMPLIANCE-MAPPING-###` normalization path without mutating findings, closing `ERG-009`,
  approving runtime compliance mapping, or approving compliance automation, legal advice, automated
  certification, regulated-industry compliance claims, custody-grade audit claims, or
  public/security-product positioning.
- Current response dry-run evidence:
  `compliance-mapping-response-dry-run.md` exercises temporary favorable and unfavorable normalized
  response fixtures, restores the ignored response path, and does not record external review, mutate
  findings, close `ERG-009`, or approve implementation/runtime compliance mapping.
- Current response-kit evidence:
  `compliance-mapping-response-kit.md` packages response-intake guidance, normalized-response
  examples, closure commands, command evidence, and artifact hashes for real reviewer feedback
  while keeping `ERG-009` planning-only and keeping implementation planning, runtime compliance
  mapping, compliance automation, legal advice, automated certification, regulated-industry
  compliance claims, and custody-grade audit claims blocked.

### PRD-PROD-IAM-STORAGE-001

- Status: `approved_for_planning`.
- Current allowed scope: production identity and durable storage architecture documentation,
  evidence-field design, migration and backup/restore planning, retention-model planning, and
  external architecture review preparation.
- Current forbidden scope: production IAM, enterprise RBAC runtime behavior, tenant/team
  authorization runtime behavior, remote admin use, runtime Postgres, database migrations,
  backup/restore runtime behavior, retention enforcement, hosted control plane, custody-grade audit
  claims, compliance automation, and public/security-product positioning.
- Current implementation posture: runtime identity and storage behavior remain blocked.
- Current architecture decision:
  `production-identity-storage-architecture-decision-record.md` records
  `approved_for_pis_001_planning_only`. It permits only the PIS-001 threat-model,
  non-goal, dependency-evaluation, exact-contract, and negative-test planning artifact. It does not
  approve dependency changes, PIS-002, schemas, migrations, production identity, runtime
  PostgreSQL, remote administration, or runtime work. Both enterprise gaps remain `planning_only`.
  The bounded execution contract is
  `production-identity-storage-pis-001-planning-gate.md`. The resulting planning artifact is
  `production-identity-storage-pis-001-threat-model-and-dependency-decision.md`; its validator keeps
  PIS-002 behind a separate entry decision and all runtime/dependency authority false.
- Current PIS-001 disposition:
  `production-identity-storage-pis-001-internal-source-review.md` binds the zero-open-finding
  independent review of exact commit `177c0c6e461176d85126c9817dba40b3a092ec95`. PIS-001 planning
  evidence is cleared.
- Current PIS-002 entry decision:
  `production-identity-storage-pis-002-entry-decision-record.md` selects only
  `SandboxDescriptorStore` for bounded dependency-free repository-interface implementation slice
  `PIS-002-SD-001`. Its closed contract is
  `production-identity-storage-pis-002-entry-decision.json`. Additional aggregates, SQLAlchemy,
  dependency changes, public behavior changes, schemas, migrations, production identity,
  PostgreSQL, new powers, release, promotion, and UAT remain unauthorized.
- Current PIS-002 implementation candidate:
  `production-identity-storage-pis-002-sandbox-descriptor-repository-implementation.md` records the
  dependency-free `SandboxDescriptorRepository` seam over the existing SQLite store and its parity
  evidence. Exact-candidate source review is now cleared by the disposition below; a second
  aggregate, dependency or schema change, PostgreSQL, production identity, release, promotion, and
  UAT remain unauthorized.
- Current PIS-002 implementation disposition:
  `production-identity-storage-pis-002-sandbox-descriptor-repository-internal-source-review.md`
  clears exact candidate `887de154` for the bounded repository interface only, with zero open
  findings and a green exact-candidate release gate. Only preparation of a separate PIS-002
  continuation decision is allowed; another aggregate, PIS-003 implementation, dependencies,
  schema/migration changes, PostgreSQL, production identity, release, promotion, and UAT remain
  unauthorized.
- Current PIS-002 continuation decision:
  `production-identity-storage-pis-002-continuation-decision-record.md` closes the dependency-free
  PIS-002 interface phase after the one reviewed repository seam. The remaining direct-SQLite stores
  cross transaction, recovery, audit-ordering, migration, or dialect boundaries, so another
  dependency-free aggregate interface is not selected. Only preparation and dependency evaluation
  for a separately gated PIS-003 entry decision are allowed; PIS-003 implementation, dependencies,
  schemas/migrations, PostgreSQL, production identity, new powers, release, promotion, and UAT remain
  unauthorized.
- Current PIS-003 entry-decision candidate:
  `production-identity-storage-pis-003-entry-decision-record.md` selects proposed slice
  `PIS-003-SD-PG-001` and exact non-default SQLAlchemy Core, Alembic, and plain synchronous Psycopg
  tooling for one isolated `sandbox_descriptors` PostgreSQL schema/import proof. Its closed contract
  is `production-identity-storage-pis-003-entry-decision.json`. The candidate requires independent
  exact-candidate source review followed by a separate committed implementation gate. Dependency
  changes, implementation, database connections/services, migration execution, runtime PostgreSQL,
  production identity, new powers, release, promotion, and UAT remain unauthorized.
- Current PIS-003 entry-decision review:
  `production-identity-storage-pis-003-entry-internal-source-review.md` records a zero-finding
  independent Sol xhigh review of exact commit `fe870f2`; Sol Ultra was not used. Its closed
  `production-identity-storage-pis-003-entry-review-authority.json` contract permits only preparation
  of a separate `PIS-003-SD-PG-001` implementation gate. It does not authorize dependencies,
  implementation, database connections/services, schema/migration execution, runtime PostgreSQL,
  production identity, new powers, release, promotion, or UAT.
- Current PIS-003 SD-PG-001 implementation gate:
  `production-identity-storage-pis-003-sd-pg-001-implementation-gate.md` binds the exact bounded
  implementation candidate, 20 allowed paths, seven-package non-default lock delta, caller-owned
  transaction/connection code boundary, phase-aware predecessor validation, offline evidence, and
  rollback. Test-harness implementation is separable from execution; any external DSN use,
  database connection, or migration execution requires a later connection-evidence gate. Its closed
  contract is `production-identity-storage-pis-003-sd-pg-001-implementation-gate.json`. The gate
  requires exact-candidate source review; dependencies, implementation, database connections or
  services, migration execution, runtime PostgreSQL, production identity, new powers, release,
  promotion, and UAT remain unauthorized.
- Current PIS-003 SD-PG-001 implementation-gate review:
  `production-identity-storage-pis-003-sd-pg-001-implementation-gate-internal-source-review.md`
  records a zero-finding independent Sol xhigh review of exact repaired commit `9f347fa`; Sol Ultra
  was not used. Its closed
  `production-identity-storage-pis-003-sd-pg-001-implementation-gate-review-authority.json`
  contract permits only the exact offline dependency, SQLAlchemy Core, Alembic artifact,
  schema/importer, and unexecuted test-harness implementation ceiling. Driver load/use, DSN use,
  connections, migration execution, services, runtime PostgreSQL, production identity, new powers,
  release, promotion, and UAT remain unauthorized pending later gates.
- Current warning language: Ithildin may discuss production identity and durable storage
  architecture, but the current runtime remains local-preview with local principal labels and SQLite.
- Current architecture evidence:
  `production-identity-storage-architecture.md` defines the `ERG-006`/`ERG-007` identity, tenancy,
  storage, migration, backup/restore, retention, and evidence questions before any future runtime
  decision. Its disaster-recovery candidate treats lost Node identities as replaceable rather than
  restorable, requires an external recovery watermark before a restored Manager can regain
  authority, and fails closed on stale snapshots, missing authority epochs, or split-brain risk.
- Current source-review evidence:
  `production-identity-storage-source-review.md` records the independent packet-and-source review
  of commit `531bcfd87f0a42a3818bc6de73ad884cd6d090f2`, its five medium
  `EXT-PROD-IAM-STORAGE-###` findings, and the exact-candidate re-review of remediation commit
  `88f8e53cc54e599df25da6b14d465a5fb06848d7`. The re-review verified every finding fixed, found no
  new critical/high/medium issue, and returned `continue_architecture_planning`. The normalized
  response passed exact commit and packet-manifest binding, making both gaps
  `ready_for_architecture_decision_record` as a review disposition only. Both registered gap states
  remain `planning_only` until a separate bounded architecture decision record is committed.
- Current disposition evidence:
  `production-identity-storage-disposition-packet.md` asks whether the current architecture
  evidence is coherent enough for continued planning while runtime identity and storage behavior
  remain blocked.
- Current launch bundle evidence:
  `production-identity-storage-external-review-bundle.md` consolidates the architecture/disposition
  packet, response-intake template, fail-closed closure gate, response dry-run, queue status, and
  command evidence for external handoff without closing `ERG-006`/`ERG-007`.
- Current external response intake evidence:
  `production-identity-storage-external-response-intake.md` defines the `EXT-PROD-IAM-STORAGE-###`
  finding namespace and `production-identity-storage` normalizer command for recording reviewer
  responses without mutating findings, closing `ERG-006`/`ERG-007`, or approving runtime identity
  and storage behavior.
- Current disposition closure evidence:
  `production-identity-storage-disposition-closure-gate.md` validates normalized source-level
  response evidence before any later triage update may move `ERG-006` or `ERG-007` toward an
  architecture decision record; absent or unfavorable evidence keeps both rows planning-only.
- Current response dry-run evidence:
  `production-identity-storage-response-dry-run.md` exercises temporary favorable and unfavorable
  normalized-response fixtures while restoring the ignored response path and without closing
  `ERG-006`/`ERG-007` or approving implementation planning.
- Current response-kit evidence:
  `production-identity-storage-response-kit.md` packages response-intake guidance,
  normalized-response examples, closure commands, command evidence, and artifact hashes for real
  reviewer feedback while keeping `ERG-006` and `ERG-007` planning-only and keeping implementation
  planning, runtime identity, runtime storage, migrations, retention enforcement, and production
  custody blocked.

## Validation

Run:

```sh
make post-rc-decision-register-check
make post-rc-decision-record-examples-check
make post-rc-decision-gate
```

For `ERG-003`, the future static preflight disposition-record shape is
`sandbox-vm-static-preflight-disposition-record-skeleton.md`. It supports only a favorable
source-reviewed local-preview static preflight disposition and keeps `ERG-004`, live POC planning,
runtime implementation, Mission Control runtime behavior, local model invocation, trusted-host
promotion, and new powers blocked.

The received `ERG-003` and `ERG-002` response disposition is tracked in
`enterprise-dual-response-disposition-record.md`. It records the allowed static-preflight closure,
the Mission Control design-only continuation state, and the open low advisory
`EXT-MC-DISPLAY-001` without approving runtime importer behavior, live sandbox/VM implementation,
or new governed tool powers.

All checks must remain green before `make release-check` can pass.
