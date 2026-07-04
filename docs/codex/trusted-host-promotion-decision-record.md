# Trusted-Host Promotion Decision Record

Status: committed decision record for `ERG-005` implementation-planning-only continuation.

Decision ID: `PRD-TRUSTED-HOST-001`.

Current governed tool count: `24`.

Previous `ERG-005` status: `blocked`.

Recorded `ERG-005` status: `ready_for_implementation_planning_only`.

Current selected capability: `not selected`.

Run:

```sh
make trusted-host-promotion-decision-record-check
```

This record applies Ithildin's internal design/source-review evidence for the trusted-host artifact
promotion lane. It authorizes only an implementation-planning-only phase for a future, separately
reviewed trusted-host promotion proposal. It does not approve runtime implementation, trusted-host
promotion, host writes, overwrite/delete/move behavior, broad archive extraction, automatic
promotion, promotion without exact artifact hash binding, promotion without approval evidence,
Mission Control runtime behavior, local model invocation, VM/container lifecycle management,
sandbox orchestration, SIEM adapter behavior, production identity, runtime Postgres, hosted
telemetry, remote MCP, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad
filesystem writes, compliance automation, new governed tool powers, or public/security-product
positioning.

## Reviewed Inputs

- Reviewer: Codex internal design/source review.
- Reviewer type: internal AI manager review.
- Reviewed commit: `71fb9d6339033369a4edfee4ea9524b2ab7b1a51`.
- Reviewed packet path: `var/review-packets/v3/trusted-host-promotion-external-review`.
- Reviewed area: `trusted-host-promotion`.
- Finding namespace: `EXT-TRUSTED-HOST-###`.
- Internal review: `docs/codex/v3-trusted-host-promotion-internal-review.md`.
- Descriptor contract: `docs/codex/trusted-host-descriptor-contract.md`.
- Decision intake: `docs/codex/trusted-host-promotion-decision-intake.md`.
- State machine: `docs/codex/trusted-host-promotion-state-machine.md`.
- Negative fixture contract: `docs/codex/trusted-host-promotion-negative-fixtures.md`.
- Zone contract: `docs/codex/trusted-host-promotion-zone-contract.md`.
- Implementation-plan skeleton: `docs/codex/trusted-host-promotion-implementation-plan.md`.
- Source-review handoff: `docs/codex/trusted-host-promotion-source-review.md`.

No normalized external response is recorded for this decision. The ignored response path
`var/review-runs/trusted-host-promotion/normalized-response.json` remains absent in normal release
gates, and `make trusted-host-promotion-disposition-closure-check` remains fail-closed unless a
future real reviewer response is normalized.

## Closure Evidence

Current committed evidence shows:

- `make trusted-host-descriptor-contract-check` reports `runtime_changes_allowed: false`,
  `trusted_host_promotion_allowed: false`, and `host_registry_mutation_allowed: false`.
- `make trusted-host-promotion-decision-intake-check` reports `implementation_approved: false`,
  `runtime_changes_allowed: false`, and `trusted_host_promotion_allowed: false`.
- `make trusted-host-promotion-state-machine-check` reports `current_runtime_state:
  not_promoted`.
- `make trusted-host-promotion-negative-fixtures-check` rejects 24 future negative cases.
- `make trusted-host-promotion-zone-contract-check` validates only non-authoritative
  `sandbox://`, `host-staging://`, `approved://`, and `evidence://` labels.
- `make trusted-host-promotion-implementation-plan-check` validates a planning skeleton while
  keeping runtime implementation and host promotion blocked.
- `make trusted-host-promotion-source-review-packet-check` validates the ERG-005 handoff packet
  and `EXT-TRUSTED-HOST-###` finding namespace.
- `make trusted-host-promotion-internal-review-check` records zero findings and `continue_design_only`.
- `make no-new-powers-guardrail` and `make tool-surface-invariant-gate` keep the tool count at
  `24` and report no new power classes.

## Decision Outcome

The approved committed outcome is:

```text
approved_for_implementation_planning_only
```

The approved lane movement is:

```text
ERG-005: blocked -> ready_for_implementation_planning_only
```

That movement means only that a more precise implementation-planning packet may now be drafted for
a future trusted-host promotion proposal. It does not approve runtime implementation.

## Planning Scope

Allowed planning scope:

- implementation-planning document refinement;
- descriptor fixture refinement;
- state-machine transition fixture refinement;
- negative transcript plan;
- exact source/staging/approved/evidence hash-binding plan;
- approval-binding and one-time scope evidence plan;
- stale/replay/conflict/path-escape denial plan;
- safe operator warning language;
- source-review handoff prompt;
- release/readiness gate additions.

## Still Blocked

The following remain blocked after this decision record:

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

## Required Next Step

The next allowed step is to refine the existing planning-only implementation packet:

```text
docs/codex/trusted-host-promotion-implementation-plan.md
```

That packet must remain design/planning only. It must require a later explicit runtime
implementation decision, source review, negative transcripts, release evidence, and review gates
before any trusted-host promotion behavior is implemented.

## Validation

Run:

```sh
make trusted-host-promotion-decision-record-check
make trusted-host-promotion-implementation-plan-check
make trusted-host-promotion-disposition-closure-check
make trusted-host-promotion-response-dry-run
```

Release gates must continue to pass with no live normalized response present.
