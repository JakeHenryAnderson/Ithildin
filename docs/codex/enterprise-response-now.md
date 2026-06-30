# Enterprise Response Now

Status: read-only current response-intake command summary.

Current governed tool count: `24`.

Run:

```sh
make enterprise-response-now
```

This command is the receive-side companion to `make enterprise-send-now`. It reads the current
`ERG-003` and `ERG-002` raw-response waiting-room state and prints the exact next response-intake
commands for each lane: paste preflight, normalizer command, lane dry run, and closure gate. It is
for the operator moment after external responses may have been pasted, when the next question is
"what command do I run now?"

It does not normalize responses, does not write response files, does not record external review,
does not mutate findings, does not close either lane, and does not approve runtime behavior.

## Expected Flow

Before responses arrive, the command should report `wait_for_external_response` and show both lanes
as generated placeholders.

After the human send step and receipt validation, paste real reviewer responses into the ignored
dual-response inbox paths:

```sh
var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-003.md
var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-002.md
```

Then run:

```sh
make enterprise-response-waiting-room
make enterprise-response-now
```

If a lane reports `candidate_response`, run the lane-specific paste preflight printed by
`enterprise-response-now`. A passing preflight means only that the response is ready for the
existing normalizer, dry-run, and closure-gate sequence.

## Relationship To Existing Checks

- `make enterprise-response-waiting-room` answers whether a response path is still a placeholder,
  missing, invalid, too large, or a candidate response.
- `make enterprise-response-paste-preflight` validates a pasted response before normalization.
- `make enterprise-response-now` summarizes the current state and prints the next commands without
  taking any of those actions.

## What This Does Not Approve

This command does not approve:

- live VM/container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- Mission Control runtime behavior;
- local model invocation;
- trusted-host promotion;
- SIEM adapter runtime behavior;
- production identity or enterprise RBAC;
- runtime Postgres;
- hosted telemetry;
- remote MCP hosting;
- compliance automation;
- public/security-product positioning;
- new governed tool powers.

## Validation

Run:

```sh
make enterprise-response-now
make enterprise-response-waiting-room
make enterprise-response-paste-preflight
make enterprise-operator-next-action
```

`make release-check` includes this command so the receive-side operator shortcut, docs wiring,
blocked-boundary language, and command routing cannot quietly drift.
