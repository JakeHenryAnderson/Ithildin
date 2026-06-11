# Operator Workbench Readiness Gate

Status: release-readiness gate.

The operator workbench is Ithildin's local-preview control-plane view for a mediated agent
workspace. It combines the existing System Trust panel, registered tools, approval evidence, Agent
Run operations dashboard, audit status, live-demo artifacts, operator-managed sandbox/workspace
posture, and read-only evidence export. It does not add run controls, sandbox orchestration, SIEM
adapters, production identity, runtime Postgres, hosted telemetry, remote MCP, shell, Docker,
Kubernetes, browser automation, arbitrary HTTP, broad filesystem writes, plugin SDK work, or new
governed tool powers.

## Operator Goal

The workbench should let a local operator answer four questions without reading every review doc:

1. What is the current trust posture?
2. What did the mediated agent do?
3. Which approvals, policy decisions, audit events, and diagnostics correlate with the run?
4. Which local evidence artifacts can be exported or handed to a reviewer?

## Current Surfaces

- `GET /runs` and the review-console Agent Runs panel provide read-only filters and summaries.
- The Agent Runs panel starts with a compact `Demo Path` strip so an operator can follow the
  intended read-only flow: filter runs, inspect evidence, and export a bundle.
- The selected run view groups existing timeline rows into evidence types, statuses, decisions, and
  correlation counts before the raw table, making the demo screen understandable without raw JSON.
- `GET /runs/{run_id}` reconstructs the selected run timeline from audit events.
- `GET /runs/{run_id}/evidence-export` exports a bounded, read-only run evidence bundle.
- `make operator-sandbox-demo-packet` records the operator-managed sandbox/workspace story.
- `make agent-run-correlation-packet` records the run-to-tool/audit/approval correlation story.
- `make demo-readiness-summary` records ready, missing, optional/manual, deferred, and recommended
  next-command status for the local demo handoff.
- `make live-demo-status`, `make live-demo-smoke`, `make live-demo-evidence-summary`, and
  `make live-demo-packet` record live-demo handoff evidence.
- `make demo-workbench-smoke` records a deterministic operator-flow smoke transcript.
- `make workbench-evidence-packet` packages the operator workbench story into one focused review
  packet.

## Demo Wrapper

`make demo-workbench` is a local evidence wrapper. It runs only existing read-only or ignored-output
demo evidence commands:

- `make live-demo-preflight`;
- `make live-demo-status`;
- `make live-demo-smoke`;
- `make live-demo-evidence-summary`;
- `make demo-readiness-summary`;
- `make demo-workbench-smoke`;
- `make operator-sandbox-demo-packet`;
- `make agent-run-correlation-packet`;
- `make workbench-evidence-packet`.

It does not start services, stop services, mutate governed workspaces, call governed tools, approve
actions, repair diagnostics, or manage containers.

## Evidence Bundle

`make workbench-evidence-packet` writes ignored artifacts under
`var/review-packets/v3/operator-workbench/`:

- workbench index;
- top-level `WORKBENCH_DEMO_INDEX.md`;
- top-level `DEMO_READINESS_SUMMARY.md`;
- top-level `WORKBENCH_DEMO_SMOKE.md`;
- `07_WORKBENCH_DEMO_STORY.md` happy-path narrative;
- reviewer prompt;
- bundled operator docs;
- command evidence;
- artifact pointers;
- artifact hashes.

`WORKBENCH_DEMO_INDEX.md` is the first file to open. Its newest reading order is:
`WORKBENCH_DEMO_INDEX.md`, `DEMO_READINESS_SUMMARY.md`, `WORKBENCH_DEMO_SMOKE.md`, the workbench
packet boundary, the live-demo packet, and the run evidence/export docs. `07_WORKBENCH_DEMO_STORY.md`
gives the happy path from preflight through cleanup. The run evidence export includes a safe
`summary` object with principal, workspace, session, status, tools used, decision counts, approval
count, patch diagnostic count, audit event count, warning count, policy hash, and manifest-lock hash.

The packet points to existing live-demo, operator sandbox, Agent Run correlation, signed evidence,
negative transcript, and consolidated review artifacts. It is a reviewer convenience artifact, not
notarization, SIEM custody, compliance automation, production security, or proof of activity outside
Ithildin-mediated actions.

## Readiness Gate

`make workbench-readiness` validates:

- the workbench readiness doc is in the review docs and docs site;
- README and reproduction-map command lists mention the workbench commands;
- `make demo-workbench` and `make workbench-evidence-packet` are wired;
- `make demo-readiness-summary`, `make demo-workbench-smoke`, `WORKBENCH_DEMO_INDEX.md`,
  `DEMO_READINESS_SUMMARY.md`, `07_WORKBENCH_DEMO_STORY.md`, and `WORKBENCH_DEMO_SMOKE.md` are
  wired;
- release-check includes the workbench readiness gate;
- tool count remains `13`;
- no-new-powers and tool-surface guardrails still pass;
- the review console still exposes Agent Runs, summaries, timeline evidence, and Export Run
  Evidence;
- the review console includes the `Demo Path` guide and grouped run evidence overview.

## Non-Goals

The operator workbench does not prove OS isolation, host compromise resistance, production
deployment safety, compliance automation, SIEM custody, production identity, remote MCP safety,
container/VM lifecycle control, or activity outside Ithildin-mediated actions.
