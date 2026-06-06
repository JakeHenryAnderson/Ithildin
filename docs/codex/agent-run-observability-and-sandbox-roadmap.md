# Agent Run Observability and Sandbox Boundary Roadmap

Status: strategic roadmap and implementation seed. This document does not add runtime behavior,
tool manifests, executors, policy rules, MCP transport, API endpoints, UI behavior, sandbox
orchestration, SIEM integration, production identity, runtime Postgres, hosted telemetry, shell,
Docker, Kubernetes, browser automation, plugin SDKs, or broad filesystem powers.

This roadmap captures the intended long-term product direction: Ithildin as the governed control
plane and evidence layer between AI agents and sensitive operating environments. The current local
preview remains a mediation layer, not a sandbox, SIEM, compliance product, production identity
system, hosted MCP service, or custody-grade evidence system.

## Product Direction

The desired product shape is a governed AI workbench:

```text
local or enterprise model / agent
  -> MCP client or agent runner
  -> Ithildin governed control plane
  -> policy, approvals, run timeline, audit evidence
  -> scoped tools and operator-managed sandbox/workspace
  -> reviewed outputs and exportable evidence
```

The useful metaphor is a lab glovebox. The agent can operate, but the operator sees the controls,
policy decisions, denials, approvals, and evidence. Ithildin should be the panel and evidence
recorder, not the claim that the host or sandbox is magically safe.

## Boundary Statement

Ithildin may grow toward regulated-environment support only by helping operators enforce and
evidence their own controls. It should not claim that it makes an agent HIPAA, GLBA, SOX, GDPR, or
other regulatory regimes compliant by itself.

Acceptable future wording:

- supports least-privilege tool mediation;
- supports approval-gated actions;
- supports local tamper-evident and locally signed evidence;
- supports policy and evidence workflows that can map to organizational controls;
- supports incident reconstruction for mediated agent actions.

Forbidden or premature wording:

- HIPAA compliant by default;
- SIEM-grade custody;
- production security control;
- kernel sandbox;
- prevents model compromise;
- immutable or notarized audit;
- production identity or enterprise RBAC;
- hosted control plane;
- safely runs arbitrary tools.

## Core Design Requirements

### 1. Agent Run Model

Introduce a first-class run/session object before deeper dashboard or SIEM work:

- run ID;
- agent/client principal;
- model/client label;
- workspace ID;
- optional sandbox ID;
- policy version/hash at start;
- manifest lock hash;
- started, paused, resumed, stopped, and completed timestamps;
- correlation IDs for tool calls, approvals, audit events, redaction summaries, and exports;
- final status such as `completed`, `paused`, `aborted`, `recovery_required`, or `failed_closed`.

The run model should collect existing evidence into a coherent story without changing tool powers.

### 2. Live Timeline Dashboard

The review console should evolve into an operations timeline:

- tool request received;
- schema validation result;
- principal/workspace resolution;
- policy decision and matched rules;
- executor start/completion/failure;
- approval requested, approved, denied, expired, or consumed;
- audit head updates;
- warnings for dev-token mode, unsupported filesystem profile, stale audit, or recovery diagnostics;
- signed export availability.

The first milestone should be read-only observability. Pause/kill controls can be planned later and
must be explicit state transitions, not hidden process control.
The dashboard evidence review target is tracked in
[dashboard-evidence-review-checklist.md](dashboard-evidence-review-checklist.md) and checked with
`make dashboard-evidence-checklist-check`.

### 3. Sandbox and Workspace Boundary Contract

Ithildin should document a sandbox boundary without becoming a Docker/Kubernetes controller.

Initial contract:

- an operator or external platform starts the sandbox/container/VM;
- Ithildin does not mount the Docker socket;
- Ithildin does not run shell commands as a governed tool;
- the sandbox exposes a named workspace root or mounted project directory;
- all Ithildin tools continue to operate through workspace registry, manifests, policy, approvals,
  and audit;
- sandbox lifecycle evidence is recorded only when supplied by trusted local configuration or a
  later reviewed integration.

This preserves the current posture: Ithildin governs mediated actions; it is not itself a kernel
sandbox.

### 4. Stable Evidence Schema and SIEM-Shaped Export

Before SIEM adapters, define stable event contracts for:

- run lifecycle;
- tool call lifecycle;
- policy decision;
- approval lifecycle;
- executor result;
- audit verification;
- signed export;
- recovery diagnostics;
- redaction summary;
- sandbox/workspace posture.

Adapters can come later. The first version should be JSONL and signed-export friendly. Future
SIEM-shaped output may map events to severity, category, correlation ID, principal, resource,
decision, and evidence hash, but must not export prompts, secrets, file contents, diffs, response
bodies, or package/script/dependency names unless separately reviewed.

### 5. Policy Packs and Control Mapping

Regulated-environment value comes from mapping agent behavior to control objectives:

- least privilege;
- approval-required writes;
- segregation of duties;
- data export restrictions;
- restricted network destinations;
- sensitive-resource labeling;
- retention and evidence export;
- denied destructive actions;
- incident reconstruction.

These should be policy/control mappings, not compliance claims. A future policy pack may say
“supports this control objective” only if tests and evidence prove the mapping.
The design-only mapping support doc is tracked in
[control-mapping-design.md](control-mapping-design.md) and checked with
`make control-mapping-design-check`.

### 6. Data Classification

Workspaces and resources should eventually carry labels such as:

- public;
- internal;
- confidential;
- PII;
- PHI;
- client data;
- regulated financial data;
- secrets-adjacent.

Data labels should feed policy decisions and dashboard warnings. The first pass can be trusted local
configuration only; UI editing, discovery, and automatic classification are separate future tasks.
The design-only proposal is tracked in
[data-classification-design.md](data-classification-design.md) and checked with
`make data-classification-design-check`.

### 7. Incident Reconstruction

Operators should be able to answer:

- what did this agent try to do;
- what did it see through Ithildin-mediated tools;
- what did policy allow or deny;
- what did a human approve;
- what changed;
- which audit head and signed export bind the evidence;
- what recovery diagnostics exist.

This requires correlation and stable evidence more than more tool powers.
The operator/reviewer guide is tracked in
[incident-reconstruction-guide.md](incident-reconstruction-guide.md) and checked with
`make incident-reconstruction-check`.

### 8. Pause, Disable, and Kill-Switch Semantics

Future controls should be defined carefully:
The design-only vocabulary is tracked in
[operator-action-states-design.md](operator-action-states-design.md) and checked with
`make operator-action-states-check`.

- pause a run;
- disable a principal;
- disable a workspace;
- block a tool;
- require manual approval for all future actions in a run;
- export evidence immediately.

These controls should affect Ithildin-mediated actions. They should not claim to stop arbitrary host
processes, model clients, containers, or OS activity outside Ithildin.

## Implementation Waves

### Wave A: Documentation and Contracts

- Record this roadmap.
- Define run/session event contracts.
- Link the secret-free [Agent Run Evidence Contract](agent-run-evidence-contract.md).
- Link the design-only [Agent Run Evidence Export Design](agent-run-evidence-export-design.md)
  without adding export endpoints, SIEM adapters, or runtime behavior.
- Link the operator-managed [Sandbox Workspace Boundary Contract](sandbox-workspace-boundary-contract.md).
- Link the future [SIEM-Shaped Evidence Design](siem-shaped-evidence-design.md) without adapters.
- Link the trusted local [Data Classification Design](data-classification-design.md) without
  runtime classification behavior.
- Link the [Control Mapping Design](control-mapping-design.md) without compliance claims.
- Link the [Incident Reconstruction Guide](incident-reconstruction-guide.md) for mediated actions
  only.
- Add gates that prevent these docs from becoming production/security claims.

### Wave B: Read-Only Run Model

- Add run records to SQLite.
- Create run IDs for API/MCP governed calls.
- Attach run IDs to audit metadata.
- Add admin read APIs for run list/detail.
- Do not add pause/kill mutation yet.

### Wave C: Timeline Dashboard

- Add a run timeline panel to the review console.
- Group tool calls, policy decisions, approvals, audit events, and diagnostics by run.
- Add filters for principal, workspace, tool, decision, and status.
- Keep this read-only at first.

### Wave D: Operator-Managed Sandbox Demo

- Document how to start a local Linux container/VM outside Ithildin.
- Mount or copy a demo workspace into that sandbox.
- Connect a small local model or MCP client through Ithildin.
- Show the run timeline as the model interacts with the governed workspace.
- Preserve no Docker socket, no shell governed tool, no Kubernetes assets, and no sandbox control
  claims.

### Wave E: SIEM-Shaped Evidence Export

- Add an event export schema that is stable and secret-free.
- Include run IDs, correlation IDs, event categories, severities, resources, policy evidence, and
  audit heads.
- Keep adapters optional and local.
- Do not claim SIEM-grade custody or compliance.

### Wave F: Control Mapping and Classification

- Add trusted local classification labels.
- Add policy fixture coverage for label-based allow/deny/approval decisions.
- Add docs mapping policy fixtures to control objectives.
- Keep compliance language scoped to “supports control evidence.”

## Near-Term Recommended Sprint Sequence

1. Finish source-review disposition for `project.manifest.summary` locally.
2. Add an agent-run/session contract document and schema proposal.
3. Add read-only run records and correlation IDs.
4. Add a minimal run timeline API and review console panel.
5. Add an operator-managed sandbox demo guide.
6. Add SIEM-shaped evidence export design.
7. Add data-classification design and policy fixtures.

Items 1 through 4 are now implemented for local-preview observability and are documented in
[agent-run-model-contract.md](agent-run-model-contract.md). They do not add sandbox/process control
or SIEM/compliance claims. The review console now includes a read-only Agent Run operations
dashboard with bounded filters, query summaries, timeline evidence, warning chips, and run evidence
export download. That surface is checked by
[agent-run-operations-readiness-gate.md](agent-run-operations-readiness-gate.md) with
`make agent-run-operations-readiness`.
The future run-level export bundle shape is documented in
[agent-run-evidence-export-design.md](agent-run-evidence-export-design.md) and checked with
`make agent-run-evidence-export-check`; it remains design-only.
The future admin-only export endpoint planning packet is documented in
[agent-run-evidence-export-implementation-plan.md](agent-run-evidence-export-implementation-plan.md)
and checked with `make agent-run-evidence-export-plan-check`; it is retained as implementation
lineage.
The bounded admin-only read endpoint is documented in
[agent-run-evidence-export-implementation.md](agent-run-evidence-export-implementation.md) and
checked with `make agent-run-evidence-export-implementation-gate`; it exports one secret-free run
evidence bundle without SIEM adapters, sandbox controls, or new tool powers.
The combined Agent Run evidence readiness gate is documented in
[agent-run-evidence-readiness-gate.md](agent-run-evidence-readiness-gate.md) and checked with
`make agent-run-evidence-readiness`.

## Stop Conditions

Stop and request internal xhigh or external/human review if:

- a sprint would add shell, Docker socket, Kubernetes, browser automation, arbitrary HTTP, broad
  filesystem writes, production identity, runtime Postgres, hosted telemetry, remote MCP, or plugin
  SDK work;
- a document implies compliance, sandboxing, SIEM-grade custody, or production security;
- run controls would claim to stop processes outside Ithildin-mediated actions;
- SIEM/export work would expose prompts, secrets, file contents, diffs, response bodies, or other
  sensitive payloads;
- the sandbox boundary requires Ithildin to control container/VM lifecycle directly.

## Strategic Takeaway

The commercial thesis is plausible: smaller local and domain models will need useful tools, but raw
tool access is not acceptable in sensitive environments. Ithildin’s defensible role is governed
mediation, evidence, approval, and observability around those tools. The next product leap is not
more power; it is making each agent run visible, attributable, bounded, and reconstructable.
