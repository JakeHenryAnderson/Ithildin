# Enterprise North-Star Roadmap

Status: checked north-star map for the path from v1.0 local-preview RC toward a future enterprise
control-plane product.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Run:

```sh
make enterprise-north-star-roadmap
```

This roadmap is a reading-order and dependency map. It does not record external review, normalize
responses, close enterprise lanes, approve runtime behavior, approve capability expansion, or
approve public/security-product positioning.

## Read This First

Use this file as the operator-facing index when deciding where Ithildin is and what should happen
next. The canonical source documents remain:

- `docs/codex/v1.0-rc-status.md`
- `docs/codex/v1.0-progress-assessment.md`
- `docs/codex/enterprise-current-checkpoint.md`
- `docs/codex/enterprise-dependency-ladder.md`
- `docs/codex/enterprise-transition-map.md`
- `docs/codex/enterprise-readiness-gap-matrix.md`
- `docs/codex/enterprise-response-intake-quickstart.md`
- `docs/codex/enterprise-response-paste-preflight.md`

## Current State

Ithildin is a v1.0 local-preview RC candidate, not a production enterprise product. The current
implemented surface is the local governed MCP/tool gateway, local review console, Agent Run and
evidence surfaces, demo/handoff packets, and bounded local-preview tools. The latest local-preview
RC packet is generated through `make review-candidate`.

The current recommended enterprise handoff set remains:

1. `ERG-003`: static sandbox/VM preflight disposition.
2. `ERG-002`: Mission Control display/import planning review.

## Phase Ladder

| Phase | Current status | Main proof command | Unlocks | Still blocked |
| --- | --- | --- | --- | --- |
| `v1_local_preview_rc` | `operator_trial_observed` | `make review-candidate` | local technical-preview handoff only | public/security-product positioning, production identity, hosted operation |
| `erg_003_static_preflight` | `external_review_required` | `make enterprise-next-review-ready-check` | static preflight local-preview closure only | live VM/container inspection, VM lifecycle, local model invocation, sandbox orchestration |
| `erg_002_mission_control_display` | `planning_only` | `make mission-control-display-next-review-ready-check` | Mission Control-side design-only decision record | Mission Control runtime importer behavior, execution authority, polling or mutating Ithildin APIs |
| `erg_004_live_sandbox_vm_poc` | `blocked` | `make sandbox-vm-live-poc-preconditions-ready-check` | live POC implementation planning only after `ERG-003` | live implementation, VM lifecycle management, sandbox orchestration |
| `erg_005_trusted_host_promotion` | `blocked` | `make trusted-host-promotion-disposition-packet-check` | promotion implementation planning only after its own disposition | direct host writes, overwrite/delete/move behavior, automatic promotion |
| `enterprise_architecture_lanes` | `planning_only_or_blocked` | `make enterprise-readiness-gap-matrix-check` | architecture decision records only | production identity, runtime Postgres, SIEM adapters, compliance automation, public positioning |

## Immediate Operator Sequence

1. Refresh the v1.0 local-preview packet:

   ```sh
   make release-check
   make review-candidate
   ```

2. Refresh the enterprise handoff set:

   ```sh
   make enterprise-review-send-refresh
   make handoff-dry-run
   make enterprise-send-now
   ```

3. Send the `ERG-003` and `ERG-002` packets.

4. After the human send step, copy and fill the ignored operator receipt. Do not fill the copied
   receipt before sending because it records what was actually sent.

   ```sh
   make enterprise-review-send-receipt-template
   make enterprise-review-send-receipt-copy
   make enterprise-review-send-receipt-validate RECEIPT=path/to/copied-receipt.json
   ```

5. After responses arrive, paste them into the ignored dual-response inbox at
   `var/review-runs/enterprise-dual-response-inbox/` and run:

   ```sh
   make enterprise-dual-response-inbox
   make enterprise-response-waiting-room
   make enterprise-response-now
   make enterprise-response-paste-preflight
   make enterprise-response-inbox
   make enterprise-response-status-board
   make enterprise-response-intake-quickstart
   ```

6. Use the lane-specific normalizer, dry-run, closure gate, and response application record before
   any committed disposition update.

## Decision Rules

- A favorable `ERG-003` response can close static preflight only; it does not approve live
  VM/container inspection, local model invocation, VM lifecycle management, or sandbox
  orchestration.
- A favorable `ERG-002` response can authorize a Mission Control-side design-only decision record only; it does not approve Mission Control runtime importer behavior or execution authority.
- `ERG-004` remains blocked until `ERG-003` is favorably dispositioned and a separate `ERG-004`
  decision record exists.
- Enterprise architecture lanes do not inherit approval from sandbox or Mission Control decisions.
- No row in this roadmap approves new governed tool powers.

## Blocked Boundaries

This roadmap does not approve:

- shell execution;
- Docker socket access;
- Kubernetes tools;
- browser automation;
- arbitrary HTTP methods, headers, bodies, cookies, or broad network access;
- broad filesystem writes, deletes, moves, chmod, archive extraction, or unbounded traversal;
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

## When To Ask For External Roadmap Review

Ask GPT 5.5 Pro or a human reviewer for a fresh roadmap only when one of these is true:

- a critical/high trust-boundary finding appears;
- `ERG-003` or `ERG-002` receives an ambiguous or unfavorable response;
- implementation would require live VM/container inspection, sandbox orchestration, Mission Control
  runtime behavior, trusted-host promotion, SIEM adapter runtime behavior, production identity,
  runtime Postgres, compliance automation, public/security-product positioning, or a new power
  class;
- the project faces a product-direction fork rather than a normal gated implementation step;
- the same release or closure gate fails three times for the same underlying reason.

## Validation

Run:

```sh
make enterprise-north-star-roadmap
make enterprise-current-checkpoint
make enterprise-dependency-ladder
make enterprise-transition-map
make v1-progress-assessment
```

`make release-check` includes this roadmap so the top-level phase order, tool count, recommended
enterprise handoff set, blocked-boundary language, and no-response state cannot quietly drift.
