# Command Center Pilot Epic and Ordered Backlog

Status: complete operator-UAT finding set accepted into backlog scope; ticket order and
implementation details remain proposed until reviewed.

Epic: `CC-PILOT-001`
Title: **Make Ithildin Command Center a self-guided, exception-first local-preview pilot cockpit**

This epic tracks product/UX work only within the current 24-tool and Gateway-authority boundary. It
does not approve UI implementation by itself and does not authorize schemas, APIs, manifests,
policy, approvals, audit, signing, promotion, orchestration, deployment, identity, SIEM, sandbox,
or security-claim changes.

## Epic Outcome

A fresh routine operator can complete the
[golden scenario](command-center-golden-pilot-scenario.md): locate one meaningful Attention item,
understand the associated mediated mission and policy outcome, review one ready artifact, and finish
with understandable evidence without facilitator coaching.

The experience follows the [product/pilot scope](command-center-product-direction-and-pilot-scope.md),
[information architecture](command-center-information-architecture.md), and
[terminology/state contract](command-center-terminology-and-state-contract.md).

## Scope and Status Contract

- `approved_for_backlog`: the operator authorized all 62 direct observations and 8 explicitly
  labeled facilitator inferences to become tracked design and pilot work.
- `implementation_not_approved`: no ticket below is authorization to begin implementation until its
  prerequisites and review gate are satisfied.
- `inference_requires_validation`: `UAT-OBS-063` through `UAT-OBS-070` must remain labeled inferred
  until the second fresh-operator UAT produces direct observations.
- `current_runtime_boundary`: local preview, governed tool count `24`, Command Center display/review
  surface, Gateway enforcement authority.

## Ordered Tickets

### `CC-PILOT-101` — Orient and triage from an exception-first front door

**Operator value:** A first-time operator immediately understands the product, authentication state,
local-preview limitation, what needs attention, and where the selected item belongs.

**Thin vertical slice:** Implement the persistent six-area shell, purpose statement, help entry,
authentication-versus-preview messaging, and one Attention item linked to the Hello World mission
Workbench. Use only existing data and one reviewed fixture path.

**Acceptance criteria:**

- first viewport answers what Ithildin is, what needs attention, and the next action;
- Attention item shows mission, state, age, consequence, and safe next action;
- selection opens a stable Workbench context without losing the item;
- routine path does not show raw YAML, hashes, manifests, or audit rows by default;
- Command Center/Workbench/Gateway boundaries are visible in concise product language;
- loading, empty, sign-in-required, unavailable, and error states are understandable;
- existing focused UI tests cover purpose, navigation, state labels, and linked selection.

**Required preimplementation evidence:** a field-to-authoritative-source map proving the slice needs
no schema or API change.

**Stop conditions:** new identity/RBAC behavior, external notification integration, mission
creation, orchestration, or synthesized attention truth.

### `CC-PILOT-102` — Explain one governed request in mission context

**Operator value:** From the selected Attention item, the operator can explain what was requested,
what Ithildin decided, why, the operational consequence, and whether human action is required.

**Thin vertical slice:** Add the Workbench Decisions view for the selected existing request. Lead
with a six-question plain-language explanation and retain policy, tool, manifest, request, and audit
identifiers in technical detail. Rehome request preflight into contextual troubleshooting rather
than the primary dashboard.

**Acceptance criteria:**

- tool registration and effective permission are explicitly separate;
- requesting identity and workspace are named and labeled;
- `Allowed`, `Denied`, and `Approval required` examples have distinct consequences, using existing
  records or safe reviewed fixtures only;
- request decision preflight is non-mutating, contextual, and clearly says it does not execute,
  create an approval, or apply policy;
- no hidden policy reason is invented when authoritative evidence lacks it;
- policy-administrator YAML remains available outside the routine path.

**Stop conditions:** policy semantic changes, new example-execution behavior, a new endpoint, or a
generic simulator returning to the primary dashboard.

### `CC-PILOT-103` — Review an artifact through an honest proposal and approval lifecycle

**Operator value:** The operator can follow one proposal through approval and recorded application
to a ready artifact without confusing any of those states.

**Thin vertical slice:** Implement stable approval/proposal list-detail behavior and the selected
artifact review view for the Hello World scenario. Use existing approval actions and existing
staging-only evidence; Command Center remains a client of Gateway authority.

**Acceptance criteria:**

- proposal, approval, application, artifact, review, and evidence states remain separate;
- each row labels workspace, requesting identity, scope, state, time, and next action;
- selected detail remains adjacent to and visibly associated with the selected row;
- concise change/artifact summary precedes raw diff, content, digest, or path;
- longer lists support labeled columns, search/filter/sort, grouping, and stable selection;
- `Ready for review` never implies approved, promoted, published, or release-ready;
- if no existing authoritative review-complete mutation exists, the UI does not create one.

**Stop conditions:** new approval semantics, approval creation outside the existing API, broader
promotion, arbitrary host writes, or a fabricated lifecycle state.

### `CC-PILOT-104` — Close the mission with understandable evidence

**Operator value:** The operator can summarize what happened and hand a technical reviewer a
bounded evidence view without first interpreting raw telemetry.

**Thin vertical slice:** Add the golden scenario Evidence closeout with decision, approval,
application, artifact, audit-integrity, signing, export, warning, and limitation summaries. Preserve
full audit rows, hashes, manifests, JSONL, and packet references behind technical drill-down.

**Acceptance criteria:**

- audit integrity, evidence completeness, export creation, and signing verification are separate;
- every `verified`, `signed`, `ready`, or `complete` label names its object and scope;
- missing signing key, stale/unavailable verification, invalid signature, partial export, and export
  failure have explicit non-success states;
- evidence states what they do not prove, including activity outside Ithildin and host-compromise
  resistance;
- the existing read-only export action, if used, remains bounded and secret-free;
- technical evidence remains complete and searchable without dominating routine closeout.

**Stop conditions:** audit mutation, new custody or immutability claim, SIEM adapter behavior,
expanded export contents, or public security/compliance claims.

### `CC-PILOT-105` — Make mission and run investigation scalable

**Operator value:** An investigator can narrow and summarize mediated activity without scanning a
raw event table.

**Thin vertical slice:** Provide mission/run groupings and filters for time, identity, mission,
workspace, tool, decision, status, outcome, and attention state, with grouped summaries before the
timeline.

**Acceptance criteria:**

- filters have labeled values, removable chips, reset behavior, and an understandable empty state;
- mission name/intent is clearly presentation context when it is not stored run truth;
- counts and volume summaries are deterministic and traceable;
- no anomaly-detection, orchestration, or external-activity claim is implied;
- full correlated timeline and IDs remain available in technical detail;
- investigator defaults do not expose policy editing or approval authority.

**Stop conditions:** new run-control behavior, model/process telemetry, new run schema/API fields,
or inferred behavioral anomaly detection.

### `CC-PILOT-106` — Separate specialist administration and technical-review surfaces

**Operator value:** Routine operations stay focused while policy administrators and technical
reviewers can still reach the complete existing detail needed for troubleshooting and review.

**Thin vertical slice:** Rehome System Trust, registered tool inventory, candidate policy impact,
manifests, raw audit events, signing/export detail, configuration, documentation, and accessibility
controls under Administration or technical-review routes using the terminology contract.

**Acceptance criteria:**

- routine operator, investigator, policy administrator, and technical reviewer defaults are
  visibly distinct;
- capability class, effective availability, decision, attention severity, and consequence use
  separate fields;
- human-facing tool names lead and machine names remain available;
- System Trust becomes scoped local posture rather than a single global safety claim;
- candidate policy impact remains non-mutating specialist work;
- integration/deployment questions link to explicit boundaries, not unsupported API, spreadsheet,
  notification, SIEM, cloud, or regulated-environment promises;
- historical Mission Control names are presented as lineage, not current product topology.

**Stop conditions:** role/RBAC semantic changes, policy application, tool-count changes, external
integrations, deployment work, or security/product claims.

### `CC-PILOT-107` — Run an uncoached fresh-operator UAT and disposition the epic

**Operator value:** The team learns whether the golden pilot is genuinely self-guided rather than
facilitator-dependent.

**Thin vertical slice:** Execute the second-UAT protocol in the golden scenario with a fresh
operator, record direct observations, explicitly validate or refute the eight inferred findings,
and return failures to the smallest responsible ticket.

**Acceptance criteria:**

- browser visibility, URL, credential path, fixture, and warning states pass environment preflight;
- facilitator provides only the task card and product-visible help;
- direct observations remain separate from interpretation;
- pass thresholds and all eight comprehension questions are recorded;
- `UAT-OBS-063` through `UAT-OBS-070` each receive a direct-validation disposition;
- evidence is labeled QA-only and does not authorize release, approval, promotion, or expansion;
- epic status remains `pilot_candidate` until a human reviews the UAT result.

**Stop conditions:** coaching is required to finish, environment intervention teaches the workflow,
an authority-confusion error occurs, or implementation requires boundary expansion.

## Finding Coverage

The mapping below keeps the complete UAT set in tracked scope without turning observations into
field-by-field implementation tickets.

| UAT finding set | Evidence class | Primary ticket | Coverage theme |
| --- | --- | --- | --- |
| `UAT-OBS-001` | Direct | `CC-PILOT-107` | Browser-visible environment preflight. |
| `UAT-OBS-002`–`007` | Direct | `CC-PILOT-101` | Purpose, hierarchy, triage, navigation, help, accessibility. |
| `UAT-OBS-008` | Direct | `CC-PILOT-106` | Explicit integration and export boundaries. |
| `UAT-OBS-009`–`012` | Direct | `CC-PILOT-101` | Authentication and prioritized post-auth orientation. |
| `UAT-OBS-013` | Direct | `CC-PILOT-105` | Agent Run filters. |
| `UAT-OBS-014`–`025` | Direct | `CC-PILOT-106` | Local posture, tools, risk dimensions, human-facing labels. |
| `UAT-OBS-026` | Direct | `CC-PILOT-102` | Policy-surface audience, inputs, and non-mutation. |
| `UAT-OBS-027` | Direct | `CC-PILOT-106` | Candidate YAML moved to specialist administration. |
| `UAT-OBS-028` | Direct | `CC-PILOT-101` | Persistent task sequence and navigation. |
| `UAT-OBS-029`–`038` | Direct | `CC-PILOT-102` | Contextual request decision preflight and guided inputs. |
| `UAT-OBS-039`–`045` | Direct | `CC-PILOT-101` | Umbrella product, Workbench, Gateway authority, front door. |
| `UAT-OBS-046`–`047` | Direct | `CC-PILOT-106` | Deployment and regulated/security claim limits. |
| `UAT-OBS-048`–`050` | Direct | `CC-PILOT-103` | Scalable approval/proposal list-detail layout. |
| `UAT-OBS-051` | Direct | `CC-PILOT-101` | Exception-first priority. |
| `UAT-OBS-052` | Direct | `CC-PILOT-105` | Operator-relevant activity aggregation. |
| `UAT-OBS-053` | Direct | `CC-PILOT-104` | Technical evidence through progressive disclosure. |
| `UAT-OBS-054` | Direct | `CC-PILOT-106` | Persona separation. |
| `UAT-OBS-055` | Direct | `CC-PILOT-101` | Persistent navigation and location cues. |
| `UAT-OBS-056`–`062` | Direct | `CC-PILOT-103` | Proposal/approval lifecycle, labels, selection, summaries. |
| `UAT-OBS-063`–`065` | Inferred | `CC-PILOT-105`, then `107` | Mission-centric run context, filters, grouping; direct retest required. |
| `UAT-OBS-066`–`067` | Inferred | `CC-PILOT-104`, then `107` | Audit/export progressive disclosure; direct retest required. |
| `UAT-OBS-068` | Inferred | `CC-PILOT-103`, then `107` | Discoverable ready-artifact story; direct retest required. |
| `UAT-OBS-069`–`070` | Inferred/blocker | `CC-PILOT-107` | Uncoached comprehension and bounded end-to-end pilot validation. |

Secondary mappings are allowed in implementation plans, but no finding may be marked resolved from
documentation alone.

## Dependency and Review Order

```text
UAT evidence classification
  -> product direction and pilot-scope review
  -> information architecture review
  -> golden-scenario and terminology/state-contract review
  -> epic/order review
  -> authoritative-data feasibility map for CC-PILOT-101 through 104
  -> CC-PILOT-101 Orient and triage
  -> CC-PILOT-102 Explain decision
  -> CC-PILOT-103 Review artifact lifecycle
  -> CC-PILOT-104 Evidence closeout
  -> CC-PILOT-105 Investigation scale
  -> CC-PILOT-106 Specialist separation
  -> focused accessibility, authority-boundary, and UI review
  -> CC-PILOT-107 fresh-operator UAT
  -> human pilot disposition
```

`CC-PILOT-105` and `CC-PILOT-106` may be implemented after `101` in either order if their changes do
not touch the selected golden path. They must be complete before the fresh UAT if their absence
would leave raw/specialist surfaces in the routine path. Only one agent should own implementation at
a time.

## Reviews Required Before UI Implementation

1. **Product review:** accept the candidate direction as direction only and the exact local-preview
   pilot scope.
2. **Authority review:** confirm Command Center/Workbench remain presentation and reviewed API
   clients, while Gateway remains the enforcement and audit source of truth.
3. **Evidence review:** confirm the selected fixture uses live authoritative records where claimed
   and labels generated packets as evidence rather than live state.
4. **Terminology review:** accept the lifecycle labels, overclaim prohibitions, and machine-ID
   retention contract.
5. **Data feasibility review:** map every required visible field and action for the first ticket to
   an existing API/record. Any missing runtime contract blocks UI work.
6. **Implementation-ticket review:** approve only the smallest next ticket, its allowed files,
   focused tests, and stop conditions.

Approval of one ticket does not approve later tickets or this entire epic.

## First Implementation Recommendation

Start with `CC-PILOT-101` after the five design artifacts and its authoritative-data feasibility map
are reviewed. It is the smallest implementation slice that tests the highest-risk UAT blocker:
whether a first-time operator can understand Ithildin and enter a meaningful triage path from the
first viewport.

Keep its implementation limited to the current UI and existing API responses. Use one Attention
item and one mission context, add focused UI tests, and stop before generalized dashboard redesign,
artifact mutation, policy tooling, new data contracts, or later-ticket specialist surfaces.

Recommended done-when for that future ticket:

- purpose, auth/local-preview distinction, six-area shell, and one linked Attention item render;
- keyboard and selection behavior pass focused tests;
- no raw technical detail dominates the routine path;
- the data-source map proves no synthesized authority or missing API;
- tool count remains `24` and no schema, manifest, policy, approval, audit, or API file changes;
- human product review accepts the slice before `CC-PILOT-102` begins.

## Epic Completion Boundary

The epic is complete only after the second UAT record is human-reviewed and every direct and
inferred finding has a disposition. A passing UAT establishes a reviewed local-preview pilot
candidate, not release, production, enterprise, regulated-environment, or security-product
readiness.
