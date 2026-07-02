# Sandbox/VM Live POC Runtime Proposal

Status: runtime-proposal-only packet for `ERG-004`.

Current `ERG-004` status: `ready_for_runtime_proposal_review`.

Current governed tool count: `24`.

Validation:

```sh
make sandbox-vm-live-poc-runtime-proposal-check
make sandbox-vm-live-poc-runtime-proposal-review-bundle
```

This proposal defines the smallest future runtime implementation slice that may be reviewed after
the ERG-004 implementation-planning packet. It does not approve runtime implementation, live
VM/container inspection, VM/container lifecycle management, sandbox orchestration, Mission Control
runtime behavior, local model invocation, trusted-host promotion, network expansion, API/MCP profile
loading, SIEM adapter behavior, production identity, runtime Postgres, hosted telemetry, remote MCP,
compliance automation, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad
filesystem writes, plugin SDK behavior, new governed tool powers, or public/security-product
positioning.

## Proposed Minimal Slice

The only future runtime slice this proposal may advance is an operator-managed VM proof of concept
that records and validates safe evidence about a sandboxed worker run. Ithildin would not start,
stop, pause, snapshot, inspect, shell into, or otherwise manage the VM. The operator remains
responsible for VM lifecycle, OS isolation, account setup, networking, mounts, local model startup,
and any external file transfer outside Ithildin.

The proposed future slice is limited to:

- accepting an operator-provided sandbox run descriptor through a separately reviewed local surface;
- validating descriptor shape, hashes, labels, and correlation IDs;
- correlating the descriptor with an existing Agent Run, audit chain, approval evidence, and signed
  export evidence;
- producing secret-free status and evidence summaries;
- generating cleanup and failure transcript evidence from operator-provided digest fields;
- denying descriptors that imply live VM inspection, lifecycle control, local model invocation,
  Mission Control execution authority, trusted-host promotion, network expansion, or host writes.

## Required Runtime Proposal Evidence

Any later implementation proposal must include all of these fields or explain why the field is
deferred:

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

Cross-source correlation must use safe identifiers and hashes only. The proposal must not require
prompt text, model response text, raw transcript text, file contents, diffs, raw host paths, raw VM
paths, raw sandbox filesystem listings, dependency names, package script values, secrets, or broad
resource enumeration.

## Proposed Descriptor Contract

A later implementation may propose a descriptor contract only if it remains descriptor-only. The
descriptor must be explicit about what Ithildin is not observing directly:

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

The descriptor may support coarse status labels such as `prepared`, `running_observed_by_operator`,
`completed_reported_by_operator`, `failed_reported_by_operator`, `cleanup_reported_by_operator`,
`recovery_required`, or `ambiguous`. It must not let Ithildin claim VM truth beyond the supplied
evidence.

## Negative Cases Required

Before any runtime implementation, the proposal must define negative transcripts or fixtures for:

- missing or stale `vm_profile_hash`;
- mismatched `sandbox_profile_id`;
- unsafe `mount_root_label`;
- unexpected `network_posture_label`;
- missing `run_id` or mismatched run correlation;
- missing approval or audit correlation where required;
- attempted VM/container lifecycle management by Ithildin;
- attempted live VM/container inspection by Ithildin;
- attempted local model invocation by Ithildin;
- attempted Mission Control execution, approval, policy, or audit authority;
- attempted trusted-host promotion;
- attempted host write or artifact promotion;
- arbitrary network expansion;
- shell/Docker/Kubernetes/browser execution;
- cleanup failure;
- missing or mismatched `failure_transcript_hash`;
- packet hash mismatch;
- raw secret, prompt, model response, file content, diff, transcript, dependency name, package
  script value, raw path, or directory listing leakage.

## Source Review Requirement

The future source-review packet must include:

- this runtime proposal;
- the implementation-planning packet;
- the `ERG-004` decision record;
- the evidence contract;
- descriptor schema sketch;
- negative transcript plan;
- cleanup/failure transcript plan;
- resource limit plan;
- audit and Agent Run correlation plan;
- Mission Control display-only boundary notes;
- no-new-powers evidence;
- exact stop conditions;
- focused command evidence.

The reviewer must decide whether a bounded runtime implementation ticket may be drafted for a later
runtime gate. This proposal does not make that decision.

## Stop Conditions

Stop and request xhigh or GPT 5.5 Pro / human review before proceeding if proposal work requires:

- live VM/container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- local model invocation by Ithildin;
- Mission Control runtime behavior;
- trusted-host promotion;
- direct host writes;
- network expansion;
- API/MCP profile loading;
- SIEM adapter runtime behavior;
- production identity or runtime Postgres;
- compliance automation or public/security-product positioning;
- new governed tool powers.
