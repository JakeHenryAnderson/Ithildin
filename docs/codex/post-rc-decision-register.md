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
| `PRD-SANDBOX-LIVE-POC-001` | Live sandbox/VM worker proof of concept | `no_go` | Maintain the decision-intake packet and wait for favorable `ERG-003` disposition | `false` | Favorable static-preflight disposition, live POC decision record, implementation plan, cleanup/failure transcripts, and external/source review |
| `PRD-CAPABILITY-001` | New governed tool after RC freeze | `no_go` | Candidate selection and design packet only | `false` | Capability proposal, implementation plan, source-review handoff, negative transcripts, and accepted-risk update |
| `PRD-TRUSTED-HOST-001` | Trusted-host promotion lane | `no_go` | Promotion state-machine design, decision-intake, implementation-plan skeleton, and evidence contract discussion only | `false` | Artifact hash-binding model, approval model, state-machine evidence, negative transcripts, zone contract, implementation-plan skeleton, decision-intake evidence, and external/source review |
| `PRD-SIEM-EXPORT-001` | SIEM-shaped export adapter lane | `no_go` | Stable schema, adapter architecture, compatibility tests, and offline export design only | `false` | The architecture packet in `siem-export-adapter-architecture.md`, the disposition packet in `siem-export-adapter-disposition-packet.md`, the response intake template in `siem-export-adapter-external-response-intake.md`, delivery model, redaction policy, compatibility tests, signing/verification story, post-RC decision record, and external/source review |
| `PRD-COMPLIANCE-MAPPING-001` | Compliance mapping support lane | `approved_for_planning` | Mapping-template architecture, operator responsibility language, legal-review boundary, and evidence-field planning only | `false` | The architecture packet in `compliance-mapping-architecture.md`, the disposition packet in `compliance-mapping-disposition-packet.md`, the response intake template in `compliance-mapping-external-response-intake.md`, exact framework scope, template schema, evidence allowlist/denylist, accepted-risk impact review, post-RC decision record, and external/source review before runtime work |
| `PRD-PROD-IAM-STORAGE-001` | Production identity and durable storage architecture | `approved_for_planning` | Maintain the architecture packet, threat model questions, migration/retention/backup planning, and external architecture review preparation | `false` | Post-RC decision record, identity provider design, tenant/workspace model, storage/migration plan, backup/restore plan, failure-mode tests, and external architecture review before runtime work |
| `PRD-PUBLIC-POSITIONING-001` | Public/security-product positioning | `no_go` | Claim-review documentation, warning-packet review, operator support/deployment model planning, evidence mapping, and external review preparation only | `false` | `public-security-product-positioning-decision-intake.md`, resolved claim-dependent external/source review rows, accepted-risk disposition, support/deployment/update/incident-response model, explicit claim wording review, and a later committed go/no-go decision before any broader public/security-product positioning |

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

### PRD-SANDBOX-PREFLIGHT-001

- Status: `no_go`.
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

### PRD-SANDBOX-LIVE-POC-001

- Status: `no_go`.
- Current allowed scope: decision-intake evidence in
  `sandbox-vm-live-poc-decision-intake.md`, favorable `ERG-003` disposition tracking,
  decision-record drafting, docs, review packets, the readiness map in
  `enterprise-sandbox-control-plane-readiness.md`, the preconditions map in
  `sandbox-vm-live-poc-preconditions-map.md`, the decision packet in
  `sandbox-vm-live-poc-decision-packet.md`, the external response intake template in
  `sandbox-vm-live-poc-external-response-intake.md`, the fail-closed closure gate in
  `sandbox-vm-live-poc-decision-closure-gate.md`, and operator warnings.
- Current forbidden scope: live VM/container inspection, local model invocation, Mission Control
  runtime behavior, sandbox orchestration, SSH, shell, Docker socket access, Kubernetes tools,
  browser automation, arbitrary HTTP, broad filesystem writes, trusted-host promotion, runtime
  profile loading, production identity, SIEM adapters, and public/security-product positioning.
- Current implementation posture: live worker runtime behavior remains blocked.
- Current warning language: Ithildin does not run a local model, inspect a live VM/container,
  orchestrate a sandbox, or promote sandbox artifacts in this lane.

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

### PRD-TRUSTED-HOST-001

- Status: `no_go`.
- Current allowed scope: design-only discussion of source/destination zones, artifact hashes,
  approval binding, replay denial, conflict handling, and operator warnings.
- Current forbidden scope: direct host writes, overwrite/delete/move behavior, broad archive
  extraction, automatic promotion, promotion without exact artifact hash binding, and promotion
  without approval evidence.
- Current implementation posture: trusted-host promotion remains blocked.
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
- Current external response intake evidence:
  `siem-export-adapter-external-response-intake.md` defines allowed reviewer-response outcomes and
  the `EXT-SIEM-ADAPTER-###` normalization path without mutating findings, closing `ERG-008`, or
  approving runtime adapter behavior.

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
- Current external response intake evidence:
  `compliance-mapping-external-response-intake.md` defines allowed reviewer-response outcomes and
  the `EXT-COMPLIANCE-MAPPING-###` normalization path without mutating findings, closing `ERG-009`,
  approving runtime compliance mapping, or approving compliance automation, legal advice, automated
  certification, regulated-industry compliance claims, custody-grade audit claims, or
  public/security-product positioning.

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
- Current warning language: Ithildin may discuss production identity and durable storage
  architecture, but the current runtime remains local-preview with local principal labels and SQLite.
- Current architecture evidence:
  `production-identity-storage-architecture.md` defines the `ERG-006`/`ERG-007` identity, tenancy,
  storage, migration, backup/restore, retention, and evidence questions before any future runtime
  decision.
- Current disposition evidence:
  `production-identity-storage-disposition-packet.md` asks whether the current architecture
  evidence is coherent enough for continued planning while runtime identity and storage behavior
  remain blocked.
- Current external response intake evidence:
  `production-identity-storage-external-response-intake.md` defines the `EXT-PROD-IAM-STORAGE-###`
  finding namespace and `production-identity-storage` normalizer command for recording reviewer
  responses without mutating findings, closing `ERG-006`/`ERG-007`, or approving runtime identity
  and storage behavior.

## Validation

Run:

```sh
make post-rc-decision-register-check
make post-rc-decision-record-examples-check
make post-rc-decision-gate
```

All checks must remain green before `make release-check` can pass.
