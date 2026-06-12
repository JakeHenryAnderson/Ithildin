# Agent Run Timeline Readiness Gate

Status: release-readiness gate. This gate does not add runtime behavior, tool manifests, executors,
policy rules, API endpoints, MCP tools, UI controls, sandbox controls, SIEM adapters, production
identity, runtime Postgres, hosted telemetry, shell, Docker, Kubernetes, browser automation, plugin
SDKs, arbitrary HTTP, or broad filesystem writes.

`make agent-run-timeline-readiness` validates that the Agent Run timeline surface remains a
read-only observability layer with source/evidence review packaging.

## Gate Composition

The gate validates:

- `agent-run-evidence-contract-check`;
- `agent-run-timeline-packet`;
- `operator-action-states-check`;
- `dashboard-evidence-checklist-check`;
- `AgentRunStore` source presence;
- `GET /runs` and `GET /runs/{run_id}` contract/API coverage;
- governed-call audit correlation with `run_id`;
- approval correlation evidence through safe metadata;
- review-console Agent Runs panel coverage;
- operator action states remain design-only vocabulary;
- dashboard evidence review expectations remain checklist-only;
- `no-new-powers-guardrail`;
- `tool-surface-invariant-gate`.

## Expected Result

- tool count remains `15`;
- Agent Runs remain admin-only and read-only;
- `/runs` and `/runs/{run_id}` do not create, mutate, replay, repair, approve, or execute actions;
- timeline evidence remains secret-free;
- run-control verbs such as pause, abort, kill, repair, replay, and disable remain design-only until
  separately reviewed;
- no new powerful tool classes are introduced.

Passing this gate does not prove sandboxing, process supervision, SIEM-grade custody, production
security control, production identity, or activity outside Ithildin-mediated tools.
