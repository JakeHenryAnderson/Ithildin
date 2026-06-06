# Operator Action States Design

Status: design-only proposal. This document does not add runtime behavior, tool manifests,
executors, policy rules, API endpoints, MCP tools, UI controls, sandbox controls, process
supervision, SIEM adapters, production identity, runtime Postgres, hosted telemetry, shell, Docker,
Kubernetes, browser automation, plugin SDKs, arbitrary HTTP, or broad filesystem writes.

This proposal names future operator-visible states for Agent Runs and mediated workspaces. The names
are vocabulary for design, review, and future evidence contracts only. They do not create pause,
abort, kill, disable, repair, replay, rollback, or process-control behavior.

## Candidate States

| State | Future meaning |
| --- | --- |
| `active` | A run is accepting Ithildin-mediated tool calls. |
| `paused` | Future policy/UI state where new mediated actions would be held. |
| `aborting` | Future transition state after an operator requests a stop. |
| `aborted` | Future terminal state after mediated action intake stops. |
| `disabled` | Future workspace/principal/run state that blocks new mediated activity. |
| `recovery_required` | Existing diagnostic posture when a patch apply or evidence path needs operator review. |
| `failed_closed` | Terminal safe failure state for a run or action. |
| `completed` | Terminal normal completion state. |

## Required Future Review

Any implementation of operator actions must define:

- explicit state transitions and invalid transitions;
- who can request the action;
- whether the action affects a run, principal, workspace, sandbox label, or tool call;
- audit event shape and approval requirements if any;
- UI evidence and warning behavior;
- negative transcripts for replay, stale state, unknown run, disabled principal, and unsupported
  sandbox/process profile;
- interaction with Agent Run timelines, patch diagnostics, and signed export evidence;
- external/source review before implementation.

## Non-Goals

This design does not:

- pause or kill model clients;
- stop host processes;
- control containers, VMs, Docker, Kubernetes, or shells;
- add API or MCP actions;
- change policy decisions;
- mutate Agent Run records;
- repair or roll back patch attempts;
- prove activity outside Ithildin-mediated actions.

## Review Gate

Run:

```text
make operator-action-states-check
```

The gate verifies this design, review-doc/docs-site wiring, README linkage, roadmap linkage, and the
no-new-powers boundary.
