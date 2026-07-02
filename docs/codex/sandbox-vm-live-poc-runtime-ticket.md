# Sandbox/VM Live POC Runtime Ticket

Status: draft-only implementation ticket for a later `ERG-004` runtime gate.

Current governed tool count: `24`.

Current `ERG-004` status: `ready_for_runtime_ticket_draft`.

Validation:

```sh
make sandbox-vm-live-poc-runtime-ticket-check
```

This ticket translates the `ERG-004` decision record, implementation plan, runtime proposal, and
internal xhigh checkpoint into a bounded future implementation task. It does not approve runtime implementation.
It is a ticket draft only.

The ticket may be used later to prepare a runtime implementation gate for an operator-managed VM
descriptor/correlation slice. That future gate must still be explicit, reviewed, and fail closed
before any source code is allowed to accept descriptors or expose runtime status.

## Objective

Draft a later implementation task for a descriptor-only, operator-managed VM proof of concept.

The future slice may accept an operator-provided descriptor, validate secret-free labels and hashes,
correlate the descriptor with existing Agent Run, approval, audit, and signed-export evidence, and
produce safe status summaries.

Ithildin must not start, stop, pause, snapshot, shell into, inspect, or otherwise manage the VM.
The operator remains responsible for VM lifecycle, OS isolation, networking, mounts, account setup,
local model startup, and file transfer outside Ithildin.

## Authoritative Inputs

Use these committed artifacts as the source of truth:

- `docs/codex/sandbox-vm-live-poc-decision-record.md`
- `docs/codex/sandbox-vm-live-poc-implementation-plan.md`
- `docs/codex/sandbox-vm-live-poc-runtime-proposal.md`
- `docs/codex/sandbox-vm-live-poc-runtime-proposal-review-bundle.md`
- `docs/codex/sandbox-vm-live-poc-evidence-contract.md`
- `docs/codex/sandbox-vm-live-poc-preconditions-map.md`
- `docs/codex/sandbox-vm-live-poc-prerequisite-disposition-dry-run.md`
- `var/review-packets/v3/sandbox-vm-live-poc-runtime-proposal-review/`

The internal xhigh checkpoint disposition was `approve_draft_runtime_ticket`. That disposition
approves only this ticket draft. It does not replace external review and does not approve runtime
implementation.

## Future Implementation Slices

A later runtime implementation gate may consider only these slices:

1. **Descriptor schema**: define a closed local descriptor shape with no arbitrary payload fields.
2. **Descriptor validation**: validate labels, hashes, timestamps, correlation IDs, and posture
   enums without inspecting the VM.
3. **Run correlation**: bind `run_id`, `workspace_id`, `principal_id`, and existing Agent Run
   evidence without creating run controls.
4. **Evidence correlation**: bind `approval_correlation_id`, `tool_call_correlation_id`,
   `audit_head_hash`, and `signed_export_hash`.
5. **Cleanup/failure evidence**: record only digest/status fields for cleanup and failure
   transcripts.
6. **Safe status rendering**: expose safe labels, short hashes, status flags, and warning states.
7. **Negative fixtures**: reject descriptors that imply forbidden authority or leak raw sensitive
   content.
8. **Source-review handoff**: generate a focused review packet before any runtime use is claimed.

## Required Descriptor Fields

The future descriptor must remain secret-free and include or explicitly reject:

- `operator_intent_id`
- `principal_id`
- `workspace_id`
- `run_id`
- `sandbox_id`
- `sandbox_profile_id`
- `vm_profile_label`
- `vm_profile_hash`
- `mount_root_label`
- `workspace_mount_label`
- `network_posture_label`
- `model_client_label`
- `model_request_hash`
- `tool_call_correlation_id`
- `approval_correlation_id`
- `audit_head_hash`
- `signed_export_hash`
- `cleanup_plan_hash`
- `cleanup_transcript_hash`
- `failure_transcript_hash`
- `mission_control_display_packet_hash`
- `promotion_status: not_promoted`
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

## Required Negative Fixtures

The future gate must include negative fixtures for:

- missing or stale `vm_profile_hash`;
- mismatched `sandbox_profile_id`;
- unsafe `mount_root_label`;
- unexpected `network_posture_label`;
- missing `run_id` or mismatched run correlation;
- missing approval correlation where required;
- missing audit correlation where required;
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

## Required Evidence

A later implementation gate must produce:

- runtime implementation decision document;
- descriptor schema contract;
- negative fixture plan and transcripts;
- cleanup/failure transcript plan;
- Agent Run correlation plan;
- approval/audit/signed-export correlation plan;
- source-review bundle;
- no-new-powers evidence;
- exact focused command evidence;
- packet redaction scan;
- rollback/removal plan if the runtime gate fails.

## Explicit Non-Goals

This ticket does not approve:

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

Stop and request xhigh or GPT 5.5 Pro / human review before implementation if the future task
requires any forbidden authority, changes the product boundary, introduces a critical/high finding,
or makes Mission Control, a local model, or a VM/container part of Ithildin's trusted runtime
authority.

## Done When

This draft ticket is complete when:

- `make sandbox-vm-live-poc-runtime-ticket-check` passes;
- `make release-check` continues to pass;
- tool count remains `24`;
- no manifest, executor, policy, API/MCP, UI runtime, sandbox orchestration, local model invocation,
  or VM/container lifecycle behavior is added;
- future runtime work remains blocked until a separate implementation gate is explicitly approved.
