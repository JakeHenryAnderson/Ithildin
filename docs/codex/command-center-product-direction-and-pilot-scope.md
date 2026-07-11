# Command Center Product Direction and Pilot Scope

Status: approved backlog scope and design direction; implementation choices remain unapproved.

This artifact converts the 2026-07-10 guided operator UAT into a bounded product and pilot charter.
It does not add application behavior, governed tools, schemas, manifests, APIs, policy semantics,
approval behavior, audit behavior, orchestration, deployment support, or runtime authority.

## Evidence Basis

The primary human evidence is the repo-owned
[initial operator UAT evidence](command-center-initial-operator-uat-evidence.md), copied from the
original ignored runtime note and recorded against commit
`6a357bd4bb7e7a7dc10abeb4bfa834addf64175c` with governed tool count `24`.

Keep its evidence classes separate:

| Evidence class | IDs or source | Planning use | What it does not prove |
| --- | --- | --- | --- |
| Direct operator observations | `UAT-OBS-001` through `UAT-OBS-062` | Approved for inclusion in product/UX backlog scope. | A particular design, implementation, or release is approved. |
| Facilitator inferences | `UAT-OBS-063` through `UAT-OBS-070` | Approved for tracked design work, visibly labeled as inferred, and required to be retested. | The fresh operator has validated the inferred gap. |
| Product-direction discussion | Candidate wording and topology from the UAT note | Direction for coherent product design and pilot framing. | Current self-hosting, regulated-environment, cloud, or security capability. |
| Operator disposition | UAT closeout authorization | Authorizes durable planning and backlog inclusion for the complete finding set. | Runtime work, authority transfer, schema/API change, approval, promotion, closure, or release. |

The UAT stopped after the proposal/approval section because the operator was fatigued. The eight
inferred findings are therefore hypotheses until the second fresh-operator UAT described in the
[golden pilot scenario](command-center-golden-pilot-scenario.md).

## Candidate Product Direction

The accepted candidate direction is:

> Ithildin is a self-hostable governed agent-operations platform that can sit alongside LLM
> orchestration systems, mediate their tool use, surface operator decisions, and preserve reviewable
> evidence.

This is a north-star statement, not a current capability or security claim. Current proof remains a
local-preview governed MCP/tool gateway. `Self-hostable` is a design direction pending explicit
deployment-profile trust contracts and validation. It does not currently mean production-ready,
cloud-equivalent, regulated-environment-ready, remotely hosted, or secure against host compromise.

## Product Topology

- **Ithildin** is the umbrella application and product experience.
- **Ithildin Command Center** is the exception-first operator cockpit.
- **Workbench** is the active mission, run, artifact, and evidence workspace inside Command Center.
- **Ithildin Gateway** remains the enforcement point for schema validation, policy evaluation,
  approval binding, governed execution, redaction, and audit recording.
- **Evidence** preserves reviewable records and exports for Ithildin-mediated activity.
- External agents and orchestration systems remain external. Ithildin does not become their prompt
  editor, model configuration surface, lifecycle manager, or process supervisor through this pilot.

One umbrella application must not imply shared or bypassable enforcement authority. Command Center
may display state, prepare an operator request, and submit an existing reviewed action through an
existing API. It must not independently decide policy, create or complete approvals, execute tools,
mutate audit evidence, or promote artifacts.

## Pilot Outcome

The pilot tests one proposition:

> A first-time routine operator can notice one important item, understand the mediated mission and
> Ithildin decision behind it, review one ready artifact, and finish with understandable evidence
> without facilitator coaching or default exposure to raw technical records.

The pilot uses one existing local-preview mission story and the existing 24-tool boundary. It
observes a mediated run; it does not add mission creation, agent launch, pause, abort, scheduling,
or orchestration.

## Pilot Scope

In scope:

- a purpose-led and authentication-aware Command Center entry;
- persistent navigation for Attention, Missions / Agent Runs, Artifacts, Approvals, Evidence, and
  Administration;
- an exception-first Attention item tied to one mission and one required operator action;
- a mission Workbench explaining the request, identity, workspace, tool, outcome, policy reason,
  and next action in plain language;
- a proposal, approval, application, artifact, and evidence lifecycle that does not collapse
  distinct states;
- one ready artifact review using safe human-facing metadata and retained technical identifiers;
- an understandable evidence closeout with audit integrity, signing, and export limitations;
- progressive disclosure for hashes, manifests, raw audit events, YAML, and exports;
- separate routine-operator, investigator, policy-administrator, and technical-reviewer routes;
- a second uncoached UAT with a fresh operator.

Out of scope:

- new governed tools or changes to the current count of `24`;
- starting or controlling agents, models, shells, browsers, containers, VMs, or jobs;
- cloud deployment, production identity, remote MCP, hosted telemetry, runtime Postgres, SIEM
  adapters, Terraform, sandbox orchestration, or compliance automation;
- policy authoring as a routine dashboard task;
- changes to policy, approval, audit, signing, promotion, schema, manifest, API, or executor
  semantics;
- trusted-host publishing beyond already reviewed staging-only behavior;
- public claims that Ithildin is a secure control plane, production security product, compliant
  system, or regulated-environment solution;
- a broad visual redesign unrelated to the golden scenario.

## Experience Principles

1. Lead with required action and operational consequence, then offer evidence.
2. Make the first viewport answer what Ithildin is, what needs attention, and what the operator can
   do next.
3. Use mission intent as the organizing context for Agent Runs, artifacts, approvals, and evidence.
4. Show human-facing names first while retaining stable machine IDs for search, APIs, logs, and
   technical drill-down.
5. Separate capability class, policy outcome, approval requirement, and operational severity.
6. Put policy preflight in the context of a real request, event, or mission troubleshooting path.
7. Preserve complete technical evidence; reduce overload through summaries and progressive
   disclosure rather than deletion.
8. Keep persona-specific tasks distinct without hiding cross-links needed for investigation.
9. Treat every generated or exported record according to what it proves and what it does not prove.
10. Treat ERG-005 packet readiness as supporting evidence, not proof of Command Center
    discoverability or pilot usability.

## Operator Roles

| Role | Primary question | Primary route | Not a default task |
| --- | --- | --- | --- |
| Routine operator | What needs my attention, why, and what happens next? | Attention and mission Workbench | Raw YAML, manifests, full audit events, or policy simulation. |
| Investigator | What happened across this mission or run, and how is it correlated? | Missions / Agent Runs and Evidence | Policy administration or approval authority by implication. |
| Policy administrator | Which existing rule caused this outcome, and how would a candidate change differ? | Contextual policy troubleshooting under Administration | A generic simulator on the primary dashboard. |
| Technical reviewer | Can I reconstruct and verify the evidence and its limitations? | Evidence technical detail and exports | Routine triage or operational authority. |

The pilot may use one local preview credential and existing role behavior. Role-specific information
architecture does not authorize new identity or RBAC semantics.

## Planning Decisions and Open Choices

Approved planning decisions:

- include all 62 direct observations in backlog coverage;
- track all 8 inferred findings and retest them as inferred;
- use the umbrella/Command Center/Workbench/Gateway topology;
- organize the cockpit around the six named information areas;
- use one narrow mission-to-attention-to-artifact-to-evidence scenario;
- preserve technical evidence behind progressive disclosure;
- require an uncoached second UAT before calling the pilot self-guided.

Implementation choices still requiring review:

- exact visual layout, components, iconography, color, and responsive behavior;
- whether a displayed summary is computed in the UI or supplied by an existing API response;
- which existing demo fixture best supplies the golden scenario without runtime or API changes;
- exact notification channel, if any; no external notification integration is assumed;
- exact role-switching or view-selection mechanism; no new authorization semantics are assumed;
- any need for a new field, endpoint, state, or mutation. Such a need stops the pilot ticket and
  returns it to product/architecture review.

## Pilot Exit Criteria

The product/UX pilot is reviewable when:

- the golden scenario is usable end to end with existing reviewed powers and authority;
- a fresh operator completes it without coaching and passes the comprehension checks;
- direct and inferred UAT findings are mapped to tickets and validation evidence;
- machine identifiers and complete technical evidence remain reachable;
- the UI never implies that Command Center, Workbench, a fixture, a generated packet, or a test is
  the source of policy, approval, execution, promotion, or audit truth;
- current limitations and local-preview warnings remain visible and understandable;
- focused UI checks and the repository's proportional gates pass.

Passing those criteria makes the pilot a reviewed candidate only. It does not establish release,
production, enterprise, regulated-environment, or security-product readiness.

## Stop Conditions

Stop implementation planning and request a new architecture or capability decision if the pilot
requires a new governed power, authority transfer, schema/API change, policy or approval semantic
change, audit mutation, new deployment claim, new identity model, orchestration, sandbox/VM control,
SIEM behavior, or a regulated/security claim.
