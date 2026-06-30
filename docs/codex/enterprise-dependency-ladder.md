# Ithildin Enterprise Dependency Ladder

Status: checked enterprise dependency ladder for post-RC work.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Recommended first closure lane: `ERG-003`.

Recommended second closure lane: `ERG-002`.

Run:

```sh
make enterprise-dependency-ladder
```

This ladder turns the enterprise progress model, gap matrix, current checkpoint, response status,
and send-readiness state into one dependency order. It is an operator sequencing aid only. It does
not record external review, close enterprise lanes, approve implementation planning, approve runtime
behavior, or approve public/security-product positioning.

## Current Ladder

| Checkpoint | Status | Depends on | Unlocks |
| --- | --- | --- | --- |
| `v1_local_preview_rc` | `operator_trial_observed` | `release-check and review-candidate` | `local technical-preview handoff only` |
| `erg_003_static_preflight` | `external_review_required` | `ERG-003 source-level or packet-and-source disposition` | `static preflight local-preview closure only` |
| `erg_002_mission_control_display` | `planning_only` | `ERG-002 display/import planning disposition` | `Mission Control-side design-only decision record` |
| `erg_004_live_sandbox_vm_poc` | `blocked` | `favorable ERG-003 disposition and separate decision record` | `live POC implementation planning only` |
| `erg_005_trusted_host_promotion` | `blocked` | `trusted-host promotion disposition and decision record` | `promotion implementation planning only` |
| `enterprise_architecture_lanes` | `planning_only_or_blocked` | `separate identity/storage/SIEM/compliance/public-positioning dispositions` | `architecture decisions only` |

## Sequencing Rules

`ERG-004` remains blocked until `ERG-003` is favorably dispositioned through the static preflight
response kit, closure gate, and a later committed decision/triage record.

Mission Control display/import planning remains design-only until `ERG-002` is favorably
dispositioned through the Mission Control response kit, closure gate, and a later committed
decision record.

Trusted-host promotion remains blocked until its own review and decision path is favorably
dispositioned. It is not unlocked by `ERG-002` or `ERG-003`.

Enterprise architecture lanes remain separate. Production identity, runtime storage, SIEM adapters,
compliance mapping support, and public positioning do not inherit approval from sandbox or Mission
Control display decisions.

No row in this ladder approves runtime behavior. Do not manually promote a lane. Use the
lane-specific response kit, closure gate, and decision-record path.

## Blocked Boundaries

This ladder does not approve:

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

## Recommended Operator Sequence

1. Refresh the send set with `make enterprise-dual-review-outbox`,
   `make enterprise-review-send-manifest`, `make enterprise-review-submission-prompt`,
   `make enterprise-review-send-receipt-template`,
   `make enterprise-review-send-receipt-validate RECEIPT=path/to/copied-receipt.json`,
   `make enterprise-dual-response-inbox`, `make enterprise-response-waiting-room`, and
   `make enterprise-response-paste-preflight`, then `make enterprise-review-handoff-drill`.
2. Send `ERG-003` with the static sandbox/VM preflight external-review packet.
3. Send `ERG-002` with the Mission Control display/import planning packet.
4. After responses arrive, paste them under
   `var/review-runs/enterprise-dual-response-inbox/`, run `make enterprise-response-waiting-room`,
   and run the response paste preflight before any lane-specific normalizer, dry-run, closure gate,
   or decision record.
5. Keep `ERG-004` blocked until the `ERG-003` response path is favorable and recorded.
6. Keep Mission Control runtime behavior blocked until the `ERG-002` response path is favorable and
   a separate Mission Control-side design-only decision exists.
7. Keep trusted-host promotion, SIEM adapters, compliance automation, production identity/storage,
   and public positioning on their own disposition tracks.

## Validation

Run:

```sh
make enterprise-dependency-ladder
make enterprise-progress-model
make enterprise-current-checkpoint
make enterprise-review-send-readiness
make enterprise-response-status-board
```

`make release-check` includes this ladder so the dependency order, tool count, blocked-boundary
language, and no-response state cannot quietly drift.
