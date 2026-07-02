# Sandbox/VM Live POC Runtime Implementation Gate

Status: draft-only implementation gate for a future `ERG-004` runtime slice.

Current governed tool count: `24`.

Current `ERG-004` status: `ready_for_runtime_implementation_gate_draft`.

Validation:

```sh
make sandbox-vm-live-poc-runtime-implementation-gate-check
```

This gate translates the internally reviewed runtime-ticket packet into a future implementation
decision checklist. Runtime implementation remains blocked. It does not approve runtime
implementation. It defines what must be present before a later sprint may add any runtime descriptor
validation, status rendering, API behavior, MCP behavior, UI behavior, or persisted state.

## Preconditions

Before any implementation sprint starts, the following committed artifacts must remain valid:

- `docs/codex/enterprise-dual-response-disposition-record.md`
- `docs/codex/sandbox-vm-live-poc-decision-record.md`
- `docs/codex/sandbox-vm-live-poc-implementation-plan.md`
- `docs/codex/sandbox-vm-live-poc-runtime-proposal.md`
- `docs/codex/sandbox-vm-live-poc-runtime-ticket.md`
- `docs/codex/sandbox-vm-live-poc-runtime-ticket-internal-review.md`
- `docs/codex/sandbox-vm-live-poc-runtime-implementation-decision.md`
- `docs/codex/sandbox-vm-live-poc-runtime-descriptor-contract.md`
- `docs/codex/sandbox-vm-live-poc-runtime-negative-fixtures.md`
- `var/review-packets/v3/sandbox-vm-live-poc-runtime-ticket-review/`

The internal runtime-ticket disposition must remain:

```text
approve_internal_runtime_ticket_review
```

This disposition permits only preparation of this gate. It does not close `ERG-004`.

## Future Runtime Slice Allowed For Consideration

A later implementation sprint may consider only a descriptor/correlation slice:

- closed descriptor schema for an operator-managed VM run;
- descriptor validation with safe labels, hashes, timestamps, enums, and correlation IDs;
- correlation with existing Agent Run, approval, audit, and signed-export evidence;
- secret-free status summaries;
- negative fixtures and transcripts for forbidden authority;
- cleanup/failure digest evidence;
- source-review handoff before claiming live runtime readiness.

The later implementation must continue to treat the VM lifecycle, OS isolation, network posture,
mount posture, local model startup, and file transfer as operator-managed and operator-attested.

## Required Future Implementation Artifacts

A future runtime implementation sprint must add or update all of these before any runtime claim:

- runtime implementation decision document;
- descriptor schema contract;
- descriptor validation test fixture pack;
- cleanup and failure transcript hash contract;
- negative transcript generator;
- Agent Run correlation tests;
- approval/audit/signed-export correlation tests;
- safe status rendering tests;
- source-review bundle for the implemented runtime slice;
- no-new-powers evidence;
- rollback/removal plan;
- exact operator reproduction map.

## Required Future Runtime Tests

A future runtime implementation sprint must include tests for:

- missing or malformed descriptor fields;
- unknown descriptor fields;
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
  script value, raw path, or directory listing leakage.

## Explicit Non-Approvals

This gate does not approve:

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

Stop before implementation if the future runtime slice requires VM lifecycle authority, live
inspection, local model invocation, Mission Control runtime authority, trusted-host promotion, host
writes, network expansion, API/MCP profile loading, new governed powers, or stronger product claims.

Stop and ask for xhigh or GPT 5.5 Pro / human review if any critical/high finding appears, if the
product boundary becomes ambiguous, if the implementation needs a new power class, or if the same
trust-boundary gate fails three times.

## Done When

This gate draft is complete when:

- `make sandbox-vm-live-poc-runtime-implementation-gate-check` passes;
- `make sandbox-vm-live-poc-runtime-descriptor-contract-check` passes;
- `make sandbox-vm-live-poc-runtime-ticket-internal-review-check` passes;
- `make no-new-powers-guardrail` passes;
- `make tool-surface-invariant-gate` passes;
- `make release-check` passes;
- tool count remains `24`;
- no manifest, executor, policy, API/MCP behavior, UI runtime behavior, VM/container lifecycle
  behavior, local model invocation, Mission Control runtime authority, host write behavior, network
  expansion, or trusted-host promotion is added.
