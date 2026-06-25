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
- supported platform matrix;
- mount/root contract;
- network posture contract;
- artifact ingress/egress contract;
- failure and cleanup transcripts;
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

After the v1.0 local-preview RC packet remains green, the next enterprise-path action should be a
design-only Mission Control display integration proposal. It should use the existing Hello World
Mission Control handoff as the seed and continue treating Mission Control as an evidence viewer, not
an execution or policy authority. In short: Mission Control is the evidence viewer, not an execution or policy authority.
