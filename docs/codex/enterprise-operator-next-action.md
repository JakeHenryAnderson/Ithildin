# Enterprise Operator Next Action

Status: checked read-only operator next-action summary for the enterprise review loop.

Current governed tool count: `24`.

Run:

```sh
make enterprise-operator-next-action
```

This command answers one narrow question: given the current checked enterprise state, what should
the operator do next? It is a mode-aware state reader. In send mode it validates the current send
artifacts; in response-present mode it routes to the response-intake commands without requiring
send-readiness reports that intentionally fail once response evidence exists. It does not generate
packets, paste responses, normalize responses, write response files, mutate findings, close
enterprise lanes, approve runtime behavior, or approve public/security-product positioning.

## Current Expected Action

With no real enterprise reviewer responses present, the next allowed operator action is:

1. Refresh the current local evidence:

   ```sh
   make release-check
   make review-candidate
   ```

2. Prepare the current send set:

   ```sh
   make enterprise-dual-review-outbox
   make enterprise-review-send-manifest
   make enterprise-review-submission-prompt
   make enterprise-review-handoff-drill
   ```

3. Send only the current recommended enterprise packets:

   - `ERG-003`: static sandbox/VM preflight disposition.
   - `ERG-002`: Mission Control display/import planning review.

4. Wait for real reviewer responses before running any response-normalization or closure flow.

## If Responses Arrive

When real reviewer responses are available, paste them into the ignored raw-response inbox paths and
run:

```sh
make enterprise-response-paste-preflight
make enterprise-response-inbox
make enterprise-response-status-board
make enterprise-response-intake-quickstart
```

Then follow the lane-specific response kit, dry-run, closure gate, response-application record, and
playbook. The current primary lanes are:

- `ERG-003`: use the sandbox/VM static preflight response kit and closure gate.
- `ERG-002`: use the Mission Control display response kit and closure gate.

In this mode, `make enterprise-operator-next-action` is expected to remain valid and report
`run_response_intake_preflight` or `run_lane_specific_closure_playbook` even though lower-level
send-readiness summaries may fail closed because response evidence is present.

## What This Does Not Approve

This next-action summary does not approve:

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
make enterprise-operator-next-action
make enterprise-current-checkpoint
make enterprise-response-status-board
make enterprise-north-star-roadmap
```

`make release-check` includes this next-action summary so the active operator action, recommended
send set, response-state interpretation, blocked-boundary language, and command wiring cannot
quietly drift.
