# Track B Ithildin Node Signed Configuration Architecture

Status: approved architecture for the limited local-preview configuration distribution slice.

Current governed tool count: `24`.

## Purpose

This slice turns Node identity into the first real fleet-control primitive: the Gateway can state
what configuration one Node should store, the Node can authenticate and verify that statement, and
Command Center can show whether the Node has acknowledged the exact generation. It deliberately
stops before runner enforcement.

```text
local administrator -> Gateway -> immutable desired generation + audit evidence
Gateway             -> Node    -> target-bound signed configuration bundle
Node                -> disk    -> verified crash-safe mode-0600 stored bundle
Node                -> Gateway -> signed stored_not_enforced acknowledgment
Command Center      -> admin API -> desired / stored / drift / evidence posture
```

## Trust Roots And Domains

- Node request authentication uses the Node private key created during enrollment.
- Configuration authenticity uses a dedicated Gateway Ed25519 keypair and the domain
  `ITHILDIN-NODE-CONFIG-V1`; it does not reuse audit or manifest-lock signing keys.
- Enrollment returns the configuration public key and key ID once as part of the Node's local
  trust bootstrap. The private key remains Gateway-local and mode `0600`.
- Remote transport confidentiality is not claimed. The observed slice remains loopback or isolated
  local-container only; later remote deployment requires TLS or mTLS and production identity.

## Closed Configuration

Each immutable generation binds:

- schema version, configuration ID, generation, Node ID, principal ID, and workspace ID;
- issue, not-before, and expiry timestamps;
- policy version and SHA-256 policy digest;
- SHA-256 digest of the exact 24-tool manifest lock;
- minimum Node version and heartbeat interval;
- offline posture `deny_governed_actions`;
- a bounded future evidence-buffer limit.

The signed envelope contains the configuration digest and the closed configuration. Unknown fields,
unsafe labels, invalid bounds, and caller-supplied identity drift are rejected.

## State Semantics

- `unassigned`: the Gateway has no desired generation.
- `evidence_incomplete`: assignment or acknowledgment is not paired with durable audit evidence.
- `awaiting_node_storage`: a complete desired generation has not been acknowledged.
- `stored_current_not_enforced`: the Node signed an acknowledgment for the exact desired generation
  and digest; this proves verified local storage only.
- `configuration_drift`: the latest Node acknowledgment does not match the desired generation and
  digest.
- `revoked`: Node authentication is revoked regardless of configuration state.

Retrieval does not mean storage. Storage does not mean activation. Activation does not mean the
runner or its action path is governed; that future claim requires actual enforcement evidence.

## Failure And Concurrency Semantics

- Assignment increments generation inside `BEGIN IMMEDIATE` and never overwrites history.
- A pending assignment cannot be retrieved until its audit event is durably appended.
- Signed retrieval consumes `(node_id, nonce)` before a response is returned; replay remains denied
  after Gateway restart.
- The Node verifies the complete envelope before replacing its local stored bundle. Replacement is
  same-directory, mode `0600`, flushed, and atomic.
- Acknowledgment accepts only the current desired generation/digest and records
  `stored_not_enforced`; stale, future, or cross-Node acknowledgments fail closed.
- Revocation wins over retrieval and acknowledgment. Configuration cannot resurrect identity.

## Non-Claims

This architecture does not yet implement group policy, staged rollout, automatic rollback, Node
self-update, policy evaluation at the Node, governed request forwarding, credential brokering,
filesystem non-bypass, runner lifecycle control, production identity, or remote fleet management.
It is the signed desired-state and drift foundation those later milestones require.
