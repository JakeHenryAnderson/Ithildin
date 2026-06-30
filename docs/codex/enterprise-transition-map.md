# Enterprise Transition Map

Status: checked post-review transition map for enterprise-readiness lanes.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Run:

```sh
make enterprise-transition-map
```

This map is the bridge between enterprise review responses and later committed decision records. It
does not record external review, normalize reviewer responses, close lanes, approve implementation
planning, approve runtime behavior, or approve public/security-product positioning.

## Current Transition Table

| Lane | Current state | Required evidence before transition | Allowed next state | Still blocked after transition |
| --- | --- | --- | --- | --- |
| `v1_local_preview_rc` | `operator_trial_observed` | release-check and review-candidate evidence | `local_technical_preview_handoff` | production identity, hosted operation, public/security-product claims |
| `ERG-003` static sandbox/VM preflight | `external_review_required` | favorable source-level or packet-and-source response through the ERG-003 response kit and closure gate | `closed_local_preview_static_preflight` | live VM/container inspection, VM/container lifecycle management, local model invocation, sandbox orchestration |
| `ERG-002` Mission Control display/import planning | `planning_only` | favorable display/import planning response through the ERG-002 response kit and closure gate | `ready_for_design_only_decision_record` | Mission Control runtime importer behavior, execution authority, API callbacks, polling or mutating Ithildin APIs |
| `ERG-004` live sandbox/VM POC | `blocked` | favorable ERG-003 disposition plus separate ERG-004 decision record | `ready_for_decision_record` | live implementation until decision record and implementation gate explicitly approve it |
| `ERG-005` trusted-host promotion | `blocked` | favorable trusted-host promotion response kit and closure gate | `ready_for_design_only_decision_record` | direct host writes, overwrite/delete/move behavior, automatic promotion |
| `ERG-006/ERG-007` identity and storage | `planning_only` | favorable identity/storage architecture response and closure gate | `architecture_continuation_only` | production identity, enterprise RBAC, runtime Postgres, migrations, retention enforcement |
| `ERG-008` SIEM export adapter | `planning_only` | favorable SIEM adapter architecture response and closure gate | `architecture_continuation_only` | SIEM adapter runtime behavior, hosted telemetry, remote delivery, custody-grade audit claims |
| `ERG-009` compliance mapping | `planning_only` | favorable compliance-mapping architecture response and closure gate | `architecture_continuation_only` | compliance automation, legal conclusions, certification claims, regulated-industry compliance claims |
| `ERG-010` public/security-product positioning | `blocked` | favorable docs/claims public-preview disposition closure gate | `positioning_decision_record_only` | public/security-product positioning unless a later decision explicitly narrows and approves claims |

## Transition Rules

- `ERG-003` may move only to `closed_local_preview_static_preflight`.
- `ERG-002` may move only to `ready_for_design_only_decision_record`.
- `ERG-004` remains blocked until `ERG-003` is favorably dispositioned and a separate decision
  record exists.
- Mission Control runtime behavior remains blocked until a separate Mission Control-side
  implementation decision exists.
- Architecture continuation states are not runtime approval states.
- No transition in this map approves new governed tool powers.
- Do not manually promote a lane from this map. Use the lane-specific response kit, normalizer,
  closure gate, and decision-record path.
- For the current `ERG-003` and `ERG-002` send set, paste responses under
  `var/review-runs/enterprise-dual-response-inbox/`, run `make enterprise-response-waiting-room`,
  run `make enterprise-response-now`, and run `make enterprise-response-paste-preflight` before
  any lane-specific closure flow.

## Blocked Boundaries

This map does not approve:

- live VM/container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- Mission Control runtime behavior;
- local model invocation;
- trusted-host promotion;
- direct host writes;
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
make enterprise-transition-map
make enterprise-dependency-ladder
make enterprise-current-checkpoint
make enterprise-response-command-matrix
make enterprise-response-application-protocol
```

`make release-check` includes this transition map so the allowed next states, blocked-boundary
language, current tool count, no-selected-capability state, and no-response state cannot quietly
drift.
