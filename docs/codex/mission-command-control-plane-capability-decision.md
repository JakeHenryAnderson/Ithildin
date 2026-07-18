# Mission Command Control Plane Capability Decision

Status: approved for bounded architecture and ordered implementation under the active enterprise
goal. Runtime admission remains disabled until the ticket-specific implementation and review gates
pass.

Current governed tool count: `24`.

## Decision

Ithildin may add a Gateway-owned mission control-plane vertical slice that lets an authenticated
administrator select a server-owned synthetic mission template for one enrolled Node, lets that Node
claim the mission through the existing signed-request boundary, and records Node-reported lifecycle
evidence without claiming runner or model-provider authority.

This is the smallest next slice that makes Command Center an authoritative mission cockpit rather
than only a presentation layer over incidental Agent Runs. It is a new reviewed API and persistence
capability, not a new MCP tool or governed power class.

## Authorized Boundary

- Gateway derives mission identity, requesting principal, workspace, target Node, configuration
  binding, and lifecycle decision state.
- Command Center may create, inspect, and cancel a mission through authenticated administrative
  APIs. Cancellation is a Gateway decision and request; it is not proof that a runner stopped.
- An enrolled Node may claim only its own queued mission through an Ed25519-signed request.
- Mission delivery is a closed server-owned synthetic template envelope. It contains no
  caller-authored objective, command line, executable path, shell, environment variable, arbitrary
  URL, filesystem path, Docker instruction, or provider secret.
- Node lifecycle reports use closed outcome/reason codes and are explicitly runner-reported
  observations. Gateway receipt is authoritative; runner execution and model inference are not.
- A validly signed late report from a no-longer-eligible Node is retained as quarantined historical evidence and cannot advance Gateway lifecycle state.
- The first implementation uses synthetic data and the existing local-preview transport posture.
- Replay, restart, lease expiry, cancellation races, revocation, stale connectivity, configuration
  drift, evidence failure, and partition behavior fail closed and receive deterministic evidence.

## Explicit Non-Approvals

This decision does not approve:

- a twenty-fifth governed tool or any manifest-lock change;
- shell execution, arbitrary process launch, Docker socket access, Kubernetes control, browser
  automation, or arbitrary HTTP;
- Ithildin starting, stopping, killing, updating, or introspecting Hermes or another runner;
- model-provider credentials, model selection authority, inference custody, prompt or chain-of-
  thought surveillance;
- remote MCP, production identity, runtime Postgres, multi-tenant deployment, or hosted telemetry;
- treating a Node report as proof of runner health, filesystem non-bypass, model completion, or
  output correctness;
- automatic retry or reassignment after an ambiguous claim or completion transition;
- enterprise production-readiness, public security-product, or compliance claims.

## Authorization Basis

The project owner directed Codex to advance Ithildin autonomously into a self-hostable external-agent
governance platform, including an authoritative mission and fleet cockpit, while preserving the
Gateway/Node/runner/provider truth split, the 24-tool surface, evidence-backed claims, and the ban on
arbitrary host control. That instruction starts this bounded capability sprint. It does not waive
the ticket gates, exact-candidate review, or later UAT boundary.

Sol Ultra remains prohibited without prior user approval. Trust-boundary review may use Sol xhigh.

## Initial Disposition

```yaml
decision: approved_for_bounded_implementation
mission_admission_enabled_now: false
node_delivery_enabled_now: false
runner_launch_authority: false
model_provider_authority: false
new_governed_tool: false
tool_count: 24
synthetic_only: true
uat_required_now: false
```

<!-- mission-command-contract:start -->
{"document_type":"capability_decision","schema_version":"1","decision":"approved_for_bounded_implementation","tool_count":24,"mission_admission_authorized":true,"node_signed_delivery_authorized":true,"freeform_objective_authorized":false,"runner_bridge_authorized":false,"runner_lifecycle_authority":false,"model_provider_authority":false,"arbitrary_host_control_authorized":false,"production_identity_authorized":false,"uat_required_now":false}
<!-- mission-command-contract:end -->

Tests and generated evidence are evidence only. They do not authorize production deployment,
external finding closure, release, or UAT acceptance.
