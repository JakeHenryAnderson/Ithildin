# Trusted-Host Promotion Limited Runtime Ticket

Status: limited-runtime implementation-ticket skeleton for `ERG-005`.

Decision ID: `PRD-TRUSTED-HOST-LIMITED-RUNTIME-TICKET-001`.

Current governed tool count: `24`.

Current `ERG-005` status: `ready_for_limited_runtime_ticket_skeleton`.

Current selected capability: `not selected`.

Run:

```sh
make trusted-host-promotion-limited-runtime-ticket-check
```

This ticket turns the limited runtime plan into a concrete future sprint boundary. It does not add
runtime behavior, does not approve runtime implementation, does not approve trusted-host promotion,
and does not close `ERG-005`.

## Strict Stop Rule

Stop before implementation if the future ticket stops being exactly:

```text
one stored sandbox artifact -> one operator-approved host staging placement -> one read-only evidence record
```

Stop and reassess if the implementation surface becomes ambiguous, if useful behavior appears to
require broader host writes, if destination labels cannot be made precise, if a gate fails three
times for the same reason, if a critical/high trust-boundary issue appears, or if the next change
would alter Ithildin's product boundary.

Allowed reassessment outcomes are:

- narrow this ticket and rerun the ticket gate;
- request focused High or XHigh internal source review;
- prepare an external review packet for GPT 5.5 Pro or a human reviewer;
- defer trusted-host promotion and pivot to a lower-risk enterprise lane;
- mark the lane `blocked` or `accepted_deferred` with a committed decision record.

Do not keep adding documentation, gates, or packet polish if the implementation milestone is no
longer getting clearer.

## Preconditions

The future implementation ticket depends on these already-checked artifacts:

- `docs/codex/sandbox-promotion-evidence-contract.md`
- `docs/codex/trusted-host-descriptor-contract.md`
- `docs/codex/trusted-host-promotion-decision-intake.md`
- `docs/codex/trusted-host-promotion-state-machine.md`
- `docs/codex/trusted-host-promotion-negative-fixtures.md`
- `docs/codex/trusted-host-promotion-zone-contract.md`
- `docs/codex/trusted-host-promotion-implementation-plan.md`
- `docs/codex/trusted-host-promotion-source-review.md`
- `docs/codex/v3-trusted-host-promotion-internal-review.md`
- `docs/codex/trusted-host-promotion-implementation-gate-decision.md`
- `docs/codex/trusted-host-promotion-limited-runtime-plan.md`

The Goal C decision outcome must remain:

```text
ready_for_limited_runtime_implementation_plan
```

The limited runtime plan status must remain:

```text
ready_for_limited_runtime_implementation_plan
```

## Future Implementation Boundary

A later explicit implementation sprint may implement only this staging-only slice:

- create a stored promotion proposal for one existing sandbox artifact;
- bind the proposal to one response-local artifact ID and one artifact SHA-256;
- bind one operator-reviewed destination label from a trusted host descriptor;
- require one one-time approval before placement;
- create at most one promotion attempt per approval ID;
- copy one artifact into one bounded host staging zone;
- verify the staged copy SHA-256 matches the approved artifact SHA-256;
- record one read-only evidence record and safe audit metadata;
- expose read-only diagnostics for `clean`, `recovery_required`, `ambiguous`, `expired`, `replayed`,
  `stale_evidence`, and `blocked_by_policy_or_manifest_drift`.

The future implementation must not create an `approved://` transition, overwrite existing host
content, delete host content, move host content, chmod files, extract archives, merge directories,
recursively copy trees, promote arbitrary paths, promote multiple artifacts per approval, or
automatically promote anything.

## Required Future Runtime Surfaces

If later approved, the implementation sprint must name and test each selected surface:

- stored promotion proposal schema and persistence;
- one-time approval binding and compare-and-set consumption;
- promotion attempt store and phase transitions;
- trusted host descriptor destination-label resolver;
- staging-only placement function;
- post-placement hash verification;
- read-only diagnostics function;
- safe audit metadata shape;
- review-console display labels if any UI is touched.

This ticket does not choose the final API, UI, storage table, audit event name, or approval route.
Those decisions belong to the later runtime implementation sprint and must be tested in that sprint.

## Required Evidence Binding

Any future implementation must bind:

- `tool_name`;
- `promotion_request_id`;
- `promotion_proposal_id`;
- `promotion_attempt_id`;
- `proposal_hash`;
- `request_hash`;
- `one_time_scope_hash`;
- `workspace_id`;
- `sandbox_descriptor_id`;
- trusted host descriptor ID and descriptor hash;
- source zone label;
- host staging zone label;
- response-local artifact ID;
- artifact SHA-256;
- artifact size in bytes;
- artifact media label;
- expected post-placement SHA-256;
- manifest hash and version;
- policy engine, policy hash, policy version, and policy document version;
- matched policy rules and obligation keys;
- requesting principal;
- approving principal;
- approval expiry;
- schema/tool input version;
- implementation-gate commit and reviewed packet hash.

Before placement, the executor must revalidate proposal hash, artifact hash, workspace binding,
sandbox descriptor hash, trusted host descriptor hash, source label, destination label, manifest
hash/version, policy hash/version where required, schema/tool input version, principal binding,
approval status, approval expiry, and one-time scope hash.

## Required Future Negative Tests

The future implementation sprint must include tests or negative transcripts for:

- missing approval;
- expired approval;
- replayed approval;
- approval scope mismatch;
- wrong tool name;
- wrong principal;
- disabled or unknown principal;
- disabled workspace;
- stale artifact hash;
- changed destination label;
- changed trusted host descriptor hash;
- policy drift;
- manifest drift;
- schema/tool input drift;
- path traversal;
- encoded traversal;
- absolute path;
- hidden/sensitive destination;
- `.git` destination;
- symlink;
- hardlink;
- directory target;
- existing destination conflict;
- overwrite/delete/move attempt;
- archive extraction attempt;
- oversized artifact;
- binary or unsupported artifact label;
- raw path leakage attempt;
- file-content leakage attempt;
- package script, dependency name, environment name/value, registry URL, private key, prompt, model
  response, VM log, shell output, stack trace, or secret marker leakage attempt.

## Required Future Acceptance Evidence

The future implementation sprint must produce:

- a separate implementation decision that explicitly allows only the staging-only slice;
- closed schema validation for promotion proposal input;
- one happy-path fixture for a small UTF-8 text artifact;
- negative fixtures for every required future negative test;
- policy preview/runtime resource parity evidence;
- audit metadata evidence with hashes, IDs, labels, counts, and redaction status only;
- read-only diagnostics evidence for incomplete or ambiguous attempts;
- source-review handoff using a dedicated `EXT-TRUSTED-HOST-RUNTIME-###` finding namespace;
- release/readiness wiring that keeps governed tool count at `24` unless a separate approved
  capability changes it;
- no-new-powers and tool-surface invariant evidence.

## Explicit Non-Approvals

This ticket does not approve:

- runtime implementation in this checkpoint;
- runtime trusted-host promotion;
- direct host writes;
- overwrite/delete/move behavior;
- broad archive extraction;
- automatic promotion;
- promotion without exact artifact hash binding;
- promotion without approval evidence;
- arbitrary host paths;
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

Stop before runtime work if the staging-only implementation requires direct host writes outside an
operator-approved staging zone, overwrite/delete/move behavior, multiple artifacts per approval,
automatic promotion, raw host paths in evidence, archive extraction, Mission Control runtime
authority, local model invocation, VM/container lifecycle control, sandbox orchestration, SIEM
adapter behavior, production identity, runtime Postgres, hosted telemetry, remote MCP, new governed
powers, stronger product claims, or unbounded raw evidence storage.

Escalate to High review first for repeated gate failures or unclear implementation boundaries.
Escalate to XHigh or GPT 5.5 Pro / human review only if a critical/high finding appears or the
product boundary remains ambiguous after High review.

## Validation

Run:

```sh
make trusted-host-promotion-implementation-gate-decision-check
make trusted-host-promotion-limited-runtime-plan-check
make trusted-host-promotion-limited-runtime-ticket-check
make no-new-powers-guardrail
make tool-surface-invariant-gate
```

The normal release gates must still pass. Tool count must remain `24`.
