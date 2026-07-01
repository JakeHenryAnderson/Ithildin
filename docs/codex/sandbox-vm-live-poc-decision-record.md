# Sandbox/VM Live POC Decision Record

Status: committed decision record for `ERG-004` implementation-planning-only continuation.

Decision ID: `PRD-SANDBOX-LIVE-POC-001`.

Current governed tool count: `24`.

Previous `ERG-004` status: `blocked`.

Recorded `ERG-004` status: `ready_for_implementation_planning_only`.

Current selected capability: `not selected`.

Run:

```sh
make sandbox-vm-live-poc-decision-record-check
```

This record applies the received GPT 5.5 Pro `ERG-004` live sandbox/VM POC decision-packet review.
It authorizes only an implementation-planning-only phase for an operator-managed, VM-first local POC.
It does not approve runtime implementation, live VM/container inspection, VM/container lifecycle
management, sandbox orchestration, Mission Control runtime behavior, local model invocation,
trusted-host promotion, network expansion, API/MCP profile loading, SIEM adapter behavior,
production identity, runtime Postgres, hosted telemetry, remote MCP, compliance automation,
shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem writes, plugin SDK
behavior, new governed tool powers, or public/security-product positioning.

## Reviewed Inputs

- Reviewer: GPT 5.5 Pro.
- Reviewer type: external AI packet/source reviewer.
- Reviewed commit: `b9ba2a03763496876830b18c9e9e5bc82ed80e96`.
- Reviewed packet path: `var/review-packets/v3/sandbox-vm-live-poc-external-review`.
- Reviewed packet hash: `sha256:b12459b7714912d8cfe40ff66a9e64370faa402e3d890add7da6631ca2ff817f`.
- Reviewed area: `sandbox-vm-live-poc`.
- Finding namespace: `EXT-LIVE-POC-###`.
- Normalized response path used for closure proof:
  `var/review-runs/sandbox-vm-live-poc/normalized-response.json`.

The normalized response file is ignored local evidence. It was used to prove the closure gate accepts
the reviewer response, then removed so normal release gates return to deterministic no-pending-response
state.

## Closure Proof

The transient normalized response recorded:

- `source_access: packet-and-source`;
- `can_close_source_rows: true`;
- `mutates_findings: false`;
- `closes_external_review: false`;
- `erg_003_favorable_disposition: true`;
- `decision_outcome: approve_limited_operator_managed_poc_planning`;
- `finding_count: 0`.

`make sandbox-vm-live-poc-decision-closure-check` reported:

- `closure_ready: true`;
- `erg_003_favorable_disposition: true`;
- `decision_outcome: approve_limited_operator_managed_poc_planning`;
- `erg_004_status: ready_for_decision_record`;
- `allowed_closure_state: ready_for_decision_record`;
- `implementation_planning_allowed: false`;
- `runtime_changes_allowed: false`;
- `live_vm_inspection_allowed: false`;
- `mission_control_runtime_allowed: false`;
- `local_model_invocation_allowed: false`;
- `sandbox_orchestration_allowed: false`;
- `trusted_host_promotion_allowed: false`;
- `new_power_classes_allowed: false`.

## Decision Outcome

The approved committed outcome is:

```text
approved_for_implementation_planning_only
```

The approved lane movement is:

```text
ERG-004: blocked -> ready_for_implementation_planning_only
```

That movement means only that an implementation-planning packet may now be drafted for a limited,
operator-managed live POC. It does not approve runtime implementation.

## Planning Scope

Allowed planning scope:

- implementation-planning document;
- static fixtures;
- operator-managed VM profile sketches;
- cleanup transcript plan;
- failure transcript plan;
- evidence field list;
- source-review handoff prompt;
- Mission Control display-only notes;
- local-model/client label design;
- stop-condition language.

VM-first framing:

- The strategic POC target is an operator-managed VM profile.
- Container profiles are deferred and may be considered later only as lower-assurance developer
  convenience evidence.
- Ithildin does not manage, start, stop, inspect, or orchestrate VMs or containers in this phase.
- Mission Control remains display/import planning only.
- Local model invocation remains blocked until a separate review and decision record.

## Still Blocked

The following remain blocked after this decision record:

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

## Required Next Step

The next allowed step is a planning-only implementation packet:

```text
docs/codex/sandbox-vm-live-poc-implementation-plan.md
```

That packet must stop at design, fixture, evidence, negative transcript, and source-review planning.
It must require a later external/source review before any runtime implementation.

## Validation

Run:

```sh
make sandbox-vm-live-poc-decision-record-check
make sandbox-vm-live-poc-implementation-plan-check
make sandbox-vm-live-poc-response-dry-run
make sandbox-vm-live-poc-decision-closure-check
```

Release gates must continue to pass with no live normalized response present.
