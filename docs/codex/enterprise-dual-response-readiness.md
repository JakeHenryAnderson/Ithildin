# Enterprise Dual Response Readiness

Status: operator response-readiness summary for the dual enterprise review handoff.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Run:

```sh
make enterprise-dual-response-readiness
```

Before normalizing a real response, generate the local landing pad:

```sh
make enterprise-dual-response-inbox
```

The inbox records the current reviewed-packet hashes and exact normalization/dry-run/closure
commands for `ERG-003` and `ERG-002`. It does not normalize responses or close either lane.

## Purpose

This check summarizes whether normalized external-review responses are present for the two current
send-ready enterprise reviews:

- `ERG-003`: static sandbox/VM preflight disposition.
- `ERG-002`: Mission Control display/import planning review.

It also runs the existing lane-specific dry-run checks and reports the next safe operator command
for each lane.

For all enterprise review lanes, use `make enterprise-response-status-board`. That board aggregates
normalized-response presence without recording review or closing any lane.

This check does not record review, does not mutate findings, does not close either lane, does not approve Mission Control runtime behavior, does not approve live VM/container inspection, and does not approve local model invocation.

## Expected No-Response State

Before a reviewer response is copied into the normalized response path, the expected state is:

- `response_present: false`;
- `closure_ready: false`;
- `recommended_next: wait_for_external_response`;
- all runtime and product-boundary authorities remain `false`.

That no-response state is valid. It means the packets are ready to send, but review feedback has not
yet been received.

## Response Paths

`ERG-003` response path:

```text
var/review-runs/sandbox-vm-static-preflight/normalized-response.json
```

If present, run:

```sh
make sandbox-vm-static-preflight-response-dry-run
make sandbox-vm-static-preflight-disposition-closure-check
```

`ERG-002` response path:

```text
var/review-runs/mission-control-display/normalized-response.json
```

If present, run:

```sh
make mission-control-display-response-dry-run
make mission-control-display-disposition-closure-check
```

## Boundary

This readiness summary is read-only orchestration around existing response gates. It does not
normalize raw reviewer text, does not write response files, does not create committed findings, does
not apply triage updates, and does not change closure-matrix rows.

Only later committed response-intake and triage records may update either lane.
