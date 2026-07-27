# Local v1 LV1-003 O4 Bridge-Disconnected Diagnosis

Status: `SOURCE_DIAGNOSIS_COMPLETE_REPAIR_NOT_YET_REVIEWED_NO_LIVE_AUTHORITY`

Date: 2026-07-26

## Bounded Evidence

Attempt018 is permanently consumed. Its identity-free disposition records:

- Gateway mission lifecycle `runner_reported_running`;
- exactly two Gateway-correlated governed operations already completed;
- Node receipt `next_operation=completion_pending`;
- Node receipt `last_closed_status=failed_closed`;
- stable terminal reason `bridge_disconnected`;
- runner command exit `0`;
- cleanup complete and recovery not required; and
- execution budget zero with all 19 authority fields false.

This diagnosis uses only those closed projections and the tracked fixed-profile source. It does not
reproduce raw runner output or any run, project, container, image, Node, mission, claim, provider,
or credential identity.

## Source Diagnosis

The current fixed profile requires three model-selected MCP affordances:
`mission.step.1`, `mission.step.2`, and `mission.complete`. Only the first two perform governed
operations. After `mission.step.2` succeeds, the Node advances its receipt to operation index `3`
and waits for the runner to select the bookkeeping-only `mission.complete` affordance before the
Node polls control and reports `runner_succeeded`.

Attempt018 completed both governed operations and the runner then exited successfully, closing the
MCP process and Unix transport. The Node therefore observed end-of-stream while still waiting for
operation index `3` and correctly persisted `bridge_disconnected`. Prompt guidance and the MCP tool
descriptions ask the model to call the third affordance, but model compliance is not a defensible
protocol transition.

The bounded product root cause is established: successful fixed-mission finalization depends on an
unnecessary third model-selected bookkeeping call after the complete governed operation sequence.
The evidence does not establish why the model chose to stop, and no claim about model correctness,
provider completion, or raw runner reasoning is made.

## Smallest Defensible Repair

The fixed bridge should expose only the two no-argument affordances that correspond to the two
server-owned governed reads. After `mission.step.2` succeeds, the Node should:

1. persist the second operation as closed;
2. refresh and validate the mission-bound heartbeat;
3. poll signed mission control;
4. refresh and validate the mission-bound heartbeat again;
5. report `runner_succeeded`;
6. persist the terminal receipt; and
7. return the second operation result with terminal status.

The MCP bridge should then close normally when the runner exits after the second successful
affordance. `mission.complete` should be removed from the fixed local affordance list, instructions,
profile, and tests. The two Gateway-governed tools remain unchanged.

This repair makes terminal state a deterministic consequence of the reviewed fixed operation
sequence rather than a third model choice. It does not make model-provider state Gateway truth:
success still means only that the fixed runner bridge completed both governed operations and the
Gateway accepted the bounded runner report.

## Boundary And Authority

The proposed repair:

- removes one local bookkeeping affordance and adds no capability;
- keeps the governed Gateway tool count exactly 24;
- adds no arbitrary input, dynamic tool selection, endpoint, command, host control, Docker access,
  credential access, provider authority, retry, or runner lifecycle control;
- preserves signed mission control, mission-bound heartbeats, Gateway report validation, and
  fail-closed receipt semantics; and
- does not authorize Attempt019, execution, release, promotion, production, or UAT.

Implementation requires a new exact code candidate and a proportional independent Sol-high review.
Sol xhigh and Ultra are not required. Any later live evidence run requires its own separate
one-shot authorization gate and immediate consumed disposition.
