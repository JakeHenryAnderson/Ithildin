# Ithildin Guided Operator UAT Notes

Status: repo-owned copy of the original secret-free QA evidence; not approval, promotion, source
review, release evidence, or authorization to implement the observations below.

Source lineage: copied without substantive observation changes from the ignored runtime note at
`var/review-runs/operator-uat/2026-07-10T18-49-52Z/OPERATOR_UAT_NOTES.md` during pre-UAT
remediation so a fresh checkout can reproduce the product-direction evidence basis.

## Session metadata

- Date: 2026-07-10
- Commit: `6a357bd4bb7e7a7dc10abeb4bfa834addf64175c`
- Starting tree: clean
- Governed tool count: `24`
- Operator posture: first-time operator comprehension walkthrough
- Runtime posture: local preview
- Compose: unavailable because the Docker daemon socket was absent
- Fallback: existing host API entrypoint plus documented `make ui-dev`
- Preflight: passed with local-demo-token and missing-runtime-signing-key warnings
- Walkthrough disposition: stopped after the proposal/approval section because the operator was
  fatigued and the remaining failure pattern was sufficiently established

No credential value, raw prompt, file content, or sensitive host path is recorded here.

## What the operator understood

Without assistance, the operator recognized that the product concerns local AI governance, but
only after reaching the Agent Runs language near the lower part of the page. The operator quickly
identified that the interface was dense, implementation-shaped, jargon-heavy, and poorly aligned
with an alert-to-triage workflow.

With facilitator explanation, the operator understood:

- a policy as rules applied to a hypothetical tool request;
- the distinction between Policy Preview and Policy Impact;
- the distinction between a registered tool and permission to execute it;
- the intended umbrella model: one Ithildin application, Command Center as the operator cockpit,
  Workbench for active missions, and Gateway as the enforcement layer; and
- the candidate north star of a self-hostable governed agent-operations platform.

The operator did not independently understand the System Trust entries, proposal-to-approval
lifecycle, raw technical metadata, or the purpose of Policy Preview on the primary dashboard.

## Observed findings

These entries come directly from the human-led portion of the walkthrough.

| ID | Section | Expected behavior | What the operator actually saw or understood | Impact | Category |
| --- | --- | --- | --- | --- | --- |
| UAT-OBS-001 | Preparation | Facilitator-opened browser is visible to the operator. | The in-app browser was not visible; the operator manually opened the live URL in Chrome. | low | environment |
| UAT-OBS-002 | First impression | Product purpose is legible from the initial viewport. | Purpose was not apparent until Agent Runs language became visible lower on the page. | high | usability |
| UAT-OBS-003 | First impression | Governance terms identify their concrete object and consequence. | Terms such as Pending Approvals, Audit Integrity, and System Trust lacked referents. | high | terminology |
| UAT-OBS-004 | First impression | Primary tasks are reachable without scanning a long page. | The single-page layout required extensive scrolling and gave low-context data substantial space. | high | visual hierarchy |
| UAT-OBS-005 | First impression | Routine controls guide non-specialist operators. | Raw arguments and YAML assumed a highly technical operator. | medium | usability |
| UAT-OBS-006 | First impression | An alert leads to a clear triage path. | The operator could not identify an alert-to-triage workflow or safe next action. | high | workflow |
| UAT-OBS-007 | First impression | Help, documentation, settings, and display/accessibility controls are discoverable. | Those surfaces were absent or undiscoverable from the console. | medium | usability |
| UAT-OBS-008 | First impression | Integration and export boundaries are clear. | The operator immediately had questions about APIs, spreadsheets, notifications, and SIEM workflows. | question | product scope |
| UAT-OBS-009 | Authentication | The UI distinguishes missing authentication from preview restrictions. | Locked panels appeared attributable to smoke/preview mode rather than a missing token. | medium | terminology |
| UAT-OBS-010 | Authentication | Private-demo authentication is low-friction. | Obtaining the sample credential assumed repository-file knowledge and interrupted onboarding. | medium | environment |
| UAT-OBS-011 | Post-auth orientation | Authentication reveals a prioritized operator view. | Unlocking replaced sparse locked panels with a dense, undifferentiated information surface. | high | visual hierarchy |
| UAT-OBS-012 | Post-auth orientation | Each panel explains the question it answers and available next action. | Panel purpose and consequences remained implicit. | high | usability |
| UAT-OBS-013 | Agent Runs preview | Runs can be filtered by relevant operator dimensions. | Category, time-range, and identity-oriented filtering around `agent:mcp-local` was inadequate. | high | workflow |
| UAT-OBS-014 | System Trust | A new operator can understand the trust summary. | Essentially the entire panel was confusing or questionable to the operator. | high | usability |
| UAT-OBS-015 | System Trust | Fingerprints have an operator-visible purpose and comparison point. | Policy Hash and Audit Head appeared as unexplained hashes with no actionable meaning. | high | terminology |
| UAT-OBS-016 | System Trust | Identity readiness is explained in plain language. | `Principals 7/7 required` was incomprehensible without explanation. | high | terminology |
| UAT-OBS-017 | System Trust | Host and filesystem compatibility are distinguished. | `Filesystem: macOS` appeared to confuse operating system and filesystem. | medium | terminology |
| UAT-OBS-018 | System Trust | File-change limits are unambiguous. | Patch Limit sounded like operating-system or application update patching. | medium | terminology |
| UAT-OBS-019 | System Trust | Summary status leads to optional evidence. | Technical detail was primary instead of progressively disclosed. | high | visual hierarchy |
| UAT-OBS-020 | Registered Tools | Capabilities have recognizable human-facing names. | Machine identifiers such as `fs.list` made the browser UI feel CLI-shaped. | high | terminology |
| UAT-OBS-021 | Registered Tools | Risk communicates severity and consequence. | Risk mixed capability type with severity, and green network styling implied safety. | high | terminology |
| UAT-OBS-022 | Registered Tools | Network capability state is understandable. | The operator could not tell why HTTP differed from a read or whether it was currently usable. | high | terminology |
| UAT-OBS-023 | Registered Tools | Primary columns support routine operator decisions. | Category, version, manifest fingerprint, and repeated MCP status overwhelmed the snapshot. | medium | visual hierarchy |
| UAT-OBS-024 | Registered Tools | Browser UI is organized around operator tasks. | The table felt like a command inventory designed for technical users. | high | usability |
| UAT-OBS-025 | Registered Tools | Registration is clearly separate from effective permission. | The table did not show approval requirements, current availability, or effective access. | high | workflow |
| UAT-OBS-026 | Policy surfaces | Preview and Impact identify audience, inputs, and non-mutating outcome. | Their distinct purpose and intended user were not explained. | high | terminology |
| UAT-OBS-027 | Policy Impact | Engineering-only inputs are separated from routine operations. | Candidate YAML appeared as a normal dashboard task. | high | product scope |
| UAT-OBS-028 | Navigation | The page has a clear reading and task sequence. | Even the facilitator bypassed prominent policy panels while following the intended workflow. | high | navigation |
| UAT-OBS-029 | Policy Preview | Label describes the visible task. | The panel did not preview policy text; it constructed a hypothetical request. | high | terminology |
| UAT-OBS-030 | Policy Preview | Request inputs are explained. | Tool, Arguments, and Principal were not identified as inputs evaluated against hidden rules. | high | usability |
| UAT-OBS-031 | Policy Preview | Requesting identity is named plainly. | Principal was unexplained identity-model jargon. | high | terminology |
| UAT-OBS-032 | Policy Preview | Safe examples demonstrate allow, deny, and approval outcomes. | No guided examples or presets were present. | medium | usability |
| UAT-OBS-033 | Policy Preview | Primary-dashboard controls match routine operator needs. | The operator could not identify when they would use the panel. | high | workflow |
| UAT-OBS-034 | Policy Preview | Troubleshooting starts from a real request or event. | The operator had to manufacture an ungrounded request manually. | high | workflow |
| UAT-OBS-035 | Product boundary | UI explains what Ithildin governs and what remains external. | Agent prompts, agent configuration, and system-wide permissions were easy to assume but absent. | high | product scope |
| UAT-OBS-036 | Policy Preview | Decision preview is grounded in visible context. | The operator described it as testing one black box with another black box. | high | usability |
| UAT-OBS-037 | Policy Preview | Known identities and workspaces are available as guided choices. | Inputs remained raw and unassisted. | medium | usability |
| UAT-OBS-038 | Product integration | Policy preflight appears where it supports an operator task. | It made more sense as a Mission/Command Center preflight than a standalone dashboard control. | high | workflow |
| UAT-OBS-039 | Product integration | Ithildin explains the Command Center/Gateway relationship. | The product-role division was not visible in the current UI. | high | product scope |
| UAT-OBS-040 | Product lineage | Historical integration seams do not masquerade as final topology. | Cross-repository Mission Control artifacts made a temporary seam look like permanent architecture. | high | product scope |
| UAT-OBS-041 | Product architecture | Review Console reflects the intended Command Center cockpit. | The current UI exposed Gateway/reviewer internals rather than operator workflows. | high | product scope |
| UAT-OBS-042 | Product architecture | Front door begins with actionable operator scenarios. | Blocked actions, pending decisions, failed runs, and ready artifacts were not the navigation model. | high | workflow |
| UAT-OBS-043 | Policy preflight | Mission preflight is contextual and optional. | The standalone simulator lacked mission context. | medium | workflow |
| UAT-OBS-044 | Product direction | Current UI communicates the product north star. | The operator could not see one app for running, supervising, governing, and reviewing agent work. | high | product scope |
| UAT-OBS-045 | Product direction | Unified UX preserves internal authority distinctions. | The difference between one umbrella app and separate enforcement authority required explanation. | high | product scope |
| UAT-OBS-046 | Deployment direction | Deployment profiles have explicit trust contracts. | Local, server, and cloud hosting emerged as a future question, not a current equivalent capability. | question | product scope |
| UAT-OBS-047 | Product claims | Regulated-environment claims match current proof. | The direction was compelling, but current local preview does not substantiate production claims. | high | product scope |
| UAT-OBS-048 | Approval/proposal lists | Longer histories support grouping, columns, sorting, and filtering. | The lists did not scale for routine scanning. | high | workflow |
| UAT-OBS-049 | Approval/proposal detail | Selection and review-attention layout remain usable. | The list/detail area appeared visually unstable and competed for space. | high | visual hierarchy |
| UAT-OBS-050 | Approval/proposal detail | Selected content remains reachable in long lists. | A longer proposal history would make the selected `README.md` content difficult to locate. | high | usability |
| UAT-OBS-051 | Dashboard | Primary view prioritizes exceptions. | Raw information volume dominated instead of required action, unusual behavior, or failures. | high | visual hierarchy |
| UAT-OBS-052 | Dashboard | Activity is aggregated by operator-relevant dimensions. | The operator wanted agent, mission, time, tool, outcome, and workspace summaries with drill-down. | high | workflow |
| UAT-OBS-053 | Dashboard | Detailed evidence is retained without dominating. | Useful technical records were primary rather than intentionally sought during investigation. | high | visual hierarchy |
| UAT-OBS-054 | Personas | Routine operator, investigator, policy admin, and reviewer workflows are separated. | All personas appeared combined on one page. | high | product scope |
| UAT-OBS-055 | Navigation | Operators can locate and return to named sections. | No persistent navigation, section index, or location cue was available. | high | navigation |
| UAT-OBS-056 | Proposal lifecycle | Proposal and approval counts form a comprehensible lifecycle. | Two proposals beside no pending approvals appeared contradictory. | high | workflow |
| UAT-OBS-057 | Proposal lifecycle | Suggested file changes use plain language. | Patch Proposals was technical and ambiguous. | high | terminology |
| UAT-OBS-058 | Proposal lifecycle | Proposed items expose their state transition and next action. | The list did not explain who should advance a proposal or what happens next. | high | workflow |
| UAT-OBS-059 | Proposal rows | Every visible value has a label. | `default` was an unlabeled workspace identifier. | high | usability |
| UAT-OBS-060 | Proposal detail | Detail remains spatially connected to selection. | Selected detail was not clearly associated with the clicked row. | high | visual hierarchy |
| UAT-OBS-061 | Proposal detail | Proposal review and approval review are unmistakable. | The operator could not tell what was happening with the patch approval. | high | workflow |
| UAT-OBS-062 | Proposal detail | Concise human summary precedes raw change data. | The operator wanted a nearby inline or pop-up explanation associated with the selected item. | medium | usability |

## Inferred findings for the remaining walkthrough

The operator explicitly asked the facilitator to extrapolate rather than continue the tiring manual
walkthrough. The entries below are facilitator inferences grounded in the live UI and the repeated
human feedback pattern. They are not direct human observations and require later validation.

| ID | Section | Expected behavior | Inferred gap | Impact | Category |
| --- | --- | --- | --- | --- | --- |
| UAT-OBS-063 | Agent Runs | Runs are mission-centric and exception-first. | Principal/workspace/tool records are likely to remain too implementation-shaped without mission intent, model/client label, meaningful outcome, and next action. | high | workflow |
| UAT-OBS-064 | Agent Runs | Operators can narrow activity quickly. | Time range, identity, mission, tool, decision, status, workspace, and attention-state filters need a coherent filter model rather than raw field searching. | high | workflow |
| UAT-OBS-065 | Agent Runs | Repeated activity is summarized before individual events. | Counts, unusual-volume indicators, grouped outcomes, and artifact readiness should precede full timelines. Behavioral anomaly detection does not exist today and must not be implied. | high | visual hierarchy |
| UAT-OBS-066 | Audit | Integrity and actionable exceptions lead; raw events are drill-down. | The large Recent Audit Events table is likely to reproduce the same overload and missing-filter problem. | high | visual hierarchy |
| UAT-OBS-067 | Audit/export | Export and signing state are explained in operator language. | Hashes, signing warnings, JSONL, and signed-export controls are likely reviewer/forensics functions and should not dominate routine operations. | high | terminology |
| UAT-OBS-068 | ERG-005 artifact review | A ready artifact appears as a concrete operator task. | No genuinely discoverable trusted-artifact-promotion story was visible in the current UI; packet readiness is not UI integration. | high | product integration |
| UAT-OBS-069 | Overall comprehension | A first-time operator can explain purpose, boundary, and next action unaided. | The operator reached the correct product model only through extensive facilitator explanation. The current UI is not pilotable as a self-guided operator experience. | blocker | usability |
| UAT-OBS-070 | Overall pilotability | One bounded scenario demonstrates the product value end to end. | The interface needs a narrow mission-to-alert/approval-to-artifact-review story before broad dashboard completeness. | high | workflow |

## Environment findings versus product findings

Environment findings:

- The Docker CLI and Compose plugin were present, but the Docker daemon was not running.
- The in-app browser surface was not visible to the operator; manual Chrome navigation succeeded.
- The documented host development path supplied a usable fallback local UI/API session.

Product and UX findings:

- The interface is implementation-shaped, not operator-task-shaped.
- It lacks an exception-first cockpit, progressive disclosure, persistent navigation, plain-language
  terminology, and scalable list/detail patterns.
- It combines operator, investigator, policy-admin, and technical-review personas.
- It does not yet express the intended umbrella product: Command Center cockpit, Workbench, Gateway,
  and Evidence inside one Ithildin experience.

## Candidate product direction

Candidate north-star wording accepted during the session:

> Ithildin is a self-hostable governed agent-operations platform that can sit alongside LLM
> orchestration systems, mediate their tool use, surface operator decisions, and preserve reviewable
> evidence.

This is product-direction context, not a current capability or security claim. Local, server, cloud,
regulated-environment, orchestration, identity, sandbox, audit-custody, and infrastructure-as-code
work remain separate future decisions and review gates.

## Proposed follow-up tickets

These are proposals only. They were not created, staged, committed, or implemented.

1. **Define the pilot operator and golden scenario.** Use one bounded story: launch or observe a
   mission, receive one meaningful attention item, inspect why Ithildin allowed/denied/required
   approval, review one ready artifact, and close with evidence.
2. **Design the Command Center information architecture.** Separate Attention, Missions/Runs,
   Artifacts, Approvals, Evidence, and Administration; keep Gateway internals behind technical
   drill-down.
3. **Create a plain-language terminology and status contract.** Replace or explain every System
   Trust entry, tool label, risk label, identity term, proposal state, and audit/signing state with
   operator meaning and consequence.
4. **Build reusable operator list/detail patterns.** Add labeled columns, search/filter/sort,
   grouping, time range, stable selection, inline or adjacent detail, and empty-state explanations.
5. **Create an exception-first Attention surface.** Prioritize pending decisions, denials,
   failures, unusual volumes, stale evidence, and artifacts ready for review; retain complete detail
   for investigation without showing it by default.
6. **Rehome specialist controls.** Move Policy Preview/Impact, manifest/version evidence, raw audit
   events, hashes, and exports into contextual troubleshooting, administration, or reviewer flows.
7. **Prototype the bounded pilot shell without adding powers.** Use existing API data and 24-tool
   boundary only; do not add orchestration, cloud deployment, production identity, SIEM, sandbox,
   or security-product claims during the UX pilot.
8. **Run a second fresh-operator UAT.** Validate the golden scenario without facilitator coaching,
   then separately test investigator and policy-admin workflows.

## Closeout assessment

- Underlying information appears useful and worth retaining.
- The current Review Console is not yet a self-guided pilot cockpit.
- The dominant gap is product workflow and information architecture, not a request for more raw
  data or more governed powers.
- No observation in this note constitutes an approved requirement.
- No positive comment constitutes ERG-005 approval, trusted-host promotion approval, release
  readiness, enterprise readiness, or regulated-environment readiness.

## Operator disposition

The operator agreed that the full finding set should become tracked design and pilot work. The
operator specifically identified the candidate product-direction paragraph, their walkthrough
comments, and the recorded observations as collectively describing the work still required.

This disposition authorizes carrying the complete finding set into later backlog/design triage. It
does not select a specific implementation, approve capability expansion, authorize runtime or
schema changes, close any review lane, or make the current console pilot-ready.
