# Enterprise Response Now

Status: read-only current response-intake command summary.

Current governed tool count: `24`.

Run:

```sh
make enterprise-response-now
```

This command is the receive-side companion to `make enterprise-send-now`. It reads the active
`ERG-004` descriptor-only raw-response waiting-room state and prints the exact next response-intake
commands for that lane: paste preflight, normalizer command, lane dry run, and closure gate. It is
for the operator moment after an external response may have been pasted, when the next question is
"what command do I run now?"

It does not normalize responses, does not write response files, does not record external review,
does not mutate findings, does not close any lane, and does not approve runtime behavior.

The historical `ERG-003`/`ERG-002` fallback response material remains available in older dual-lane
docs, but this helper now follows the current active `ERG-004` handoff path.

## Expected Flow

Before a response arrives, the command should report `wait_for_external_response` and show active
`ERG-004` as a generated placeholder.

After the human send step and receipt validation, paste the real reviewer response into the ignored
descriptor-only response inbox path:

```sh
var/review-runs/sandbox-vm-live-poc-runtime-descriptor-only-response-inbox/RAW_RESPONSE_ERG-004-DESCRIPTOR-ONLY.md
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
