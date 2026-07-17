# Track B Node Governed Access Implementation Plan

Status: approved bounded implementation plan.

Current governed tool count: `24`.

## NGA-001 — Contract And Gate

- Record the capability decision, signed body, authority prerequisites, partition semantics, and
  explicit non-claims.
- Add a release prerequisite that rejects write/network/offline/runner-control expansion and any
  tool-count change.

## NGA-002 — Authenticated Gateway Ingress

- Add one strict Node tool-call payload and one signed POST route.
- Reuse `NodeStore.authenticate_request` so path/body tamper, clock skew, revocation, and durable
  replay rejection remain identical to other Node transitions.
- Resolve principal and workspace only after authentication from the stored Node record.

## NGA-003 — Configuration And Role Binding

- Require a recently observed Node, current desired configuration, exact storage acknowledgment,
  matching heartbeat digest, minimum version, active workspace, and `deny_governed_actions` posture.
- Resolve a dedicated enabled static Node profile with exactly `AgentReadOnly`; do not treat
  enrollment as self-assigned role authority.
- Force the enrolled workspace into arguments and allow only existing MCP-exposed read manifests.

## NGA-004 — Existing Governance Pipeline

- Construct the existing `GovernedToolCallService` with the Node-derived principal record and
  existing executors/stores.
- Preserve manifest validation, scope resolution, policy decision evidence, redaction, audit-chain
  writes, and agent-run correlation.
- Return existing bounded result states without adding an executor or governed tool.

## NGA-005 — Node Client And Failure Semantics

- Reverify the stored signed configuration before every call.
- Add a synchronous method that signs once and never performs local execution, buffering, queuing,
  or automatic retry.
- Treat Gateway partition as a closed failure and response loss as indeterminate.

## NGA-006 — Adversarial And Observed Evidence

- Cover success, identity derivation, workspace injection, cross-workspace denial, non-read denial,
  profile failure, configuration drift/expiry/mismatch, below-minimum version, revocation, signature
  tamper, durable replay, restart, and partition.
- Run a real loopback proof with one synthetic Node and export only identifiers, hashes, state
  labels, audit correlation, and explicit non-claims.

## Validation

Run focused API/Node tests and the capability gate, then lint, typecheck, policy parity,
`make agent-workflow-check`, `make release-check`, an exact clean commit, and
`make review-candidate`.

Stop if implementation needs a new tool, dependency, Node listener, remote MCP, write/network
authority, local fallback, runner lifecycle control, arbitrary host access, or a claim stronger than
the observed evidence.
