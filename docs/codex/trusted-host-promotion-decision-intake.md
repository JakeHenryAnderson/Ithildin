# Trusted-Host Promotion Decision Intake

Status: decision-intake planning packet for `ERG-005` and `PRD-TRUSTED-HOST-001`.

Current governed tool count: `24`.

Current `ERG-005` status: `blocked`.

Current selected capability: `not selected`.

This intake defines the evidence required before a future post-RC decision record may approve any
trusted-host artifact promotion work. It does not approve runtime behavior, direct host writes,
overwrite/delete/move behavior, broad archive extraction, automatic promotion, promotion without
exact artifact hash binding, promotion without approval evidence, API/MCP behavior, Mission Control
runtime behavior, local model invocation, VM/container lifecycle management, sandbox orchestration,
SIEM adapters, production identity, runtime Postgres, hosted telemetry, shell,
Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem writes, compliance
automation, or public/security-product claims.

Validate this intake with:

```sh
make trusted-host-promotion-decision-intake-check
```

## Required Preconditions

Any future implementation decision for `PRD-TRUSTED-HOST-001` must prove:

- the sandbox promotion evidence contract remains current and design-only;
- an artifact hash-binding model exists for source artifact, host staging artifact, and approved
  host artifact labels;
- an approval model binds the exact artifact hash, source label, staging label, approved label,
  policy hash, manifest hash, operator principal, expiry, and one-time scope;
- a promotion state machine defines requested, approved, completed, rejected, expired, conflicted,
  stale, replay-denied, and recovery-required states;
- a source and destination zone contract defines `sandbox://`, `host-staging://`, `approved://`,
  and evidence labels without exposing raw host paths;
- conflict negative transcripts cover existing target, hash mismatch, stale artifact, unsupported
  type, unsafe label, and denied overwrite cases;
- replay negative transcripts cover reused approval, reused promotion ID, stale request hash, and
  expired approval cases;
- path escape negative transcripts cover absolute path, parent traversal, encoded traversal,
  hidden path, `.git`, symlink, hardlink, and broad archive extraction cases;
- operator warning language states that sandbox outputs are staged evidence only until an approved
  promotion implementation exists;
- external/source review evidence exists for the exact implementation before any host write path is
  enabled;
- no post-RC decision record claims trusted-host promotion, direct host writes, automatic
  promotion, overwrite/delete/move authority, archive extraction, sandbox orchestration, SIEM,
  identity, storage, remote, or compliance authority.

## Required Decision Evidence

A future decision record must include at least:

| Evidence | Required source |
| --- | --- |
| Promotion evidence contract | `sandbox-promotion-evidence-contract.md` |
| Post-RC decision gate | `make post-rc-decision-gate` |
| Post-RC decision register | `make post-rc-decision-register-check` |
| No-new-powers evidence | `make no-new-powers-guardrail` and `make tool-surface-invariant-gate` |
| Artifact hash-binding model | future implementation-planning packet |
| Approval binding model | future implementation-planning packet |
| Promotion state machine | `trusted-host-promotion-state-machine.md` |
| Negative fixture contract | `trusted-host-promotion-negative-fixtures.md` |
| Zone contract | `trusted-host-promotion-zone-contract.md` |
| Implementation-plan skeleton | `trusted-host-promotion-implementation-plan.md` |
| Conflict negative transcripts | `trusted-host-promotion-negative-fixtures.md` and future transcript generator |
| Replay negative transcripts | `trusted-host-promotion-negative-fixtures.md` and future transcript generator |
| Path escape negative transcripts | `trusted-host-promotion-negative-fixtures.md` and future transcript generator |
| External/source review | future source-review handoff and disposition |

## Allowed Future Decision Outcomes

A future post-RC decision may choose only one of these outcomes:

- `go_for_promotion_state_machine_planning`: continue design, contract, fixture, and review-packet
  work only.
- `conditional_go_for_promotion_implementation_planning`: approve one exact implementation plan for
  later review, without enabling runtime behavior.
- `conditional_go_for_bounded_promotion_implementation`: approve one exact trusted-host promotion
  implementation only after all preconditions above are proven and reviewed.
- `no_go`: keep the lane blocked and require additional review evidence.

Any outcome other than `no_go` must still keep host promotion disabled unless a separate
implementation decision explicitly authorizes the exact runtime path.

## Required Negative Evidence

Before implementation, evidence must show denial or safe warning behavior for:

- missing promotion state, missing approval ID, missing artifact hash, or missing zone label;
- source hash mismatch, staging hash mismatch, approved-output hash mismatch, stale artifact, and
  changed artifact after approval;
- reused approval, reused promotion ID, stale request hash, expired approval, wrong principal, wrong
  workspace, wrong manifest hash, wrong policy hash, and wrong schema/tool version;
- absolute, parent-traversal, URL, encoded traversal, Unicode ambiguity, control-character, hidden,
  `.git`, symlink, hardlink, directory, binary, unsupported type, and broad archive-extraction
  targets;
- existing target conflict, overwrite request, delete request, move request, chmod request, and
  automatic promotion request;
- raw file content, prompt, diff, response body, token, private key, raw host path, environment
  value, dependency name, package script value, VM log, shell output, or raw sandbox-internal display.

## Current Allowed State

Current artifacts may reference this intake as a future decision checklist only. Today this intake
allows docs, state-machine sketches, evidence contracts, static fixtures, review packets,
source-review questions, and operator warnings. It does not approve runtime behavior.

The state-machine sketch is recorded in
[trusted-host-promotion-state-machine.md](trusted-host-promotion-state-machine.md) and validated
with `make trusted-host-promotion-state-machine-check`.
The negative fixture contract is recorded in
[trusted-host-promotion-negative-fixtures.md](trusted-host-promotion-negative-fixtures.md) and
validated with `make trusted-host-promotion-negative-fixtures-check`.
The zone contract is recorded in
[trusted-host-promotion-zone-contract.md](trusted-host-promotion-zone-contract.md) and validated
with `make trusted-host-promotion-zone-contract-check`.
The implementation-plan skeleton is recorded in
[trusted-host-promotion-implementation-plan.md](trusted-host-promotion-implementation-plan.md) and
validated with `make trusted-host-promotion-implementation-plan-check`.

Current output must continue to report:

- decision record required: `true`;
- implementation approved: `false`;
- runtime changes allowed: `false`;
- trusted-host promotion allowed: `false`;
- direct host writes allowed: `false`;
- overwrite/delete/move allowed: `false`;
- broad archive extraction allowed: `false`;
- automatic promotion allowed: `false`;
- promotion without exact artifact hash binding allowed: `false`;
- promotion without approval evidence allowed: `false`;
- Mission Control runtime allowed: `false`;
- local model invocation allowed: `false`;
- sandbox orchestration allowed: `false`;
- SIEM adapter allowed: `false`;
- new power classes allowed: `false`;
- public/security-product positioning allowed: `false`.
