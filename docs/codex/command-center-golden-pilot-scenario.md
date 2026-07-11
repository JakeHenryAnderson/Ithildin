# Command Center Golden Pilot Scenario

Status: design and acceptance specification; not implementation, UAT completion, or release
evidence.

## Scenario: Review the Hello World Mission

A first-time routine operator opens Ithildin Command Center to observe a local-preview mediated
mission. One proposed artifact action requires attention. The operator understands why Ithildin
required approval, reviews the resulting ready artifact, and finishes with a plain-language evidence
summary.

The scenario observes an existing Agent Run and uses existing approval, artifact, audit, and export
behavior. Ithildin does not start, schedule, pause, abort, or otherwise orchestrate the agent. The
fixture name `Hello World` is human-facing presentation context, not a new runtime mission object or
schema field.

## Intended Learning

At the end, the operator can explain:

- Ithildin mediates an external agent's tool use; it does not configure or run the agent;
- Command Center is the cockpit and Workbench is the mission context;
- Gateway remains the source of policy, approval, execution, and audit truth;
- the selected request required a one-time approval because an existing policy requires approval
  for that bounded write or staging action;
- a registered tool is not automatically permitted;
- `ready for review` does not mean approved, promoted, published, or release-ready;
- the evidence describes Ithildin-mediated activity and has explicit signing/export limitations.

## Fixture and Data Preconditions

Before implementation, the ticket owner must demonstrate that the scenario can be rendered from
existing reviewed records and APIs. The candidate fixture may reuse the existing Hello World
sandbox artifact and staging-only ERG-005 evidence, but the UI must not treat a generated packet as
live state.

Required existing data:

- one correlated Agent Run with safe principal, workspace, tool, decision, status, time, and request
  identifiers;
- one approval-required artifact action with proposal and approval records kept distinct;
- one bounded artifact label, digest, source/destination labels, and recorded application result;
- correlated audit events and an evidence export or packet reference;
- explicit local-preview, audit-integrity, signing, and export warning states.

If any required display needs a new field, endpoint, state, mutation, policy rule, approval behavior,
audit behavior, or governed tool, stop. Return to product/architecture review rather than silently
expanding this scenario.

## Starting State

- Local UAT services have been started through the existing documented path.
- A browser visible to the operator is already open at the Command Center URL.
- The local-preview credential or an authenticated session is available through the documented
  operator setup; the task does not require repository-file exploration.
- Exactly one seeded `Hello World` mission story is easy to identify.
- Exactly one meaningful Attention item is present: an artifact action requires operator review.
- No unrelated warning or queue item visually outranks the scenario item unless it is genuinely
  more severe.

## Stage Contract

| Stage | Operator sees | Operator action | Ithildin explanation | Authoritative result/evidence |
| --- | --- | --- | --- | --- |
| 1. Orient | Product purpose, local-preview posture, authentication state, six-area navigation, and one Attention item. | Open the Attention item. | Ithildin mediates external agent tool use and records reviewable evidence. | Authentication and system posture come from current local state. |
| 2. Enter Workbench | `Hello World` mission context, requesting identity, workspace, latest outcome, and the required action. | Open the related decision. | Workbench is a view over the mission's mediated activity; it did not start the agent. | Existing run and audit correlation identify the request. |
| 3. Understand the decision | A plain-language request summary, `Approval required`, policy reason, one-time scope, expiry, and consequence. | Explain the decision aloud, then use the existing approval action if the test script calls for it. | The tool is registered, but this request is not executable until the existing approval workflow authorizes the exact bounded action. | Existing policy and approval records remain authoritative. |
| 4. Follow the lifecycle | Proposal, approval, application, and artifact states appear as distinct linked steps. | Follow the artifact link after the recorded action succeeds. | Approval authorizes a bounded request; Gateway performs and audits the action. Command Center does not execute it. | Existing proposal, approval, executor/diagnostic, and audit records provide state. |
| 5. Review the artifact | Human-facing artifact label, mission, safe summary, readiness, source/destination labels, digest match status, and limitations. | Mark the review task complete only through an existing reviewed action, or record a UAT acknowledgement if no such action exists. | `Ready for review` describes the review task. It does not assert promotion, publication, release, or trust. | Existing artifact and staging-only evidence; no broader host promotion. |
| 6. Finish with evidence | A concise closeout: request, decision, human action, application result, artifact, audit integrity, signing status, export status, and warnings. | Open technical detail only if desired; create an export only through the existing read-only export action. | Evidence covers Ithildin-mediated activity. Local verification/signing is not notarization, hosted custody, or proof of external activity. | Existing run evidence export, audit verification, signing, and packet references. |

If the current runtime does not expose a reviewed mutation for marking an artifact review complete,
the pilot records task completion only in the UAT observation sheet. It must not add or counterfeit a
runtime state to make the walkthrough appear complete.

## Decision Explanation Example

The primary explanation should follow this pattern:

> The agent requested permission to create the Hello World artifact in the configured mission
> workspace. Ithildin requires a one-time approval for this write. Nothing was written before the
> approval. If approved, Ithildin Gateway will apply only the reviewed request and record the result.

Technical detail retains the machine tool name, request ID, approval ID, policy fingerprint,
manifest fingerprint, resource evidence, and relevant audit event IDs. The primary explanation must
not invent a policy rationale that is absent from the authoritative decision record.

## Acceptance Criteria

### Orientation and navigation

- The operator identifies Ithildin's purpose from the first viewport within 30 seconds.
- The operator distinguishes missing authentication from local-preview or smoke restrictions.
- Attention, Missions / Agent Runs, Artifacts, Approvals, Evidence, and Administration are persistent
  and locatable without scrolling a single long dashboard.
- Help and the terminology contract are reachable from the shell.

### Triage and mission context

- The operator locates the intended Attention item within 60 seconds.
- The item states what requires action, why it matters, the mission, age, state, and safe next step.
- Workbench keeps the selected mission, attention item, decision, artifact, and evidence spatially
  and navigationally connected.
- Human-facing labels lead; stable machine IDs remain searchable and copyable in technical detail.

### Governance comprehension

- Without coaching, the operator correctly identifies the requesting identity, workspace, tool
  purpose, decision, policy reason, approval scope, and consequence.
- The operator can say that registration is not permission.
- The operator can say that Command Center did not make the policy decision or execute the action.
- Raw YAML, hashes, manifests, and audit rows are not required to complete the routine path.

### Artifact and evidence

- Proposal, approval, application, artifact, review, and evidence states are not collapsed.
- The artifact review shows an understandable summary before raw content, diff, digest, or path.
- `Ready for review` is not styled or worded as approved, promoted, published, or release-ready.
- The closeout shows audit integrity, signing, and export as separate statuses with limitations.
- Complete technical evidence remains reachable through drill-down.

### Accessibility and failure handling

- State, risk, and decision are not communicated through color alone.
- Keyboard focus and selection remain stable across list/detail navigation.
- Empty, loading, authentication-required, unavailable, expired, denied, and failed states explain
  what happened and the next safe action.
- No UI action bypasses existing policy, approval, execution, artifact, or audit authority.

## Second Fresh-Operator UAT Gate

The second UAT is required before the golden pilot may be described as self-guided.

### Participant and facilitator rules

- Use an operator who did not participate in the first UAT and has not read these design artifacts.
- Provide only the task card below and normal product-visible help.
- Do not explain Ithildin vocabulary, page purpose, topology, or next steps during the timed task.
- The facilitator may resolve only an environment failure that prevents the visible product from
  loading. Record the intervention and restart the timed task if it could have taught the workflow.
- Record direct observations separately from facilitator interpretation.

### Task card

> Open Ithildin. Find what needs your attention for the Hello World mission. Determine what the
> agent requested, what Ithildin decided and why, review the artifact when it is ready, and show the
> evidence you would hand to a technical reviewer. Stop when you believe the task is complete.

### Environment preflight

- Confirm the browser is visible to the operator before timing starts.
- Confirm the URL is reachable and the intended seeded scenario exists.
- Confirm the credential path is available through the documented operator experience.
- Confirm local-preview and signing warnings match actual runtime state.
- Do not coach around a broken environment; label environment failures separately.

### Pass gate

The UAT passes only if the operator:

- completes all six scenario stages without workflow or vocabulary coaching;
- completes the task in 12 minutes or less, excluding recorded environment recovery;
- makes no unsafe or authority-confused action;
- answers at least 7 of 8 comprehension questions correctly;
- rates confidence in the next action at least 4 on a 5-point scale;
- does not need raw YAML, manifests, hashes, or audit rows for routine completion;
- can still locate technical evidence when asked;
- validates or refutes each inferred finding `UAT-OBS-063` through `UAT-OBS-070` with a new direct
  observation.

### Comprehension questions

1. What was the mission trying to produce?
2. Which identity and workspace made the request?
3. What did Ithildin decide?
4. Why did the request need approval?
5. Did Command Center execute the tool?
6. What does `ready for review` mean here?
7. What does the audit-integrity status establish?
8. What does the evidence not prove?

### Required UAT record

Record participant posture, commit, tool count, environment, start/end time, task outcome, direct
observations, errors, interventions, comprehension answers, confidence score, the disposition of
each inferred finding, and links to screenshots or secret-free evidence. Label the record as QA
evidence only. It is not approval, promotion, source review, release evidence, or authorization for
scope expansion.

## Failure and Stop Conditions

Fail the UAT rather than coach through it if the operator cannot locate the next action, cannot
explain the policy consequence, confuses proposal with approval, mistakes readiness for promotion,
or cannot distinguish Command Center from Gateway authority.

Stop the implementation lane if completing the scenario requires new governed powers, mission
orchestration, schema/API changes, new approval or audit semantics, broader artifact promotion,
production identity, cloud behavior, SIEM behavior, sandbox control, or regulated/security claims.
