# Track B Node Governed Access Architecture

Status: approved architecture for the bounded local-preview read-only slice.

Current governed tool count: `24`.

## Request Path

```text
external runner adapter
  -> Ithildin Node client
  -> signed POST /nodes/{node_id}/governed-tool-calls
  -> Gateway Node authentication and durable replay rejection
  -> Gateway-derived agent:node.<node_id> + enrolled workspace
  -> dedicated AgentReadOnly Node profile
  -> existing GovernedToolCallService
  -> existing manifest, scope, policy, audit, redaction, and read executor
```

The request body contains only protocol version, the exact stored configuration generation and
digest, a bounded runner session label, an existing tool name, and arguments. Principal, roles,
Node identity, and workspace authority are not accepted from the body. The path/header Node must
match the authenticated database record.

## Authority Preconditions

Before governance evaluation, the Gateway requires all of the following:

- the Node is enrolled, evidence-complete, and recently observed by an accepted heartbeat;
- the Node's reported version meets the signed desired minimum;
- the desired configuration is complete, current, and unexpired;
- the request generation and digest equal the desired generation and digest;
- the Node's acknowledgment equals that same generation and digest with
  `stored_not_enforced` status;
- the latest accepted heartbeat reports that exact configuration digest;
- the desired offline posture is `deny_governed_actions`;
- the enrolled workspace is active;
- the dedicated static Node role profile is present, enabled, and exactly `AgentReadOnly`.

These are Gateway prerequisites, not proof that a runner enforced the configuration. The signed
request proves possession of the Node identity key; the Gateway record remains authoritative for
principal and workspace identity.

## Workspace And Tool Binding

If arguments omit `workspace_id`, the Gateway injects the enrolled workspace before manifest and
policy evaluation. If they supply another workspace, the request is denied and audited. The first
slice permits only an existing manifest whose MCP exposure is true and whose risk is `read`.
Unknown or other-risk tools are denied through the same governance audit path. No executor is added.

The effective session identifier is namespaced by the authenticated Node ID and exact configuration
generation/digest, so the existing governed-call input hash and agent-run correlation bind the
authority snapshot without changing the core policy or approval pipeline. Runner-supplied labels
provide correlation only and cannot merge authority across Nodes or configuration generations.

## Restart, Replay, And Partition Semantics

Node authentication consumes its nonce transactionally before governance proceeds. A replay remains
denied after Gateway restart. If the Gateway is unavailable, the Node client performs no tool work,
stores no request, and returns a closed `Gateway is unavailable` failure. It does not queue or retry.
If the Gateway accepted a request but its response was lost, the outcome is indeterminate; repeating
the same nonce is rejected and the client must not invent success.

The local-preview Node remains an outbound client with no listener. Transport is limited to the
existing approved local hosts and does not claim confidentiality.

## Non-Claims

This architecture does not provide write authority, approval execution, runner control, prompt or
model-output monitoring, filesystem non-bypass, remote MCP, offline operation, production identity,
TLS/mTLS, sandbox orchestration, endpoint management, or broad fleet enforcement. It is the first
evidence-backed action-path mediation slice under a server-derived Node identity.
