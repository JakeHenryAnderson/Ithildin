# Trusted-Host Promotion Runtime Implementation Decision

Status: implementation-gate decision draft for the future `ERG-005` staging-only runtime slice.

Decision ID: `PRD-TRUSTED-HOST-RUNTIME-IMPLEMENTATION-001`.

Current governed tool count: `24`.

Current `ERG-005` status: `ready_for_runtime_implementation_gate_skeleton`.

Current selected capability: `not selected`.

Run:

```sh
make trusted-host-promotion-runtime-implementation-decision-check
```

This decision draft names the exact runtime surfaces that may be considered in a later
implementation sprint. It does not add runtime behavior in this checkpoint and does not close
`ERG-005`.

## Preconditions

The implementation decision depends on these already-checked artifacts:

- `docs/codex/trusted-host-promotion-implementation-gate-decision.md`
- `docs/codex/trusted-host-promotion-limited-runtime-plan.md`
- `docs/codex/trusted-host-promotion-limited-runtime-ticket.md`
- `docs/codex/trusted-host-promotion-state-machine.md`
- `docs/codex/trusted-host-promotion-negative-fixtures.md`
- `docs/codex/trusted-host-promotion-zone-contract.md`
- `docs/codex/sandbox-promotion-evidence-contract.md`

The limited runtime ticket status must remain:

```text
ready_for_limited_runtime_ticket_skeleton
```

## Approved Future Runtime Slice

A later implementation sprint may implement only this staging-only slice:

```text
one stored sandbox artifact -> one operator-approved host staging placement -> one read-only evidence record
```

The allowed future runtime implementation may include:

- closed promotion proposal schema;
- local SQLite-backed promotion proposal records;
- local SQLite-backed promotion attempt records;
- one-time approval binding and compare-and-set approval consumption;
- trusted host staging destination labels resolved from an operator-reviewed descriptor;
- copy-only placement of one approved artifact into one staging zone;
- post-placement SHA-256 verification;
- read-only diagnostics for incomplete, failed, or ambiguous attempts;
- safe audit metadata containing IDs, labels, hashes, counts, redaction status, and policy/manifest
  evidence;
- negative transcript generation for rejected promotion cases;
- source-review handoff packet using `EXT-TRUSTED-HOST-RUNTIME-###` finding IDs.

## Required Future Acceptance Evidence

A later implementation sprint must prove:

- schema validation rejects unknown fields;
- proposal and approval evidence bind exact artifact SHA-256, destination label, workspace, sandbox
  descriptor, trusted host descriptor, principal, policy, manifest, expiry, and one-time scope;
- replayed approvals and concurrent promotion attempts fail closed;
- stale artifact hash, changed destination label, policy drift, manifest drift, and schema drift fail
  before placement;
- destination resolution rejects arbitrary host paths, absolute paths, parent traversal, encoded
  traversal, hidden/sensitive paths, `.git`, symlinks, hardlinks, directories, archive extraction,
  overwrite/delete/move/chmod behavior, and recursive copy;
- successful placement verifies the staged file SHA-256 against the approved artifact SHA-256;
- failure after placement records `recovery_required` or `ambiguous` diagnostics without mutating
  repair;
- outputs and audit metadata contain no file contents, diffs, raw host paths, package scripts,
  dependency names, environment names or values, registry URLs, prompts, model responses, VM logs,
  shell output, stack traces, private keys, or secret markers;
- no MCP tool, new governed tool, Mission Control runtime authority, sandbox orchestration, local
  model invocation, network expansion, SIEM adapter runtime behavior, production identity, runtime
  Postgres, hosted telemetry, remote MCP, compliance automation, or public/security-product
  positioning is introduced.

## Explicit Non-Approvals

This decision draft does not approve:

- runtime implementation in this checkpoint;
- promotion beyond a staging-only destination;
- direct arbitrary host writes;
- overwrite/delete/move behavior;
- chmod behavior;
- broad archive extraction;
- recursive copy or directory merge behavior;
- automatic promotion;
- promotion without exact artifact hash binding;
- promotion without one-time approval evidence;
- raw host path exposure;
- Mission Control runtime behavior;
- local model invocation by Ithildin;
- VM/container lifecycle management;
- sandbox orchestration;
- SIEM adapter runtime behavior;
- production identity;
- runtime Postgres;
- hosted telemetry;
- remote MCP;
- compliance automation;
- shell, Docker, Kubernetes, or browser governed powers;
- arbitrary HTTP;
- broad filesystem writes;
- plugin SDK behavior;
- new governed tool powers;
- public/security-product positioning.

## Stop Conditions

Stop before runtime work if implementation requires arbitrary host paths, more than one artifact per
approval, overwrite/delete/move/chmod behavior, archive extraction, recursive copy, automatic
promotion, Mission Control runtime authority, local model invocation, VM/container lifecycle
control, sandbox orchestration, SIEM adapter behavior, production identity, runtime Postgres, hosted
telemetry, remote MCP, new governed powers, stronger product claims, or unbounded raw evidence
storage.

Escalate to High review first for repeated gate failures or unclear implementation boundaries.
Escalate to XHigh or GPT 5.5 Pro / human review only if a critical/high finding appears or the
product boundary remains ambiguous after High review.

## Validation

Run:

```sh
make trusted-host-promotion-limited-runtime-ticket-check
make trusted-host-promotion-runtime-implementation-decision-check
make no-new-powers-guardrail
make tool-surface-invariant-gate
```

The normal release gates must still pass. Tool count must remain `24`.
