# Sandbox/VM Live POC Preconditions Map

Status: preconditions map for blocked `ERG-004`.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Current `ERG-004` status: `blocked`.

This map turns the live sandbox/VM worker proof-of-concept lane into an explicit readiness
checklist. It does not approve live VM/container inspection, does not approve sandbox
orchestration, does not approve local model invocation, does not approve Mission Control runtime
behavior, does not approve trusted-host promotion, and does not approve network expansion.

`ERG-004` remains blocked until a future post-RC decision record can reference favorable `ERG-003`
static preflight disposition evidence. A future decision record must include favorable `ERG-003` static preflight disposition evidence before any later implementation-planning packet may be authorized. This map is not that decision record.

## Purpose

The next useful work for the live POC lane is not runtime behavior. It is proving that the decision
inputs are complete enough for a reviewer or operator to say whether implementation planning may
begin later.

This map gives reviewers and future implementers one place to answer:

- did the static preflight lane receive favorable external/source disposition;
- are all critical/high static-preflight findings resolved or stopping the lane;
- is there a non-draft decision record path for `PRD-SANDBOX-LIVE-POC-001`;
- are operator-managed VM/container assumptions explicit;
- are Mission Control, local model, Ithildin, and trusted-host roles separated;
- are cleanup, failure, and cross-source evidence requirements defined;
- are stop conditions strong enough to keep runtime authority blocked.

## Required Preconditions

Before `ERG-004` can move from `blocked` to any implementation-planning state, all of these
preconditions must be true:

| Preconditions | Required evidence | Current expected state |
| --- | --- | --- |
| Favorable static preflight disposition | `ERG-003` external/source reviewer response, disposition packet, response intake result | missing; `ERG-004` remains blocked |
| No open critical/high static-preflight findings | committed finding records and verification notes | must be true before planning |
| Post-RC decision record | `PRD-SANDBOX-LIVE-POC-001` decision record naming commit and reviewed packets | missing; required later |
| Operator-managed VM/container profile | profile contract, mount/root posture, network posture, unsupported-profile warnings | design evidence only |
| Ithildin boundary | mediated actions only, no sandbox orchestration, no host promotion, no broad writes | must remain unchanged |
| Mission Control role | display/import only unless a separate decision explicitly changes it | runtime authority blocked |
| Local model role | proposal-producing client only after separate planning/review | invocation blocked |
| Cleanup transcript requirement | manual cleanup evidence shape and hash fields | required before runtime POC |
| Failure transcript requirement | denied/failed scenario evidence shape and hash fields | required before runtime POC |
| Cross-source evidence | run ID, audit head, sandbox ID, model output hash, packet hashes | evidence contract exists |
| Stop conditions | explicit stop on boundary drift, unreviewed writes, network expansion, local-model authority drift, Mission Control authority drift | required |

## Current Artifact Map

Review these artifacts before any decision about live POC planning:

- `docs/codex/sandbox-vm-static-preflight-reviewer-reproduction-map.md`
- `docs/codex/sandbox-vm-static-preflight-external-review-bundle.md`
- `docs/codex/sandbox-vm-static-preflight-disposition-plan.md`
- `docs/codex/sandbox-vm-static-preflight-external-response-intake.md`
- `docs/codex/sandbox-vm-static-preflight-triage-update.md`
- `docs/codex/sandbox-vm-static-preflight-disposition-packet.md`
- `docs/codex/sandbox-vm-live-poc-decision-intake.md`
- `docs/codex/sandbox-vm-live-poc-evidence-contract.md`
- `docs/codex/sandbox-vm-live-poc-decision-packet.md`
- `docs/codex/sandbox-vm-live-poc-external-response-intake.md`
- `docs/codex/sandbox-vm-live-poc-decision-closure-gate.md`
- `docs/codex/enterprise-sandbox-control-plane-readiness.md`
- `docs/codex/post-rc-decision-register.md`

Generated evidence paths:

- `var/review-packets/v3/sandbox-vm-static-preflight-source-review/`
- `var/review-packets/v3/sandbox-vm-static-preflight-disposition/`
- `var/review-packets/v3/sandbox-vm-live-poc-decision/`
- `var/review-packets/v3/sandbox-vm-poc-review/`

## Command Sequence

Use this sequence to reproduce the current precondition evidence:

```sh
make sandbox-vm-static-preflight-reviewer-reproduction-map-check
make sandbox-vm-static-preflight-external-review-bundle-check
make sandbox-vm-static-preflight-disposition-packet-check
make sandbox-vm-static-preflight-external-response-intake-check
make sandbox-vm-static-preflight-triage-update-check
make sandbox-vm-live-poc-decision-intake-check
make sandbox-vm-live-poc-evidence-contract-check
make sandbox-vm-live-poc-decision-packet
make sandbox-vm-live-poc-decision-packet-check
make sandbox-vm-live-poc-preconditions-map-check
make sandbox-vm-live-poc-external-response-intake-check
make external-findings-intake-dry-run
make no-new-powers-guardrail
make tool-surface-invariant-gate
```

Expected safe outcome today:

- `ERG-003` remains `external_review_required`;
- `ERG-004` remains `blocked`;
- live VM/container inspection remains blocked;
- sandbox orchestration remains blocked;
- local model invocation remains blocked;
- Mission Control runtime behavior remains blocked;
- trusted-host promotion remains blocked;
- network expansion remains blocked;
- tool count remains `24`.

## Decision Outcomes

This map allows only these future disposition outcomes:

- `continue_design_only`: keep improving decision evidence while `ERG-004` remains blocked.
- `revise_preconditions`: fix missing evidence or unclear boundary language.
- `allow_implementation_planning_later`: only after favorable `ERG-003` disposition and a separate
  post-RC decision record; this still does not approve runtime behavior.
- `block_live_poc`: keep `ERG-004` blocked because a precondition failed or a boundary contradiction
  appeared.

No outcome in this map approves implementation, runtime inspection, VM/container lifecycle control,
Mission Control execution authority, local model invocation, trusted-host promotion, SIEM adapter
behavior, production identity, compliance automation, or any new governed tool power.

## What This Map Does Not Prove

This map does not prove external review has happened, does not close `ERG-003`, does not close
`ERG-004`, does not approve live VM/container inspection, and does not prove a sandbox is safe. It
does not authorize runtime work. It only defines the preconditions that must be satisfied before a
future decision record may permit implementation planning.

Validate this map with:

```sh
make sandbox-vm-live-poc-preconditions-map-check
```
