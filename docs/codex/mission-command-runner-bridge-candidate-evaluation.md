# MCC-007 Fixed Hermes Runner-Bridge Candidate Evaluation

Status: design-only candidate evaluation ready for exact-candidate review. No runner-bridge
capability is selected or authorized for implementation.

Current governed tool count: `24`.

## Decision Question

Can Ithildin later prove one fixed Hermes handoff without becoming a generic process, container,
host, or model-provider control plane?

The candidate answer is narrow enough to continue design review: a future bridge would be an
operator-installed, operator-started component beside one enrolled Node. It would accept only the
Gateway-derived, server-owned synthetic mission envelope already claimed by that Node and use one
closed Hermes profile whose executable or OCI identity, entrypoint, arguments, environment names,
working directory, mounts, network posture, and resource ceilings are fixed outside mission content.

This record evaluates that shape only. It does not approve the bridge, select a deployable artifact,
change Node transport, add an endpoint, or run Hermes.

## Candidate Trust Boundary

```text
Gateway mission truth
        |
        | signed Node claim and closed control decisions
        v
enrolled Node ---- bounded local handoff ---- operator-managed fixed Hermes bridge
        |                                           |
        | signed runner-reported observations       | configured provider
        v                                           v
Gateway evidence                              model-provider truth
```

The Gateway remains authoritative for mission admission, claim, cancellation decision, accepted
reports, governed Agent Runs, and audit evidence. The Node remains authoritative only for its signed
receipt and report statements. A later bridge may report that it attempted or observed a fixed
runner transition, but it cannot turn runner state, inference, output correctness, or provider state
into Gateway truth.

The bridge must not accept a command, executable, image, argument, environment value, path, URL,
mount, provider, model, credential, or free-form prompt from mission content. It must have no admin
token, Docker socket, Kubernetes access, host process namespace, shell, arbitrary filesystem root,
or generic process-control API. An operator-owned deployment profile, not Command Center or the
mission envelope, fixes those values.

## Required Later Capability Decision

A later capability decision must bind all of the following before any adapter implementation:

1. **Artifact and executable provenance.** Exact Hermes version, source or OCI digest, entrypoint,
   platform, SBOM/license evidence, verification method, upgrade owner, and rollback artifact.
2. **Local protocol and identity.** One closed Node-to-bridge protocol, peer authentication,
   exclusive state-directory ownership and modes, replay identifiers, message size limits, timeout,
   restart recovery, and fail-closed behavior for partial or conflicting handoffs.
3. **Prompt custody.** Whether the bridge receives template text or a sealed reference, where any
   plaintext exists, maximum lifetime, crash residue, log/redaction rules, and which component owns
   deletion evidence. Raw prompts, model output, chain of thought, and credentials cannot enter
   Gateway inventory, audit, telemetry, or evidence export.
4. **Static resource ceilings.** CPU, memory, process/PID, file-size, disk, wall-time, network, and
   concurrency limits fixed by the operator-managed profile rather than by mission content.
5. **Cancellation semantics.** Gateway `cancel_requested`, Node `cancel_observed`, bridge signal
   delivery, runner acknowledgment, runner exit, and `runner_reported_canceled` remain separate
   facts. No UI label may translate a request or signal into proof that a process stopped.
6. **Evidence ownership.** Exact safe bridge receipts, Node signature binding, runner/profile digest,
   timestamps, outcome/reason codes, optional artifact digests, restart/replay/partition evidence,
   retention, and quarantine rules. The model provider remains authoritative for inference facts.
7. **Non-bypass ceiling.** The bridge cannot claim that Hermes lacks built-in filesystem, terminal,
   network, plugin, or provider-side paths. Any non-bypass claim requires a separately reviewed host
   or sandbox boundary and adversarial evidence; it is not implied by governed MCP usage.
8. **Upgrade, rollback, and failure custody.** Operator-controlled upgrade and rollback, incompatible
   profile refusal, downgrade evidence, orphaned mission handling, and a stop line that never grants
   Ithildin generic host lifecycle authority.

The later decision must also define an exact candidate inventory, implementation tickets, negative
tests, release rollback, and independent Sol xhigh review. Sol Ultra remains opt-in by prior user
approval and is not authorized here.

## Rejected Alternatives

- Gateway or Command Center launching arbitrary executables, shells, containers, jobs, or commands;
- Docker-socket, Kubernetes, SSH, remote-desktop, browser-automation, or host-agent control;
- caller-authored objectives, prompts, arguments, environment, mounts, URLs, or filesystem paths;
- a generic runner SDK, plugin surface, remote MCP transport, or twenty-fifth governed tool;
- Node or bridge custody of model-provider credentials through mission content;
- automatic retry, reassignment, or process kill after an ambiguous claim, partition, or cancel;
- treating bridge health, process exit, or Node reports as model completion or output verification;
- production identity, runtime PostgreSQL, hosted telemetry, production release, promotion, or UAT
  claims.

## Current Disposition And Stop Line

`MCC-007` is a candidate-evaluation label, not an implementation ticket added to the authorized
`MCC-001` through `MCC-006` sequence. The current selected capability remains `not selected`.

No code, adapter, public API, Node transport, schema, persistence, policy, manifest, dependency,
deployment, service, or container change is authorized by this record. No Hermes artifact, process,
container, provider, prompt, credential, host state, or network endpoint may be inspected or used to
validate it. Tests and exact review can establish only that the design boundary is coherent enough
for a later separate capability decision.

<!-- mission-command-contract:start -->
{"document_type":"runner_bridge_candidate_evaluation","schema_version":"1","ticket_id":"MCC-007","disposition":"design_only_candidate_ready_for_exact_review","candidate":"fixed_hermes_runner_bridge","tool_count":24,"capability_selected":false,"implementation_authorized":false,"runtime_adapter_authorized":false,"runner_bridge_authorized":false,"runner_lifecycle_authority":false,"model_provider_authority":false,"prompt_custody_authorized":false,"arbitrary_host_control_authorized":false,"generic_process_control_authorized":false,"shell_execution_authorized":false,"docker_socket_authorized":false,"network_expansion_authorized":false,"node_transport_change_authorized":false,"public_api_change_authorized":false,"policy_change_authorized":false,"persistence_change_authorized":false,"new_governed_tool":false,"production_identity_authorized":false,"release_allowed":false,"production_promotion_allowed":false,"uat_complete":false,"sol_ultra_authorized":false,"fixed_provenance_required":true,"operator_managed_runner_required":true,"closed_profile_required":true,"static_resource_limits_required":true,"gateway_node_runner_truth_separation_required":true,"separate_capability_decision_required":true,"exact_candidate_review_required":true,"required_future_decisions":["artifact_and_executable_provenance","local_protocol_and_identity","prompt_custody","static_resource_ceilings","cancellation_semantics","evidence_ownership","non_bypass_ceiling","upgrade_rollback_and_failure_custody"]}
<!-- mission-command-contract:end -->
