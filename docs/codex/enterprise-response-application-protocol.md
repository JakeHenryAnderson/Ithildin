# Enterprise Response Application Protocol

Status: checked operator protocol for applying enterprise external-review responses.

Run:

```sh
make enterprise-response-application-protocol
```

This protocol starts after a reviewer response has been saved to the ignored response inbox. It
does not record external review by itself, does not normalize real responses by itself, does not
close enterprise lanes, does not approve runtime behavior, and does not approve public/security-
product positioning.

## Current Baseline

- Current governed tool count: `24`.
- Current selected capability: `not selected`.
- Current recommended send set: `ERG-003` then `ERG-002`.
- Enterprise response evidence is not present yet.
- Enterprise closure-ready count is `0`.
- Runtime expansion remains blocked until a lane-specific closure gate proves a favorable response
  and a later committed decision record explicitly authorizes the next step.

## Operator Protocol

For any enterprise reviewer response:

1. Regenerate the current checkpoint and response inbox.
2. Save the raw reviewer response only under the lane-specific ignored `var/review-runs/` response
   path.
3. Run the exact lane-specific normalization command from the response inbox.
4. Run the lane-specific dry-run command.
5. Run the lane-specific closure gate.
6. If the closure gate is not ready, keep the lane in its current state and record no committed
   disposition.
7. If the closure gate is ready and no critical/high finding is open, create a later committed
   triage or decision record using the lane-specific response kit.
8. Rerun `make enterprise-current-checkpoint`, `make release-check`, and `make review-candidate`.

Do not edit status docs directly. Use the response kit, closure gate, and decision-record path for
the lane being reviewed.

## Current Send-Set Lanes

### ERG-003 Static Sandbox/VM Preflight

Use the `ERG-003` static preflight response flow first because it is the prerequisite for any later
live VM/container proof-of-concept planning.

Key artifacts:

- `docs/codex/sandbox-vm-static-preflight-response-kit.md`
- `docs/codex/sandbox-vm-static-preflight-response-dry-run.md`
- `docs/codex/sandbox-vm-static-preflight-disposition-closure-gate.md`
- `docs/codex/sandbox-vm-static-preflight-response-application-record.md`
- `docs/codex/sandbox-vm-static-preflight-response-application-playbook.md`

Allowed successful outcome:

- `ERG-003` may move only to `closed_local_preview_static_preflight`.

Still not approved by `ERG-003` closure alone:

- live VM/container inspection;
- VM/container lifecycle management;
- local model invocation;
- sandbox orchestration;
- Mission Control runtime behavior;
- trusted-host promotion;
- SIEM adapters;
- public/security-product positioning;
- new governed tool powers.

### ERG-002 Mission Control Display/Import Planning

Use the `ERG-002` response flow for Mission Control display/import planning only.

Key artifacts:

- `docs/codex/mission-control-display-response-kit.md`
- `docs/codex/mission-control-display-response-dry-run.md`
- `docs/codex/mission-control-display-disposition-closure-gate.md`
- `docs/codex/mission-control-display-decision-record-skeleton.md`
- `docs/codex/mission-control-importer-acceptance-matrix.md`
- `docs/codex/mission-control-handoff-reference-validator.md`

Allowed successful outcome:

- `ERG-002` may move only to `ready_for_design_only_decision_record`.

Still not approved by `ERG-002` closure alone:

- Mission Control runtime importer behavior;
- Mission Control execution authority;
- Mission Control policy authority;
- Mission Control approval authority;
- Mission Control audit authority;
- API callbacks;
- polling or mutating Ithildin APIs;
- local model invocation;
- sandbox orchestration;
- trusted-host promotion;
- SIEM adapters;
- public/security-product positioning;
- new governed tool powers.

## Other Enterprise Lanes

If another enterprise response arrives first, use the all-lane response inbox and that lane's
response kit or closure gate:

- `ERG-005`: trusted-host promotion remains blocked unless the response kit and closure gate prove a
  design-only disposition is ready.
- `ERG-006/ERG-007`: production identity and runtime storage remain planning-only.
- `ERG-008`: SIEM export adapter remains planning-only.
- `ERG-009`: compliance mapping remains planning-only and must not become compliance automation.
- `ERG-004`: live sandbox/VM worker proof of concept remains blocked until a favorable `ERG-003`
  disposition exists.
- `ERG-010`: public/security-product positioning remains blocked.

## Stop Conditions

Stop and reassess before committing any disposition if:

- a response includes any critical/high finding;
- the reviewed packet hash does not match the current artifact hash;
- the response asks for runtime behavior outside the lane's approved scope;
- a closure gate is not ready;
- a normalizer rejects the response;
- a response would imply production identity, runtime Postgres, hosted telemetry, remote MCP,
  sandbox orchestration, SIEM adapter runtime behavior, compliance automation, public/security-
  product positioning, or new governed tool powers.

## Validation

Run:

```sh
make enterprise-response-application-protocol
make enterprise-response-inbox
make enterprise-response-status-board
make enterprise-response-command-matrix
make enterprise-response-intake-drill
make enterprise-current-checkpoint
```

`make release-check` includes this protocol so future response application work cannot quietly lose
the stop conditions, lane ordering, or blocked-boundary language.
