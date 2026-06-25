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
- `docs/codex/read-only-project-intelligence.md` explains the eleven-tool project-intelligence
  family as orientation evidence, while `docs/codex/read-only-capability-inventory.md` maps that
  family back to the full 24-tool governed surface, policy resources, gates, and source-review
  handoffs.
- `make operator-sandbox-demo-packet` records the operator-managed sandbox/workspace story.
- `make agent-run-correlation-packet` records the run-to-tool/audit/approval correlation story.
- `make demo-readiness-summary` records ready, missing, optional/manual, deferred, and recommended
  next-command status for the local demo handoff.
- `make demo-operator-walkthrough` writes `OPERATOR_DEMO_WALKTHROUGH.md` as the front-door
  operator path with expected screens, expected evidence files, next human steps, and reset
  guidance.
- `make demo-reset-guide` records read-only reset/recovery guidance for repeated or incomplete
  demo flows.
- `make demo-flow` writes `DEMO_FLOW_RESULT.md` with proposal, approval, audit, and candidate run
  ID evidence after the optional mediated local demo.
- `make demo-observed-summary` writes `DEMO_OBSERVED_SUMMARY.md` as the compact post-demo entry
  point for observed proposal, approval, audit, run, and export evidence.
- `make demo-flow-readiness` validates the demo-flow result, reset guide, UI demo labels, packet
  wiring, and no-new-powers posture.
- `make demo-flow-result-check`, `make demo-evidence-packet`, and
  `make demo-evidence-readiness` validate and package the optional demo result evidence for review.
- `make live-demo-status`, `make live-demo-smoke`, `make live-demo-evidence-summary`, and
  `make live-demo-packet` record live-demo handoff evidence.
- `make sandbox-artifact-observed-demo` records observed local fixture approval/execution evidence
  for the bounded `sandbox.artifact.write_text` path.
- `make hello-world-sandbox-observed-demo` records the operator-facing Hello World version of the
  observed governed artifact path.
- `make demo-workbench-smoke` records a deterministic operator-flow smoke transcript.
- `make workbench-evidence-packet` packages the operator workbench story into one focused review
  packet.

## Demo Wrapper

`make demo-workbench` is a local evidence wrapper. It runs only existing read-only or ignored-output
demo evidence commands:

- `make live-demo-preflight`;
- `make live-demo-status`;
- `make live-demo-smoke`;
- `make sandbox-artifact-observed-demo`;
- `make hello-world-sandbox-observed-demo`;
- `make live-demo-evidence-summary`;
- `make demo-readiness-summary`;
- `make demo-operator-walkthrough`;
- `make operator-demo-guide`;
- `make demo-state-report`;
- `make demo-observed-summary`;
- `make demo-reset-guide`;
- `make demo-evidence-packet`;
- `make demo-workbench-smoke`;
- `make operator-sandbox-demo-packet`;
- `make agent-run-correlation-packet`;
- `make workbench-evidence-packet`.

It does not start services, stop services, mutate governed workspaces, repair diagnostics, or manage
containers. It includes one temporary local fixture governed call through
`sandbox.artifact.write_text` to record observed approval/execution evidence; that fixture does not
touch the configured demo workspace or promote artifacts to the host.

## Evidence Bundle

`make workbench-evidence-packet` writes ignored artifacts under
`var/review-packets/v3/operator-workbench/`:

- workbench index;
- top-level `WORKBENCH_DEMO_INDEX.md`;
- top-level `DEMO_READINESS_SUMMARY.md`;
- top-level `OPERATOR_DEMO_WALKTHROUGH.md`;
- top-level `OPERATOR_DEMO_GUIDE.md`;
- top-level `DEMO_STATE_REPORT.md`;
- top-level `DEMO_RESET_GUIDE.md`;
- top-level `WORKBENCH_DEMO_SMOKE.md`;
- `07_WORKBENCH_DEMO_STORY.md` happy-path narrative;
- `08_OPERATOR_DEMO_GUIDE.md` bundled guide copy;
- `09_DEMO_STATE_REPORT.md` bundled state report copy;
- `10_DEMO_RESET_GUIDE.md` bundled reset guide copy;
- `12_OPERATOR_DEMO_WALKTHROUGH.md` bundled walkthrough copy;
- reviewer prompt;
- bundled operator docs;
- command evidence;
- artifact pointers;
- artifact hashes.
- `var/review-packets/v3/sandbox-artifact-observed-demo/` observed sandbox artifact write
  approval/execution evidence.
- `var/review-packets/v3/hello-world-sandbox-observed-demo/` observed Hello World sandbox artifact
  evidence.

`WORKBENCH_DEMO_INDEX.md` is the first file to open. Its newest reading order is:
`WORKBENCH_DEMO_INDEX.md`, `OPERATOR_DEMO_WALKTHROUGH.md`, `DEMO_OBSERVED_SUMMARY.md`,
`DEMO_FLOW_RESULT.md` after `make demo-flow`, `RUN_EVIDENCE_EXPORT.json`,
`OPERATOR_DEMO_GUIDE.md`, `DEMO_STATE_REPORT.md`, `DEMO_READINESS_SUMMARY.md`,
`WORKBENCH_DEMO_SMOKE.md`, `DEMO_RESET_GUIDE.md`, the workbench packet boundary, the live-demo
packet, the observed sandbox artifact write evidence, and the run evidence/export docs.
The observed Hello World sandbox artifact evidence sits immediately after the generic observed
sandbox artifact write packet in that reading order.
`OPERATOR_DEMO_WALKTHROUGH.md` gives the first human
path with expected screens, expected evidence files, next steps, and reset guidance.
`07_WORKBENCH_DEMO_STORY.md` gives the happy path from preflight through cleanup,
`OPERATOR_DEMO_GUIDE.md` gives the operator-facing stage table, `DEMO_STATE_REPORT.md` records
seed/reachability/artifact status plus next commands, and `DEMO_RESET_GUIDE.md` records read-only
recovery guidance. The run evidence export includes a safe
`summary` object with principal, workspace, session, status, tools used, decision counts, approval
count, patch diagnostic count, audit event count, warning count, policy hash, and manifest-lock hash.

The packet points to existing live-demo, operator sandbox, observed sandbox artifact write, Agent Run
correlation, signed evidence, negative transcript, and consolidated review artifacts. It is a
reviewer convenience artifact, not notarization, SIEM custody, compliance automation, production
security, or proof of activity outside Ithildin-mediated actions.

When demoing the read-only project-intelligence family from the workbench, the operator should
frame these tools as safe workspace orientation: counts, allowlisted labels, truncation, and policy
evidence. The demo should not imply command execution, CI execution, dependency scanning, language
detection, config parsing, registry/network lookup, raw path disclosure, file-content inspection,
or deployment/compliance readiness.

## Readiness Gate

`make workbench-readiness` validates:

- the workbench readiness doc is in the review docs and docs site;
- README and reproduction-map command lists mention the workbench commands;
- `make demo-workbench` and `make workbench-evidence-packet` are wired;
- `make demo-readiness-summary`, `make demo-operator-walkthrough`, `make operator-demo-guide`, `make demo-workbench-smoke`,
  `make demo-state-report`, `make demo-observed-summary`, `make demo-reset-guide`, `WORKBENCH_DEMO_INDEX.md`,
  `DEMO_READINESS_SUMMARY.md`, `OPERATOR_DEMO_GUIDE.md`, `DEMO_STATE_REPORT.md`,
  `DEMO_FLOW_RESULT.md`, `DEMO_OBSERVED_SUMMARY.md`, `DEMO_RESET_GUIDE.md`,
  `OPERATOR_DEMO_WALKTHROUGH.md`, `07_WORKBENCH_DEMO_STORY.md`, `10_DEMO_RESET_GUIDE.md`,
  `11_DEMO_OBSERVED_SUMMARY.md`, `12_OPERATOR_DEMO_WALKTHROUGH.md`, and
  `WORKBENCH_DEMO_SMOKE.md` are wired;
- release-check includes the workbench readiness gate;
- review-candidate includes the focused demo evidence closure packet;
- tool count remains `24`;
- no-new-powers and tool-surface guardrails still pass;
- the review console still exposes Agent Runs, summaries, timeline evidence, and Export Run
  Evidence;
- the review console includes the `Demo Path` guide and grouped run evidence overview.

## Non-Goals

The operator workbench does not prove OS isolation, host compromise resistance, production
deployment safety, compliance automation, SIEM custody, production identity, remote MCP safety,
container/VM lifecycle control, or activity outside Ithildin-mediated actions.
