# Sandbox/VM Live POC Implementation Plan

Status: implementation-planning-only packet for `ERG-004`.

Current governed tool count: `24`.

Current `ERG-004` status: `ready_for_implementation_planning_only`.

Current selected capability: `not selected`.

Decision record:
`docs/codex/sandbox-vm-live-poc-decision-record.md`.

Run:

```sh
make sandbox-vm-live-poc-implementation-plan-check
```

This packet defines the planning boundary for a future operator-managed live sandbox/VM proof of
concept. It does not approve runtime implementation, live VM/container inspection, VM/container
lifecycle management, sandbox orchestration, Mission Control runtime behavior, local model
invocation, trusted-host promotion, network expansion, API/MCP profile loading, SIEM adapter
behavior, production identity, runtime Postgres, hosted telemetry, remote MCP, compliance
automation, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem
writes, plugin SDK behavior, new governed tool powers, or public/security-product positioning.

## POC Shape

The future POC should be VM-first and operator-managed.

- The operator provisions and starts the VM outside Ithildin.
- The operator controls VM lifecycle outside Ithildin.
- The operator records a static VM profile and posture evidence for review.
- Ithildin records and validates evidence about the intended workspace/profile, but does not manage
  the VM.
- Mission Control may display/import future evidence only after separate planning and review.
- A local model/client may be represented by a label and request hash only; invocation remains
  blocked until separately reviewed.

Container profiles remain deferred. They may be useful later as lower-assurance developer fixtures,
but they are not part of this `ERG-004` implementation-planning packet.

## Future Inputs To Design

No API, MCP, manifest, executor, or runtime input is approved by this packet. A later implementation
proposal may draft static fixture shapes for:

- `workspace_id`;
- `run_id`;
- `principal_id`;
- `sandbox_profile_id`;
- `sandbox_id`;
- `operator_intent_id`;
- `vm_profile_label`;
- `vm_profile_hash`;
- `mount_root_label`;
- `network_posture_label`;
- `cleanup_plan_hash`;
- `failure_transcript_hash`;
- `mission_control_display_packet_hash`;
- `model_client_label`;
- `model_request_hash`.

Any future input shape must avoid prompts, model responses, file contents, diffs, raw host paths,
secrets, dependency names, package script values, raw sandbox internals, and broad filesystem
enumeration.

## Future Evidence Categories

The planning phase may define static fixtures and expected evidence fields for:

- operator intent evidence;
- Ithildin Agent Run evidence;
- Ithildin audit and approval evidence;
- sandbox/VM profile evidence;
- sandbox transcript digest evidence;
- cleanup transcript digest evidence;
- failure transcript digest evidence;
- local model/client label evidence;
- Mission Control display-only packet evidence;
- source-review handoff evidence;
- negative transcript evidence;
- `promotion_status: not_promoted`.

Cross-source correlation must use safe identifiers and hashes only. No prompt text, model response,
file contents, diffs, raw host path, raw VM transcript, or sandbox filesystem listing may appear in
review artifacts unless a later review explicitly approves that data class.

## Required Negative Plans

The implementation-planning phase must define negative fixtures or transcripts for:

- missing or stale VM profile hash;
- unsafe mount/root posture;
- unexpected network posture;
- attempted VM/container lifecycle management by Ithildin;
- attempted live VM/container inspection;
- attempted local model invocation;
- attempted Mission Control execution or approval authority;
- attempted trusted-host promotion;
- attempted host write;
- broad write or arbitrary network expansion;
- cleanup failure;
- failure transcript missing or mismatched;
- packet hash mismatch;
- raw secret, prompt, model response, file content, diff, or raw path leakage.

## Future Source Review Requirement

Before any runtime implementation, a future source-review packet must include:

- this implementation plan;
- the `ERG-004` decision record;
- the evidence contract;
- static fixture contracts;
- negative transcript plans;
- proposed operator-managed VM profile contract;
- proposed cleanup/failure transcript contract;
- proposed Mission Control display-only notes;
- proposed local model/client label contract;
- no-new-powers evidence;
- exact stop conditions;
- focused command evidence.

The future reviewer must decide whether a bounded runtime implementation may be planned. This packet
does not make that decision.

## Stop Conditions

Stop and request external/source review before proceeding if planning requires:

- runtime implementation;
- live VM/container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- Mission Control runtime behavior;
- local model invocation;
- trusted-host promotion;
- network expansion;
- API/MCP profile loading;
- SIEM adapter behavior;
- production identity;
- runtime Postgres;
- hosted telemetry;
- remote MCP;
- compliance automation;
- shell/Docker/Kubernetes/browser governed powers;
- arbitrary HTTP;
- broad filesystem writes;
- plugin SDK behavior;
- new governed tool powers;
- public/security-product positioning.

## Validation

Run:

```sh
make sandbox-vm-live-poc-decision-record-check
make sandbox-vm-live-poc-implementation-plan-check
make sandbox-vm-live-poc-response-dry-run
make sandbox-vm-live-poc-decision-closure-check
```

The normal release gates must still pass with no normalized `ERG-004` response file present under
`var/review-runs/`.
