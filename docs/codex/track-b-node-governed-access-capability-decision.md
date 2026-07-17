# Track B Node Governed Access Capability Decision

Status: **approved for one bounded local-preview, Node-authenticated, read-only governed-access
slice**.

Decision date: 2026-07-17

Decision authority: the project owner explicitly authorized autonomous implementation of the
smallest defensible Ithildin Node vertical slice with authenticated enrollment, server-derived
agent identity, constrained governed access, restart/replay/partition evidence, and no arbitrary
host control. This decision is that separately documented capability sprint. It does not rewrite
historical external-review findings or retroactively change the scope of earlier Track B decisions.

Current governed tool count: `24`.

This slice uses server-derived agent identity and permits no arbitrary host control.

## Approved Slice

An enrolled Node may submit one synchronously signed governed-tool request to the local-preview
Gateway. The Gateway must:

1. authenticate the exact request through the existing Ed25519 Node signature, timestamp, and
   durable nonce contract;
2. derive Node, principal, role profile, and workspace authority from trusted Gateway state rather
   than request content;
3. require an active, evidence-complete, recently observed Node whose exact desired configuration
   is unexpired, acknowledged as `stored_not_enforced`, and reported in its latest heartbeat;
4. bind every request to the Node's enrolled workspace and reject caller-supplied workspace drift;
5. expose only existing MCP-exposed `read` tools to a dedicated `AgentReadOnly` Node profile;
6. reuse the existing manifest validation, resource scoping, policy evaluation, redaction,
   append-only audit, and agent-run correlation pipeline;
7. return a bounded result synchronously without local fallback, buffering, queuing, or automatic
   retry.

The Node client may verify its stored signed configuration again before sending, force its enrolled
workspace into the signed arguments, and report Gateway unavailability as a closed failure. The
slice may add one Node-authenticated FastAPI route and corresponding client method. It must not add
a governed tool, dependency, or alternate executor.

## Explicitly Not Approved

- write, write-proposal, network, destructive, shell, process, Docker, Kubernetes, browser,
  credential, service-manager, or arbitrary host control;
- runner invocation, runner lifecycle control, prompt interception, model inference, chain-of-thought
  collection, or a local MCP listener owned by the Node;
- request buffering, offline execution, background replay, automatic retry, or at-least-once
  execution claims;
- trusting caller-supplied principal, role, Node, workspace, policy, configuration, or approval
  authority;
- remote MCP, non-local transport, TLS/mTLS, production identity, fleet-wide policy enforcement,
  filesystem non-bypass, or Tanium-equivalent claims;
- changing the existing 24-tool manifest surface.

## Required Evidence

- body, path, timestamp, signature, and nonce tampering fail closed;
- a consumed nonce remains rejected after Gateway restart;
- unknown, revoked, stale, evidence-incomplete, below-minimum, unconfigured, expired, drifting, or
  unacknowledged Nodes cannot reach tool execution;
- a missing or disabled Node role profile denies access;
- cross-workspace arguments are rejected and omitted workspace arguments are bound to the enrolled
  workspace before policy evaluation;
- non-read, non-MCP-exposed, and unknown tools do not execute;
- a valid read reaches the existing governed pipeline under the exact Gateway-derived Node
  principal and produces correlated audit/run evidence;
- a Gateway partition produces no local execution, queue, or buffered request; response loss remains
  indeterminate and is never retried automatically;
- policy parity remains 24/24 and the governed tool count remains 24.

Tests and generated evidence prove only this local-preview mediated read path. They do not authorize
production deployment, write authority, runner enforcement, release, UAT acceptance, or public
security-product claims.
