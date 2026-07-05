# Trusted-Host Promotion Limited Runtime Plan

Status: limited runtime implementation-plan checkpoint for `ERG-005`.

Decision ID: `PRD-TRUSTED-HOST-LIMITED-RUNTIME-PLAN-001`.

Current governed tool count: `24`.

Current `ERG-005` status: `ready_for_limited_runtime_implementation_plan`.

Current selected capability: `not selected`.

Run:

```sh
make trusted-host-promotion-limited-runtime-plan-check
```

This plan is the next artifact after the Goal C implementation-gate decision. It defines the exact
shape a future limited runtime implementation may ask to build, but it does not approve runtime
implementation, trusted-host promotion, direct host writes, overwrite/delete/move behavior, broad
archive extraction, automatic promotion, Mission Control runtime behavior, local model invocation,
VM/container lifecycle management, sandbox orchestration, SIEM adapter behavior, production
identity, runtime Postgres, hosted telemetry, remote MCP, shell/Docker/Kubernetes/browser governed
powers, arbitrary HTTP, broad filesystem writes, compliance automation, plugin SDK behavior, new
governed tool powers, or public/security-product positioning. Runtime trusted-host promotion
remains blocked.

## Strict Operating Rule

This lane must stop instead of grinding if the work stops clearly advancing the milestone. If the
implementation surface becomes ambiguous, if useful behavior appears to require broader host writes,
if a gate fails three times for the same reason, if a critical/high trust-boundary issue appears, or
if the next change would alter Ithildin's product boundary, stop and reassess before doing more work.

Allowed reassessment outcomes are:

- tighten this plan and rerun the limited-plan gate;
- request a focused High/XHigh internal source review;
- prepare an external review packet for GPT 5.5 Pro or a human reviewer;
- defer trusted-host promotion and pivot to a lower-risk enterprise lane;
- mark the lane `blocked` or `accepted_deferred` with a committed decision record.

Do not keep adding documentation, gates, or packet polish if the milestone is no longer getting
clearer. The correct behavior at that point is to pause, report the current commit, dirty state,
failing command, suspected ambiguity, and recommended next options.

## Allowed First Runtime Slice

The only runtime slice this plan may prepare is:

```text
one stored sandbox artifact -> one operator-approved host staging placement -> one read-only evidence record
```

The first slice is staging-only. It must not create an `approved://` transition, overwrite existing
host content, delete host content, move host content, chmod files, extract archives, merge
directories, recursively copy trees, promote arbitrary paths, or automatically promote anything.

The future runtime surface, if separately approved later, must be limited to:

- one generated promotion proposal;
- one one-time approval;
- one promotion attempt per approval ID;
- one artifact hash;
- one source zone label;
- one host staging zone label;
- one bounded destination label resolved by an operator-reviewed trusted host descriptor;
- read-only diagnostics after failures or ambiguous states.

No implementation may be started from this plan unless a later implementation gate explicitly
authorizes a specific runtime slice.

## Future Interfaces Under Review

The future implementation may propose these surfaces only after a separate implementation gate:

| Future surface | Allowed future role | Still blocked now |
| --- | --- | --- |
| Stored promotion proposal | Create immutable promotion evidence for review | Runtime proposal creation |
| One-time approval binding | Bind exact proposal, artifact, destination, policy, manifest, and principal evidence | Approval consumption for promotion |
| Promotion attempt store | Record phases and recovery evidence | Any runtime write/placement |
| Host staging placement | Copy one artifact to a bounded staging destination | Direct host writes today |
| Read-only diagnostics | Report `clean`, `recovery_required`, `ambiguous`, or `blocked` | Mutating repair/retry/rollback |
| Audit evidence | Record labels, hashes, IDs, decisions, redaction status, and safe counts | File contents or raw host paths |

Any MCP tool, API endpoint, UI action, Mission Control action, local model action, sandbox
orchestration action, SIEM adapter, production identity integration, runtime Postgres feature, or
remote MCP behavior remains out of scope unless a later separate post-RC decision explicitly starts
that lane.

## Required Future Evidence Binding

A future promotion proposal and approval must bind all of the following before any placement is
attempted:

- `tool_name`;
- `promotion_request_id`;
- `promotion_proposal_id`;
- `promotion_attempt_id` after execution starts;
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

Before any future placement attempt, the executor must revalidate proposal hash, artifact hash,
workspace binding, sandbox descriptor hash, trusted host descriptor hash, source label, destination
label, manifest hash/version, policy hash/version where required, schema/tool input version,
principal binding, approval status, approval expiry, and one-time scope hash.

Any mismatch, missing evidence, stale artifact hash, disabled workspace, missing descriptor, wrong
tool, wrong principal, wrong destination, expired approval, replay attempt, policy drift, manifest
drift, schema drift, or ambiguous path/label must fail closed before placement.

## Destination And Storage Constraints

A future resolver may accept only operator-reviewed destination labels. It must reject:

- arbitrary host paths;
- absolute paths;
- parent traversal;
- encoded traversal;
- URL-shaped labels outside explicitly allowed zone labels;
- hidden or sensitive destinations;
- `.git` internals;
- symlinks;
- hardlinks;
- directories;
- archive files that require extraction;
- broad archive extraction;
- binary or unsupported media labels;
- oversized artifacts;
- Unicode normalization ambiguity;
- control characters;
- casefold ambiguity;
- overwrite, delete, move, chmod, recursive copy, merge, or append semantics.
- shell/Docker/Kubernetes/browser governed powers.

The future destination resolver must keep raw host paths out of user-facing API responses, audit
events, packet evidence, and generated docs unless a later source review approves a more specific
redaction/display contract. Safe labels, IDs, hashes, counts, and warning codes are allowed.

## State Machine Requirements

The future state machine must preserve these phase boundaries:

```text
proposed -> approval_required -> approved -> preparing -> placing_to_staging
  -> placed_to_staging -> verified -> completed
```

Failure states must include:

```text
rejected
failed_before_placement
recovery_required
ambiguous
expired
replayed
stale_evidence
blocked_by_policy_or_manifest_drift
```

Approval consumption and attempt creation must be compare-and-set guarded so concurrent calls cannot
consume the same approval twice or create more than one attempt for a single approval ID.

If failure occurs before placement, the future system must preserve no-partial-write behavior and
record a safe failed attempt. If failure occurs after placement but before full completion, the
future system must record `recovery_required` or `ambiguous` when possible and expose only
read-only diagnostics. It must not mark the promotion as cleanly completed unless proposal,
approval, placement verification, and audit completion have all succeeded.

## Negative Fixtures Required Before Implementation

A later implementation sprint must add negative fixtures or transcripts for:

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

## Source Review And Pivot Gate

Before implementation, create a focused source-review packet for this exact limited runtime surface.
The review prompt must ask whether the future runtime slice may be implemented for local-preview
testing only. It must not ask for public/security-product positioning, production identity,
compliance claims, broad host access, Mission Control runtime authority, sandbox orchestration, SIEM
adapter behavior, or any new power class.

Implementation must not start if:

- the reviewer finds a critical/high issue;
- the reviewer says the proposal needs broader host writes;
- the reviewer says destination labels are too ambiguous;
- the reviewer cannot distinguish staging-only placement from approved host promotion;
- the reviewer says the evidence cannot support useful recovery diagnostics;
- the plan cannot be validated by deterministic gates.

If any of those happen, the lane should pivot to remediation, deferral, or external consultation
rather than accumulating more low-value packet polish.

## Validation Expectations

This plan is valid only if all of these remain true:

- tool count remains `24`;
- selected capability remains `not selected`;
- `make trusted-host-promotion-implementation-gate-decision-check` passes;
- `make trusted-host-promotion-implementation-plan-check` passes;
- `make trusted-host-promotion-state-machine-check` passes;
- `make trusted-host-promotion-negative-fixtures-check` passes;
- `make trusted-host-promotion-zone-contract-check` passes;
- `make no-new-powers-guardrail` passes;
- `make tool-surface-invariant-gate` passes;
- no live normalized external response is required;
- runtime implementation remains false;
- trusted-host promotion remains false;
- direct host writes remain false;
- automatic promotion remains false;
- Mission Control runtime remains false;
- sandbox orchestration remains false;
- new governed tool powers remain false.

## Next Possible Sprint

If this limited runtime plan stays green, the next possible sprint is not implementation by default.
The next sprint should either:

1. generate the focused limited-runtime source-review packet; or
2. draft the implementation ticket and gate skeleton while still keeping runtime code blocked.

Choose option 1 if there is any ambiguity. Choose option 2 only if the boundaries are still crystal
clear after this check.
