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

If the dual-response disposition record, runtime-ticket internal review, and runtime
gate-readiness decision record are present, the next allowed operator action is to prepare the
still-blocked `ERG-004` descriptor-only runtime implementation-planning checkpoint:

```sh
make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-check
make sandbox-vm-live-poc-runtime-descriptor-only-plan-check
make sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket-check
make sandbox-vm-live-poc-runtime-descriptor-only-implementation-decision-check
make sandbox-vm-live-poc-runtime-descriptor-only-implementation-check
make sandbox-vm-live-poc-runtime-descriptor-only-internal-source-review-check
make sandbox-vm-live-poc-runtime-descriptor-only-negative-transcripts
make sandbox-vm-live-poc-runtime-descriptor-only-ticket-review-bundle-check
make sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle-check
make sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake-check
make sandbox-vm-live-poc-runtime-descriptor-only-response-inbox-check
make sandbox-vm-live-poc-runtime-descriptor-only-send-receipt-check
make sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run
make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check
make no-new-powers-guardrail
make tool-surface-invariant-gate
```

Primary descriptor-only handoff artifacts:

- `docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-implementation.md`
- `docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-internal-source-review.md`
- `docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-negative-transcripts.md`
- `docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle.md`
- `docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake.md`
- `docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-response-inbox.md`
- `docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-send-receipt.md`
- `docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run.md`
- `docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight.md`
- `var/review-packets/v3/sandbox-vm-live-poc-runtime-descriptor-only-source-review`

The descriptor-only implementation is now a bounded operator-attested descriptor-record slice, and
the current handoff is source review of that slice. The internal source review now includes a
high-effort addendum with no blocking findings, but external/source disposition is still required.
This remains descriptor-only and does not
approve live VM/container inspection, VM/container lifecycle management, local model invocation,
sandbox orchestration, Mission Control
runtime behavior, trusted-host promotion, host writes, network expansion, API/MCP profile loading,
or new governed tool powers.

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

When a real reviewer response is available for the current active `ERG-004` route, preserve the
descriptor-only send receipt, refresh the focused descriptor-only response inbox if needed, paste
the response only into the descriptor-only raw-response file, and run the paste preflight before any
normalization:

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-send-receipt-check
make sandbox-vm-live-poc-runtime-descriptor-only-response-inbox
make enterprise-response-waiting-room
make enterprise-response-now
make enterprise-response-paste-preflight
```

After the paste preflight is clean, run:

```sh
make enterprise-response-intake-refresh
```

Then follow the lane-specific response kit, dry-run, closure gate, response-application record, and
playbook. For the current active route, the primary lane is:

- `ERG-004`: use the descriptor-only source-review response inbox, response dry run, application
  preflight, response-application record, and response-application playbook.

Historical fallback lanes remain available only when the operator next-action command reports the
fallback ERG-003/ERG-002 route:

- `ERG-003`: use the sandbox/VM static preflight response kit and closure gate.
- `ERG-002`: use the Mission Control display response kit and closure gate.
- Historical fallback response handling may still use `make enterprise-dual-response-inbox`, but
  that is not the active ERG-004 descriptor-only receive path.

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
