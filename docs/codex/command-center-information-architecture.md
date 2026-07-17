# Command Center Information Architecture

Status: current product/UX information architecture. This document describes presentation and
routing contracts; it does not authorize new runtime behavior.

This information architecture applies the
[pilot scope](command-center-product-direction-and-pilot-scope.md) to Ithildin Command Center. It
organizes existing and future display surfaces; it does not create data, states, APIs, mutations,
permissions, or Gateway authority.

## Navigation Model

The persistent primary navigation is:

1. **Attention**
2. **Missions / Agent Runs**
3. **Artifacts**
4. **Approvals**
5. **Evidence**
6. **Administration**

`Workbench` is not a seventh inventory page. It is the contextual workspace opened from a mission,
run, attention item, approval, artifact, or evidence record. It keeps the selected mission and its
correlated objects together.

The shell should always expose:

- product name and one-sentence purpose;
- current location and selected mission, when any;
- authentication state separated from local-preview restrictions;
- local-preview and trust-posture warnings that materially affect the current task;
- help and terminology entry points;
- current operator view: routine operator, investigator, policy administrator, or technical
  reviewer;
- stable return paths to Attention and the selected Workbench.

A view label changes presentation and defaults only unless backed by existing authorization. It
must not imply a new role, permission, identity, or RBAC capability.

## Area Contracts

### Attention

**Question:** What requires action or investigation now, and what is the consequence of waiting?

Primary content:

- pending operator decisions;
- denied or failed mediated actions that affect a mission outcome;
- deterministic Node fleet exceptions derived from existing Gateway state;
- recovery-required diagnostics;
- artifacts ready for review;
- evidence integrity or signing warnings that affect the current handoff;
- clearly labeled volume summaries derived from existing records.

Each item shows a plain-language title, mission, why it matters, required action, age, current state,
and safe next action. It links into the relevant Workbench context.

Do not imply behavioral anomaly detection. An `unusual volume` label is allowed only if a reviewed,
deterministic comparison exists; otherwise show neutral counts and filters.

Technical drill-down may show request IDs, run IDs, approval IDs, policy hashes, event hashes, and
raw audit records. Those details must not dominate the queue.

The current deterministic queue precedence is: pending approval; Node authority or evidence
incompleteness; failed mediated action; patch recovery; operational Node drift; passive patch
proposal. Within the Node classes, one item per enrolled Node represents that Node's highest-ranked
known exception. Revoked and currently healthy Nodes do not create Attention items. A Node action
routes to the exact authoritative fleet record; it does not mutate Node state.

Node Attention is a presentation derivation from enrollment, audit-evidence, accepted-heartbeat,
signed desired-configuration, storage-acknowledgment, signing-trust, and version-comparison fields
already returned by the Gateway. It is not anomaly detection, endpoint health monitoring, runner
health, model-provider health, or proof of configuration enforcement.

### Missions / Agent Runs

**Question:** What work was the agent trying to accomplish, what mediated activity occurred, and
what is its current outcome?

Primary content:

- mission-facing name and intent, when supplied by reviewed local configuration or fixture;
- model/client label when available, with no inference from untrusted content;
- run status and last activity time;
- requesting identity, workspace, tools used, decisions, outcomes, artifacts, and attention count;
- filters for time, identity, mission, tool, decision, status, workspace, and attention state;
- grouped summaries before individual events.

The current Agent Run record remains a diagnostic grouping of mediated calls. A mission label or
intent is presentation context, not proof that Ithildin started, owns, or controls an agent process.

Opening a mission enters Workbench with tabs or local navigation for Overview, Activity, Decisions,
Artifacts, and Evidence. The raw timeline remains available under Activity or technical detail.

### Artifacts

**Question:** What output is ready for review, what state is it in, and what decision is available?

Primary content:

- human-facing artifact label and mission;
- source zone and destination label in safe language;
- review readiness and current lifecycle state;
- concise content/change summary where already available and safe;
- digest comparison and proposal/approval binding when relevant;
- next action and the authority that will perform it.

`Ready for review` means an artifact has sufficient evidence for the defined review task. It does
not mean approved, applied, promoted, published, release-ready, or trusted. Raw content, diffs,
paths, and hashes appear only when needed and already authorized for that reviewer.

### Approvals

**Question:** Which decision needs a human, why was it required, and what exactly would the existing
approval authorize?

Primary content:

- request summary, mission, requesting identity, tool, resource label, risk/capability class, and
  policy reason;
- one-time scope, expiry, and operational consequence;
- proposal state kept distinct from approval state;
- stable list selection with adjacent detail;
- search, filtering, sorting, and grouping for longer histories;
- clear outcomes for approved, denied, expired, superseded, executing, executed, and failed states
  where those states exist in current authoritative records.

Command Center submits operator decisions only through existing approval APIs. It does not create
approval truth or execute the governed action itself.

### Evidence

**Question:** What can the operator or reviewer understand, verify, and hand off about Ithildin-
mediated activity?

Primary content:

- mission/run evidence summary;
- policy decision, approval, execution, artifact, audit-integrity, redaction, and export status;
- important warnings before technical inventory;
- explanation of what is locally verified and what is not;
- reviewer and investigator drill-down to timelines, raw audit events, hashes, manifests, packet
  references, JSONL, and signed exports.

Evidence completeness, audit integrity, signature validity, and export creation are separate states.
An unsigned bundle may still contain useful local evidence if clearly labeled; it must not appear
equivalent to a valid locally signed export.

### Administration

**Question:** How is this local preview configured, and how can a specialist inspect existing
policy, tools, identities, workspaces, and system posture?

Primary content:

- System Trust summary and detailed diagnostics;
- registered tool inventory with human-facing names and effective policy/approval context;
- identities/principals and workspaces;
- contextual policy troubleshooting and candidate impact analysis;
- manifest/version evidence;
- local configuration, help, display, and accessibility controls;
- technical export controls and documentation links.

Policy Preview should be framed as **Request decision preflight** and start from a real request,
attention item, mission, or guided safe example. Candidate YAML Policy Impact remains a specialist
policy-administration task. Neither belongs on the routine operator front door.

## Workbench Context

Workbench preserves one selected mission context across:

| Workbench view | Operator question | Default content | Technical detail |
| --- | --- | --- | --- |
| Overview | What is this mission and what needs attention? | Intent, status, attention, identities, workspace, outcomes. | Run/session IDs and source metadata. |
| Activity | What happened in order? | Grouped milestones and outcomes. | Full correlated event timeline. |
| Decisions | Why did Ithildin allow, deny, or require approval? | Plain-language decision explanation and consequence. | Matched policy evidence, tool/manifest identifiers, request ID. |
| Artifacts | What output can I review? | Artifact cards, readiness, proposal/approval/application state. | Diffs, digests, safe paths, diagnostics where authorized. |
| Evidence | What can I verify or export? | Integrity, signing, completeness, warnings, handoff summary. | Raw events, hashes, JSONL, packet references, export metadata. |

Selection must remain stable across list and detail views. A selected object must show its label,
type, state, and mission association adjacent to the detail so the operator never has to infer what
they clicked.

## Persona Surface Separation

| Area | Routine operator default | Investigator default | Policy administrator default | Technical reviewer default |
| --- | --- | --- | --- | --- |
| Attention | Required actions and consequences | Failures, denials, recovery, evidence warnings | Policy-related denials and stale candidate work | Integrity, signing, and handoff warnings |
| Missions / Runs | Mission outcomes and attention | Filters, groupings, correlated timelines | Decisions grouped by identity/tool/workspace | Evidence-bearing runs and reconstruction |
| Artifacts | Ready-for-review items | Artifact lineage and diagnostics | Policy relationship only | Digests, binding, packet lineage |
| Approvals | Pending decisions and clear scope | Approval history and correlations | Rule/reason context | Binding and lifecycle evidence |
| Evidence | Understandable closeout | Reconstruction and raw events | Policy-decision evidence | Hashes, signatures, exports, manifests |
| Administration | Help, preferences, visible limitations | Diagnostic configuration | Policy preflight/impact and identities | Tool manifests, raw contracts, review docs |

Cross-links are allowed; mixing all specialist controls into every default view is not. Information
architecture separation does not create a new authorization model.

## Reusable Interaction Patterns

Every queue or history uses the same contract:

- named columns with operator meaning;
- search plus task-relevant filter presets;
- time range and sort order when records can grow;
- grouping before raw rows;
- stable selected-row state;
- adjacent or clearly anchored detail;
- concise summary before raw data;
- explicit empty, loading, authentication-required, unavailable, and error states;
- machine ID copy/search controls in technical detail;
- no color-only encoding of risk, decision, or state.

Every decision explanation answers, in order:

1. What did the agent request?
2. What did Ithildin decide?
3. Why?
4. What was the operational consequence?
5. Is human action required?
6. What evidence is available?

## Authority and Data Provenance

| Displayed concept | Authoritative source | Command Center responsibility |
| --- | --- | --- |
| Tool registration and manifest identity | Gateway registry and manifest lock | Explain and display; never infer effective permission from registration alone. |
| Policy decision | Gateway policy evaluation/audit evidence | Summarize the recorded decision and retain policy evidence. |
| Approval state | Existing approval records/APIs | Display and submit allowed operator action; never synthesize completion. |
| Execution/application result | Gateway executor and diagnostics | Display recorded outcome; never execute outside Gateway. |
| Agent Run | Existing run records and audit correlation | Group and explain mediated activity; never claim process control. |
| Artifact and promotion state | Existing artifact/proposal/promotion records | Display exact recorded state; never equate review readiness with promotion. |
| Audit integrity and signing | Existing audit verification and signing records | Explain status and limitations; never mutate or overclaim custody. |
| Export | Existing export API or packet generator | Initiate only an existing reviewed export and label the result accurately. |

Presentation-derived counts, labels, and groupings must be deterministic, traceable to authoritative
records, and visibly marked when they are a UI summary rather than stored Gateway state.

## Implementation Review Gate

Before UI implementation begins, reviewers must accept the product/pilot scope, this information
architecture, the [golden scenario](command-center-golden-pilot-scenario.md), the
[terminology and state contract](command-center-terminology-and-state-contract.md), and the ordered
[epic and backlog](command-center-pilot-epic-and-backlog.md). The first implementation ticket must
also confirm that its required data already exists without schema or API changes.
