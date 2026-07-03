# Sandbox/VM Live POC Runtime Descriptor-Only Plan

Status: descriptor-only implementation-planning packet for the future `ERG-004` runtime descriptor
slice.

Current governed tool count: `24`.

Current `ERG-004` status: `ready_for_descriptor_only_runtime_implementation_planning`.

Current selected capability: `not selected`.

Run:

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-plan-check
```

This packet translates the internal runtime gate-readiness review into a concrete planning boundary
for a later descriptor-only implementation sprint. It does not add runtime behavior, does not approve
runtime implementation, and does not close `ERG-004`.

## Planning Preconditions

The descriptor-only plan depends on these already-checked artifacts:

- `docs/codex/sandbox-vm-live-poc-runtime-ticket-internal-review.md`
- `docs/codex/sandbox-vm-live-poc-runtime-implementation-gate.md`
- `docs/codex/sandbox-vm-live-poc-runtime-descriptor-contract.md`
- `docs/codex/sandbox-vm-live-poc-runtime-negative-fixtures.md`
- `docs/codex/sandbox-vm-live-poc-runtime-descriptor-contract-internal-review.md`
- `docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-review-bundle.md`
- `docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-internal-review.md`
- `docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton.md`
- `docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-response-application-record.md`
- `docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-response-application-playbook.md`
- `docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-response-application-preflight.md`

The internal gate-readiness review disposition must remain:

```text
approve_internal_runtime_gate_readiness_review
```

## Future Descriptor-Only Slice

A later implementation sprint may plan only this narrow descriptor/correlation slice:

- validate an operator-supplied descriptor object;
- reject unknown descriptor fields;
- reject forbidden source flags or authority claims;
- store only safe labels, hashes, timestamps, enums, booleans, correlation IDs, and status codes;
- render secret-free descriptor status summaries;
- correlate descriptor fields with existing Agent Run, approval, audit, and signed-export evidence;
- emit safe audit metadata for descriptor validation attempts;
- generate negative transcript summaries for rejected descriptor cases;
- generate a source-review handoff packet for the implemented descriptor-only slice.

The descriptor must keep these source facts explicit:

- `descriptor_source: operator_supplied`
- `vm_lifecycle_source: operator_managed`
- `isolation_claim_source: operator_attested`
- `network_posture_source: operator_attested`
- `mount_posture_source: operator_attested`
- `model_client_source: operator_attested`
- `ithildin_live_inspection_performed: false`
- `ithildin_lifecycle_control_performed: false`
- `mission_control_runtime_authority_used: false`
- `trusted_host_promotion_performed: false`

## Future Runtime Surfaces To Decide Later

This plan does not approve any runtime surface. A later implementation sprint must explicitly decide
whether the descriptor-only slice needs any of these, and must add a new implementation gate before
touching them:

- API route for descriptor submission or status;
- UI rendering of descriptor status;
- database table or local file persistence for descriptor records;
- Agent Run correlation fields;
- audit event shape for descriptor validation;
- source-review bundle generator for the implemented descriptor slice.

No MCP tool, governed tool manifest, executor, policy rule, approval behavior, Mission Control
runtime behavior, VM/container lifecycle behavior, or live inspection behavior is approved here.

## Required Future Tests

A later implementation sprint must include tests for:

- missing required descriptor fields;
- unknown descriptor fields;
- invalid `descriptor_source`;
- invalid `vm_lifecycle_source`;
- invalid `ithildin_live_inspection_performed`;
- invalid `ithildin_lifecycle_control_performed`;
- invalid `mission_control_runtime_authority_used`;
- invalid `trusted_host_promotion_performed`;
- stale or mismatched `vm_profile_hash`;
- mismatched `sandbox_profile_id`;
- unsafe `mount_root_label`;
- unexpected `network_posture_label`;
- missing `run_id`;
- mismatched `workspace_id`, `principal_id`, or `run_id`;
- missing approval correlation where required;
- missing audit correlation where required;
- missing signed-export correlation where required;
- attempted VM/container lifecycle management by Ithildin;
- attempted live VM/container inspection by Ithildin;
- attempted local model invocation by Ithildin;
- attempted Mission Control execution, approval, policy, or audit authority;
- attempted trusted-host promotion;
- attempted host write or artifact promotion;
- arbitrary network expansion;
- API/MCP profile loading;
- shell/Docker/Kubernetes/browser execution;
- cleanup failure;
- missing or mismatched `failure_transcript_hash`;
- packet hash mismatch;
- raw secret, prompt, model response, file content, diff, transcript, dependency name, package
  script value, raw path, directory listing, environment value, registry URL, command line, or shell
  output leakage.

## Explicit Non-Approvals

This plan does not approve:

- runtime implementation;
- live VM/container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- Mission Control runtime behavior;
- local model invocation by Ithildin;
- trusted-host promotion;
- host writes or artifact promotion;
- network expansion;
- API/MCP profile loading;
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

Stop before implementation if the future descriptor-only slice requires VM lifecycle authority, live
inspection, local model invocation, Mission Control runtime authority, trusted-host promotion, host
writes, network expansion, API/MCP profile loading, new governed powers, or stronger product claims.

Escalate to High review first if repeated gate failures or unclear implementation boundaries appear.
Escalate to XHigh or GPT 5.5 Pro / human review only if a critical/high finding appears or the
product boundary remains ambiguous after High review.

## Validation

Run:

```sh
make sandbox-vm-live-poc-runtime-gate-readiness-internal-review-check
make sandbox-vm-live-poc-runtime-descriptor-contract-check
make sandbox-vm-live-poc-runtime-descriptor-only-plan-check
make no-new-powers-guardrail
make tool-surface-invariant-gate
```

The normal release gates must still pass. Tool count must remain `24`.
