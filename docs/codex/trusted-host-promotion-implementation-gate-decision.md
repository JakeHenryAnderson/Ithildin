# Trusted-Host Promotion Implementation-Gate Decision

Status: committed Goal C implementation-gate decision for `ERG-005`.

Decision ID: `PRD-TRUSTED-HOST-GATE-001`.

Current governed tool count: `24`.

Previous `ERG-005` status: `ready_for_implementation_planning_only`.

Recorded Goal C outcome: `ready_for_limited_runtime_implementation_plan`.

Current selected capability: `not selected`.

Run:

```sh
make trusted-host-promotion-implementation-gate-decision-check
```

This decision records that the Goal A implementation-planning contract and Goal B
source-review/runtime-boundary packet are precise enough to prepare a later, limited runtime
implementation plan for trusted-host promotion. It does not approve runtime implementation,
trusted-host promotion, direct host writes, overwrite/delete/move behavior, broad archive
extraction, automatic promotion, promotion without exact artifact hash binding, promotion without
approval evidence, Mission Control runtime behavior, local model invocation, VM/container lifecycle
management, sandbox orchestration, SIEM adapter behavior, production identity, runtime Postgres,
hosted telemetry, remote MCP, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP,
broad filesystem writes, compliance automation, plugin SDK behavior, new governed tool powers, or
public/security-product positioning.

## Decision Inputs

- Reviewed commit: `af434f5afa1cdce9a11ae4cf304079436d635fa7`.
- Goal A contract: `docs/codex/trusted-host-promotion-implementation-plan.md`.
- Goal B runtime-boundary packet: `docs/codex/trusted-host-promotion-source-review.md`.
- Source-review bundle path: `var/review-packets/v3/trusted-host-promotion-external-review`.
- Internal review: `docs/codex/v3-trusted-host-promotion-internal-review.md`.
- Decision intake: `docs/codex/trusted-host-promotion-decision-intake.md`.
- State machine: `docs/codex/trusted-host-promotion-state-machine.md`.
- Negative fixture contract: `docs/codex/trusted-host-promotion-negative-fixtures.md`.
- Zone contract: `docs/codex/trusted-host-promotion-zone-contract.md`.
- Earlier planning decision: `docs/codex/trusted-host-promotion-decision-record.md`.

No normalized external response is recorded for this Goal C decision. The ignored response path
`var/review-runs/trusted-host-promotion/normalized-response.json` remains absent in normal release
gates, and `make trusted-host-promotion-disposition-closure-check` remains fail-closed unless a
future real reviewer response is normalized.

## Decision Criteria

The allowed Goal C outcomes were:

- `blocked`;
- `accepted_deferred`;
- `ready_for_limited_runtime_implementation_plan`.

The selected outcome is:

```text
ready_for_limited_runtime_implementation_plan
```

The allowed lane movement is:

```text
ERG-005: ready_for_implementation_planning_only -> ready_for_limited_runtime_implementation_plan
```

This movement means only that a future implementation-planning sprint may draft the exact limited
runtime surface for review. It does not implement that surface and does not approve any host write.

## Why This Is Ready For A Limited Runtime Plan

The current evidence is sufficiently specific to plan the next artifact:

- the request shape requires exact source artifact identity, source zone, target zone, target label,
  target relative path label, expected artifact hash, requesting principal, workspace ID, approval
  evidence, policy evidence, manifest evidence, and request hash;
- the state machine separates requested, approval-required, approved, executing, promoted,
  failed-before-promotion, recovery-required, and rejected states;
- approval consumption and one-time scope must be modeled before any host placement can happen;
- diagnostics must distinguish no-write, post-placement ambiguous, replay, conflict, stale hash,
  path escape, and denied-zone states without repairing or rewriting host files;
- negative fixtures cover path escape, stale evidence, replay, wrong principal, wrong zone,
  missing hash binding, missing approval evidence, overwrite/delete/move, archive extraction, and
  automatic promotion attempts.

## Still Blocked

The following remain blocked after this Goal C decision:

- runtime implementation;
- trusted-host promotion;
- direct host writes;
- overwrite/delete/move behavior;
- broad archive extraction;
- automatic promotion;
- promotion without exact artifact hash binding;
- promotion without approval evidence;
- Mission Control runtime behavior;
- local model invocation;
- VM/container lifecycle management;
- sandbox orchestration;
- SIEM adapter behavior;
- production identity;
- runtime Postgres;
- hosted telemetry;
- remote MCP;
- shell/Docker/Kubernetes/browser governed powers;
- arbitrary HTTP;
- broad filesystem writes;
- compliance automation;
- plugin SDK behavior;
- new governed tool powers;
- public/security-product positioning.

## Next Allowed Step

The next allowed step is a separate limited runtime implementation-plan sprint. That future plan
must remain a planning artifact unless a later decision explicitly approves code. It must name every
future runtime surface, prove no new power class is being introduced, define closed schemas, bind
approval and artifact hashes, define recovery diagnostics, add negative transcript expectations,
and prepare source-review handoff evidence before any implementation begins.

## Validation

Run:

```sh
make trusted-host-promotion-implementation-gate-decision-check
make trusted-host-promotion-implementation-plan-check
make trusted-host-promotion-source-review-packet-check
make trusted-host-promotion-disposition-closure-check
make trusted-host-promotion-response-dry-run
make no-new-powers-guardrail
make tool-surface-invariant-gate
```

Release gates must continue to pass with no live normalized response present.
