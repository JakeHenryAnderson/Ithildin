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

The command is intentionally lightweight: it does not regenerate review packets or recursively run
send-readiness bundles just to print the next operator action. Run the listed action commands for
the heavier validation artifacts.

## Current Expected Action

If the dual-response disposition record and runtime-ticket internal review are present, the next
allowed operator action is to prepare the still-blocked `ERG-004` live sandbox/VM POC runtime
implementation gate:

```sh
make sandbox-vm-live-poc-runtime-ticket-internal-review-check
make sandbox-vm-live-poc-runtime-implementation-gate-check
make sandbox-vm-live-poc-runtime-descriptor-contract-check
make sandbox-vm-live-poc-runtime-descriptor-contract-internal-review-check
make sandbox-vm-live-poc-runtime-gate-readiness-review-bundle-check
make sandbox-vm-live-poc-runtime-gate-readiness-internal-review-check
make sandbox-vm-live-poc-runtime-descriptor-only-plan-check
make sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket-check
make sandbox-vm-live-poc-runtime-descriptor-only-ticket-review-bundle-check
make sandbox-vm-live-poc-runtime-gate-readiness-response-intake-check
make sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run
make sandbox-vm-live-poc-runtime-gate-readiness-response-application-record-check
make sandbox-vm-live-poc-runtime-gate-readiness-response-application-playbook-check
make sandbox-vm-live-poc-runtime-gate-readiness-response-application-preflight-check
make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton-check
```

The descriptor-only plan and implementation ticket are the current non-runtime bridge before any
future descriptor slice can be implemented. This is runtime implementation-gate preparation only. It
does not approve runtime implementation in this checkpoint, live VM/container inspection,
VM/container lifecycle management, local model invocation, sandbox orchestration, Mission Control
runtime behavior, trusted-host promotion, or new governed tool powers.

## Historical Send Fallback

If the dual-response disposition record or runtime-ticket internal review is absent in a future
fresh checkout, the command may fall back to the historical ERG-003/ERG-002 send route. That is not
the current route after the recorded dispositions. In that fallback state, the operator action is:

1. Refresh the current local evidence:

   ```sh
   make release-check
   make review-candidate
   ```

2. Prepare the current send set:

   ```sh
   make enterprise-review-send-refresh
   make handoff-dry-run
   make enterprise-send-now
   ```

3. Send only the current recommended enterprise packets:

   - `ERG-003`: static sandbox/VM preflight disposition.
   - `ERG-002`: Mission Control display/import planning review.

4. Inspect the display-only `handoff_artifacts` paths from `make enterprise-operator-next-action`:

   - `var/review-packets/v3/enterprise-dual-review-outbox`
   - `var/review-packets/v3/enterprise-review-send-manifest`
   - `var/review-packets/v3/enterprise-review-send-quickstart`
   - `var/review-packets/v3/enterprise-review-submission-prompt`
   - `var/review-packets/v3/enterprise-review-send-receipt-template`
   - `var/review-runs/enterprise-review-send-receipts/enterprise-review-send-receipt-copy.json`
   - `var/review-packets/v3/enterprise-review-send-package`
   - `var/review-packets/v3/enterprise-review-upload-staging`
   - `var/review-runs/enterprise-dual-response-inbox`
   - `var/review-runs/enterprise-review-send-session-record`

5. Wait for real reviewer responses before running any response-normalization or closure flow.

## If Responses Arrive

When real reviewer responses are available, preserve the local send receipt, refresh the ignored
dual-response inbox paths, paste responses only into those ignored raw-response files, and run the
paste preflight before any normalization:

```sh
make enterprise-review-send-receipt-template
make enterprise-review-send-receipt-copy
make enterprise-review-send-receipt-validate RECEIPT=path/to/copied-receipt.json
make enterprise-dual-response-inbox
make enterprise-response-waiting-room
make enterprise-response-now
make enterprise-response-paste-preflight
```

After the paste preflight is clean, run:

```sh
make enterprise-response-intake-refresh
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
