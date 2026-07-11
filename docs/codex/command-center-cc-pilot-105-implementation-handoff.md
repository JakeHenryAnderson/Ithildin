# CC-PILOT-105 Implementation Handoff

Status: implementation candidate complete; authorized to proceed to `CC-PILOT-106` after gates.

Base commit: `6a357bd4bb7e7a7dc10abeb4bfa834addf64175c`
Governed tool count: `24`
Runtime authority change: none
Schema/API/telemetry/run-control change: none

## Implemented Slice

The Agent Runs surface now provides two explicit filter layers:

- existing bounded server query fields for identity, workspace, status, and tool; and
- client-side filters for last recorded update, presentation mission context, observed decision,
  observed execution outcome, and observed attention.

Active values appear as individually removable chips, and `Clear all` resets both layers. The
summary reports shown-versus-loaded runs, presentation mission groups, observed-attention count,
and the exact 100-recent-event decision/outcome scope before the timeline. A no-match state repeats
that bounded-window limitation.

Mission labels are visibly described as presentation context. Attention means only a correlated
recent failure, denial, or approval-required decision; it is not anomaly detection, risk scoring, or
incident declaration.

## Authority Boundary

Server queries remain limited to current supported parameters and `limit=25`. Client filters use
only those loaded runs and `GET /audit-events?limit=100`. Selection remains keyed by `run_id` and
does not start, pause, abort, retry, or otherwise control a run.

No telemetry, schema, endpoint, policy, approval, state, tool, or governed power was added.

## Focused Test Evidence

The UI harness verifies:

- existing authenticated bounded run query parameters;
- bounded investigation summary and shown/loaded count;
- observed-decision chip creation;
- observed-attention no-match behavior;
- `Clear all` restoration and chip removal;
- retained selected Workbench detail and all prior decision/artifact/evidence behavior.

Focused result:

```text
Test Files  1 passed (1)
Tests       10 passed (10)
```

## Live Browser Verification

The live Command Center showed one loaded run, one presentation mission group, and one run with
observed attention, with the 100-event observation scope and anti-anomaly/off-platform disclaimer
visible before selection detail. All nine labeled server/client filter controls were present. The
filter layout was tightened to avoid a single over-dense row at intermediate desktop widths.

Browser logs contained only Vite connection/hot-update messages and the React development-tools
notice. This is implementation QA, not fresh-operator UAT or evidence of external activity coverage.

## Validation

Passed: `make ui-test`, `make typecheck`, `make tool-surface-invariant-gate`,
`make no-new-powers-guardrail`, `make agent-workflow-check`, the serial release-readiness/docs-site
pytest pair, `make lint`, `make docs-site`, and `git diff --check`.

## Next Gate

Proceed to `CC-PILOT-106` only after proportional gates pass. Specialist-surface separation may
rehome existing controls but must not create new authorization, policy, export, or runtime behavior.
