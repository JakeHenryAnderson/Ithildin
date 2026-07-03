# Sandbox/VM Live POC Runtime Descriptor-Only Implementation Ticket

Status: descriptor-only implementation-ticket packet for the future `ERG-004` runtime descriptor
slice.

Current governed tool count: `24`.

Current `ERG-004` status: `ready_for_descriptor_only_runtime_implementation_ticket`.

Current selected capability: `not selected`.

Run:

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket-check
```

This ticket turns the descriptor-only implementation plan into a concrete future sprint boundary. It
does not add runtime behavior, does not approve runtime implementation in this checkpoint, and does
not close `ERG-004`.

## Preconditions

The implementation ticket depends on these already-checked artifacts:

- `docs/codex/sandbox-vm-live-poc-runtime-ticket-internal-review.md`
- `docs/codex/sandbox-vm-live-poc-runtime-implementation-gate.md`
- `docs/codex/sandbox-vm-live-poc-runtime-descriptor-contract.md`
- `docs/codex/sandbox-vm-live-poc-runtime-descriptor-contract-internal-review.md`
- `docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-review-bundle.md`
- `docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-internal-review.md`
- `docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-plan.md`
- `docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-response-application-preflight.md`

The internal gate-readiness review disposition must remain:

```text
approve_internal_runtime_gate_readiness_review
```

The descriptor-only plan status must remain:

```text
ready_for_descriptor_only_runtime_implementation_planning
```

## Future Implementation Boundary

A later explicit implementation sprint may implement only this descriptor/correlation slice:

- validate an operator-supplied descriptor object;
- reject unknown descriptor fields;
- reject forbidden source flags or authority claims;
- persist a descriptor record only if the sprint explicitly chooses a local persistence surface;
- store only safe labels, hashes, timestamps, enums, booleans, correlation IDs, and status codes;
- expose read-only descriptor status summaries only if the sprint explicitly chooses an API or UI
  surface;
- correlate descriptor fields with existing Agent Run, approval, audit, and signed-export evidence;
- emit safe audit metadata for descriptor validation attempts if an audit event shape is explicitly
  chosen;
- generate negative transcript summaries for rejected descriptor cases;
- generate a source-review handoff packet for the implemented descriptor-only slice.

This ticket does not choose the final persistence, API, UI, Agent Run, or audit-event shape. Those
decisions belong to the later runtime implementation sprint and must be covered by tests in that
sprint.

## Required Descriptor Facts

Any future descriptor-only implementation must preserve these facts as data, not as claims Ithildin
verified by inspecting or controlling a VM/container:

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

## Required Future Test Classes

The future implementation sprint must include tests or negative fixtures for:

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

## Required Future Acceptance Evidence

The future implementation sprint must produce:

- an implementation decision that names the exact runtime surfaces touched;
- closed schema validation for the operator-supplied descriptor;
- positive descriptor fixtures with safe, secret-free output only;
- negative descriptor fixtures for every required future test class;
- policy/runtime parity notes if any governed path observes descriptor state;
- audit metadata evidence if any audit event is added;
- source-review handoff using a dedicated `EXT-LIVE-DESC-###` finding namespace;
- release/readiness wiring that keeps governed tool count at `24` unless a separate approved
  capability changes it;
- no-new-powers and tool-surface invariant evidence.

## Explicit Non-Approvals

This ticket does not approve:

- runtime implementation in this checkpoint;
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

Stop before runtime work if descriptor-only implementation requires VM lifecycle authority, live
inspection, local model invocation, Mission Control runtime authority, trusted-host promotion, host
writes, network expansion, API/MCP profile loading, new governed powers, stronger product claims,
or unbounded raw evidence storage.

Escalate to High review first for repeated gate failures or unclear implementation boundaries.
Escalate to XHigh or GPT 5.5 Pro / human review only if a critical/high finding appears or the
product boundary remains ambiguous after High review.

## Validation

Run:

```sh
make sandbox-vm-live-poc-runtime-gate-readiness-internal-review-check
make sandbox-vm-live-poc-runtime-descriptor-contract-check
make sandbox-vm-live-poc-runtime-descriptor-only-plan-check
make sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket-check
make no-new-powers-guardrail
make tool-surface-invariant-gate
```

The normal release gates must still pass. Tool count must remain `24`.
