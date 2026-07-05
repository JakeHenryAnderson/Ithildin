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

If the dual-response disposition record, runtime-ticket internal review, runtime gate-readiness
decision record, and descriptor-only local-development disposition are present, the next allowed
operator action is to prepare the implemented staging-only `ERG-005` trusted-host promotion runtime
source-review lane:

```sh
make trusted-host-descriptor-contract-check
make trusted-host-promotion-decision-intake-check
make trusted-host-promotion-state-machine-check
make trusted-host-promotion-negative-fixtures-check
make trusted-host-promotion-zone-contract-check
make trusted-host-promotion-implementation-plan-check
make trusted-host-promotion-source-review-packet-check
make trusted-host-promotion-disposition-packet-check
make trusted-host-promotion-external-review-bundle-check
make trusted-host-promotion-response-kit-check
make trusted-host-promotion-response-dry-run
make trusted-host-promotion-internal-review-check
make trusted-host-promotion-implementation-gate-decision-check
make trusted-host-promotion-limited-runtime-plan-check
make trusted-host-promotion-limited-runtime-ticket-check
make trusted-host-promotion-runtime-implementation-decision-check
make trusted-host-promotion-negative-transcripts
make trusted-host-promotion-runtime-source-review-bundle-check
make no-new-powers-guardrail
make tool-surface-invariant-gate
```

Primary trusted-host handoff artifacts:

- `docs/codex/trusted-host-promotion-decision-intake.md`
- `docs/codex/trusted-host-promotion-state-machine.md`
- `docs/codex/trusted-host-promotion-negative-fixtures.md`
- `docs/codex/trusted-host-promotion-zone-contract.md`
- `docs/codex/trusted-host-promotion-implementation-plan.md`
- `docs/codex/trusted-host-promotion-source-review.md`
- `docs/codex/trusted-host-promotion-disposition-packet.md`
- `docs/codex/trusted-host-promotion-external-review-bundle.md`
- `docs/codex/trusted-host-promotion-response-kit.md`
- `docs/codex/trusted-host-promotion-implementation-gate-decision.md`
- `docs/codex/trusted-host-promotion-limited-runtime-plan.md`
- `docs/codex/trusted-host-promotion-limited-runtime-ticket.md`
- `docs/codex/trusted-host-promotion-runtime-implementation-decision.md`
- `docs/codex/trusted-host-promotion-runtime-implementation.md`
- `docs/codex/v3-trusted-host-promotion-runtime-internal-review.md`
- `docs/codex/trusted-host-promotion-runtime-source-review.md`
- `var/review-packets/v3/trusted-host-promotion-runtime-source-review`
- `var/review-packets/v3/trusted-host-promotion-external-review`

The descriptor-only ERG-004 implementation is now a bounded operator-attested descriptor-record
slice with `descriptor_only_local_preview_disposition_ready` recorded for continued local
development. That does not close ERG-004 for broader claims. ERG-005 now has an implemented
staging-only, single-artifact runtime slice with negative transcripts, internal source review, and a
focused runtime source-review bundle. Broad trusted-host promotion remains blocked, and unclear
implementation questions should stop for reassessment instead of creating more low-value packet
polish. This next action does not approve live VM/container inspection, VM/container lifecycle
management, local model invocation, sandbox orchestration, Mission Control runtime behavior, broad
trusted-host promotion, arbitrary host writes, network expansion, API/MCP profile loading, or new
governed tool powers.

The previous descriptor-only response intake remains documented for lineage in
`sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake.md`.

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

When a real reviewer response is available for the current active `ERG-005` route, preserve the
trusted-host response kit, paste the response only into the trusted-host raw-response file, and run
the lane-specific dry-run before any committed triage:

```sh
make trusted-host-promotion-response-kit-check
make trusted-host-promotion-response-dry-run
make trusted-host-promotion-external-response-intake-check
make trusted-host-promotion-disposition-closure-check
make enterprise-response-waiting-room
make enterprise-response-now
```

After the paste preflight is clean, run:

```sh
make enterprise-response-intake-refresh
```

Then follow the lane-specific response kit, dry-run, closure gate, response-application record, and
playbook. For the current active route, the primary lane is:

- `ERG-005`: use the trusted-host promotion response kit, dry run, external response intake, and
  disposition closure gate.

Historical fallback lanes remain available only when the operator next-action command reports the
fallback ERG-003/ERG-002 route:

- `ERG-003`: use the sandbox/VM static preflight response kit and closure gate.
- `ERG-002`: use the Mission Control display response kit and closure gate.
- Historical fallback response handling may still use `make enterprise-dual-response-inbox` and
  `make enterprise-response-paste-preflight`, but that is not the active ERG-005 trusted-host
  receive path.

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
