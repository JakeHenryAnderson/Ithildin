# Enterprise Response Application Rehearsal

Status: checked fixture-free rehearsal for the current `ERG-003` and `ERG-002` response application path.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Run:

```sh
make enterprise-response-application-rehearsal
```

This rehearsal is a read-only operator check for the active send set. It proves the current
response-application path is wired before real reviewer responses arrive.

It does not send packets, does not paste reviewer content, does not normalize real responses, does
not write normalized response files, does not write response files, does not mutate findings, does
not record external review, does not close `ERG-003`, does not close `ERG-002`, and does not approve
runtime behavior.

Boundary checklist:

- does not normalize real responses
- does not write response files
- does not mutate findings
- does not record external review
- does not close `ERG-003`
- does not close `ERG-002`
- does not approve runtime behavior
- does not approve Mission Control runtime behavior
- does not approve live VM/container inspection
- does not approve public/security-product positioning

## What It Checks

The rehearsal validates:

- `make enterprise-response-status-board`
- `make enterprise-response-command-matrix`
- `make enterprise-response-application-protocol`
- `make enterprise-response-intake-quickstart`
- `make sandbox-vm-static-preflight-response-application-preflight-check`
- `make mission-control-display-response-application-preflight-check`

The expected current state is:

- `ERG-003`: `external_review_required`
- `ERG-002`: `planning_only`
- response evidence present: `0`
- closure-ready lanes: `0`
- next response action: wait for real reviewer responses

## Allowed Future Paths

If a real `ERG-003` response later passes normalization, dry-run, and closure-gate checks, a later
committed triage update may move only:

```text
ERG-003: external_review_required -> closed_local_preview_static_preflight
```

If a real `ERG-002` response later passes normalization, dry-run, and closure-gate checks, a later
committed decision update may move only:

```text
ERG-002: planning_only -> ready_for_design_only_decision_record
```

## Still Blocked

Even if this rehearsal passes, it does not approve:

- live VM/container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- Mission Control runtime behavior;
- Mission Control execution authority;
- Mission Control policy authority;
- Mission Control approval authority;
- Mission Control audit authority;
- API callbacks;
- polling or mutating Ithildin APIs;
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

It specifically does not approve Mission Control runtime behavior, does not approve live
VM/container inspection, and does not approve public/security-product positioning.

## When A Response Arrives

Use the rehearsal output only as a pre-response confidence check. After a real reviewer response
arrives, follow:

- `docs/codex/enterprise-response-intake-quickstart.md`
- `docs/codex/enterprise-response-application-protocol.md`
- `docs/codex/sandbox-vm-static-preflight-response-application-preflight.md`
- `docs/codex/mission-control-display-response-application-preflight.md`

Then run:

```sh
make enterprise-response-paste-preflight
make enterprise-response-inbox
make enterprise-response-status-board
make enterprise-response-command-matrix
make enterprise-response-application-rehearsal
```

Stop if a response is packet-mismatched, normalizer-rejected, not closure-ready, contains any
critical/high finding, or asks for runtime behavior outside the lane boundary.
