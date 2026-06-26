# Sandbox/VM Live POC Decision Packet

Status: external decision-packet definition for blocked `ERG-004`.

Current governed tool count: `24`.

Current `ERG-004` status: `blocked`.

Current selected capability: `not selected`.

This packet packages the evidence and reviewer questions required before Ithildin may even consider
implementation planning for a live sandbox/VM worker proof of concept. It does not approve live
VM/container inspection, sandbox orchestration, local model invocation, Mission Control runtime
behavior, trusted-host promotion, SIEM adapter behavior, production identity, runtime Postgres,
compliance automation, public/security-product positioning, or any new governed tool power.

## Preconditions

Before a reviewer can recommend moving `ERG-004` beyond blocked status, the packet must show:

- favorable `ERG-003` external/source disposition for static preflight;
- no unresolved critical/high static-preflight findings;
- a post-RC decision-record path for `PRD-SANDBOX-LIVE-POC-001`;
- an operator-managed VM/container profile contract;
- a network/mount/root contract;
- cleanup transcript requirements;
- failure transcript requirements;
- Ithildin run/audit/evidence correlation requirements;
- Mission Control display-only boundary if Mission Control is involved;
- local model/client evidence fields that do not approve local model invocation;
- stop conditions for ambiguous sandbox, host, identity, audit, or product-positioning claims.

## Allowed Reviewer Outcomes

The reviewer may choose only these outcomes:

- `continue_design_only`: keep refining the evidence packet without approving implementation.
- `revise_before_decision`: identify missing evidence or unclear boundary text.
- `approve_limited_operator_managed_poc_planning`: allow a later implementation-planning packet,
  not runtime implementation.
- `block_live_poc`: keep the live POC lane blocked.

No outcome in this packet approves implementation, runtime inspection, VM/container lifecycle
control, Mission Control execution authority, local model invocation, trusted-host promotion, or
new governed tool powers.

## Decision Evidence Fields

Future evidence must remain secret-free and include stable labels:

- `decision_record_id`;
- `erg_id: ERG-004`;
- `prd_id: PRD-SANDBOX-LIVE-POC-001`;
- `prior_lane: ERG-003`;
- `operator_vm_profile_id`;
- `workspace_id`;
- `sandbox_id`;
- `network_posture`;
- `mount_root_posture`;
- `artifact_ingress_posture`;
- `artifact_egress_posture`;
- `mission_control_role`;
- `ithildin_role`;
- `local_model_role`;
- `cleanup_transcript_status`;
- `failure_transcript_status`;
- `external_review_status`;
- `implementation_approved: false`.

## What This Packet Does Not Prove

This packet does not prove `ERG-004` is closed, does not prove a sandbox is safe, does not prove
Mission Control can participate at runtime, and does not prove a local model may be invoked. A later
committed decision record, implementation plan, source-review result, and explicit go/no-go outcome
would be required before any implementation work.

## External Response Intake

Record any GPT 5.5 Pro / Very High or human expert response with
[sandbox-vm-live-poc-external-response-intake.md](sandbox-vm-live-poc-external-response-intake.md).
That intake template uses the `EXT-LIVE-POC-###` finding namespace and `sandbox-vm-live-poc`
normalizer area, but it does not close `ERG-004`, mutate findings, approve implementation planning,
approve runtime implementation, approve live VM/container inspection, approve local model
invocation, or approve Mission Control runtime behavior.
