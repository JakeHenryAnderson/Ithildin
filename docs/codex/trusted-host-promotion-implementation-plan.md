# Trusted-Host Promotion Implementation Plan Skeleton

Status: implementation-planning skeleton for `ERG-005` and `PRD-TRUSTED-HOST-001`.

Current governed tool count: `24`.

Current `ERG-005` status: `blocked`.

Current selected capability: `not selected`.

This packet defines the minimum shape of a future implementation plan for trusted-host artifact
promotion. It does not approve runtime behavior, direct host writes, overwrite/delete/move behavior,
broad archive extraction, automatic promotion, promotion without exact artifact hash binding,
promotion without approval evidence, API/MCP behavior, Mission Control runtime behavior, local model
invocation, VM/container lifecycle management, sandbox orchestration, SIEM adapters, production
identity, runtime Postgres, hosted telemetry, shell, Docker/Kubernetes/browser governed powers,
arbitrary HTTP, broad filesystem writes, compliance automation, or public/security-product claims.

Validate this implementation-plan skeleton with:

```sh
make trusted-host-promotion-implementation-plan-check
```

## Required Inputs

A future implementation plan must cite and satisfy all of these existing artifacts before it can ask
for runtime approval:

| Required artifact | Required evidence |
| --- | --- |
| Promotion evidence contract | `sandbox-promotion-evidence-contract.md` |
| Trusted host descriptor contract | `trusted-host-descriptor-contract.md` |
| Decision intake | `trusted-host-promotion-decision-intake.md` |
| State machine | `trusted-host-promotion-state-machine.md` |
| Negative fixture contract | `trusted-host-promotion-negative-fixtures.md` |
| Zone contract | `trusted-host-promotion-zone-contract.md` |
| Post-RC decision gate | `post-rc-decision-gate.md` and `post-rc-decision-register.md` |
| External/source review | future source-review handoff and favorable disposition |
| Release readiness | future focused tests, negative transcripts, packet redaction scan, and release-check wiring |

No future implementation plan may skip the trusted host descriptor contract, decision intake, state
machine, negative fixtures, zone contract, external/source review, or release readiness evidence.

## Future Runtime Shape

If a later decision record approves implementation, the only future runtime shape this skeleton
allows planning for is:

```text
sandbox://artifact -> host-staging://artifact -> approved://artifact
```

The future implementation must be one artifact, one approval, one promotion attempt, and one bounded destination label. Runtime planning must keep raw filesystem paths out of operator-facing evidence and must model labels as evidence identifiers until a separately reviewed storage resolver binds them to exact safe locations.

Any future tool or endpoint proposal must be reviewed as a new power-bearing surface. This skeleton
does not approve a manifest, executor, policy rule, API route, MCP exposure, UI action, Mission
Control action, local model action, sandbox orchestration action, or SIEM adapter.

## Required Future Components

A future implementation plan must define:

- an exact artifact hash-binding model for source artifact, host staging artifact, and approved
  host artifact;
- an approval binding model for approval ID, request hash, one-time scope hash, approval expiry,
  source label, staging label, approved label, policy hash, manifest hash, operator principal,
  workspace ID, sandbox ID, schema/tool version, and reviewed packet commit;
- an attempt store with compare-and-set state transitions and one attempt per approval ID;
- a read-only diagnostic model for incomplete or recovery-required attempts;
- a safe storage resolver that rejects arbitrary host paths, hidden paths, `.git`, symlinks,
  hardlinks, directories, unsupported file types, binary targets, archive extraction, absolute paths,
  parent traversal, encoded traversal, URL-shaped labels, Unicode ambiguity, and control characters;
- an atomic placement model that cannot overwrite, delete, move, chmod, merge directories, or recursively copy;
- negative transcripts for conflict, replay, stale evidence, unsafe labels, path escape, sensitive
  payloads, and product-boundary overclaims;
- audit evidence limited to labels, hashes, IDs, state labels, decision labels, and safe counts;
- rollback/reconciliation non-goals unless a separate decision record approves a mutating recovery
  design.

## Implementation Gate Preconditions

Before any future implementation gate may report `implementation approved: true`, the future plan
must prove:

- `make trusted-host-promotion-decision-intake-check` passes;
- `make trusted-host-promotion-state-machine-check` passes;
- `make trusted-host-promotion-negative-fixtures-check` passes;
- `make trusted-host-promotion-zone-contract-check` passes;
- `make trusted-host-promotion-implementation-plan-check` passes;
- a future source-review bundle exists for the exact implementation surface;
- a favorable external/source-review disposition exists for that exact surface;
- negative transcript generation covers the future runtime path;
- packet redaction scan finds no raw host paths, file contents, prompts, diffs, response bodies,
  secrets, VM logs, shell output, package script values, dependency names, environment names or
  values, registry URLs, private keys, stack traces, or raw sandbox-internal paths;
- `make release-check` includes the new runtime checks after implementation.

The current design/source-review handoff is
[`trusted-host-promotion-source-review.md`](trusted-host-promotion-source-review.md), generated by
`make trusted-host-promotion-source-review-packet`. That handoff can disposition whether planning
may continue, but it does not satisfy the future source review required for an exact runtime
implementation surface.

## Product-Boundary Stop Conditions

Stop the implementation-planning lane and require a new post-RC decision record if the plan needs:

- arbitrary host paths;
- raw filesystem path exposure;
- promotion without staging;
- promotion without exact hash binding;
- promotion without approval evidence;
- automatic, batch, wildcard, recursive, overwrite, delete, move, chmod, directory merge, or broad
  archive extraction behavior;
- shell, Docker, Kubernetes, browser automation, arbitrary HTTP, network expansion, production identity,
  runtime Postgres, hosted telemetry, remote MCP, sandbox orchestration, Mission Control runtime
  action, local model invocation, SIEM adapter behavior, or compliance automation;
- public/security-product positioning.

## Current Implementation Boundary

This skeleton is a planning and review artifact. Current runtime/demo evidence may only report
`promotion_status: not_promoted`. This skeleton does not implement a tool, endpoint, executor,
policy rule, approval mutation, diagnostics endpoint, storage resolver, host placement, rollback,
repair, Mission Control runtime action, local model action, sandbox orchestration, or SIEM adapter.

Current outputs must continue to report:

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
