# Track B Node Configuration Trust Rotation Capability Decision

Status: **approved for bounded local-preview, one-Node-at-a-time configuration-signing trust
transition and restart-based signer rotation**. Automatic key-file mutation and fleet-wide cutover
remain unapproved.

Decision date: 2026-07-16

Decision authority: the project owner authorized autonomous enterprise evolution, including safe
configuration distribution, upgrade/rollback, and hardening. This separate decision narrows that
authority into a recoverable signing-trust transition. It does not rewrite or close historical
`external_pending` rows.

Current governed tool count: `24`.

## Approved Slice

1. The current Gateway configuration signer may authorize one next Ed25519 public key for one Node
   in a target-bound, time-bounded envelope using `ITHILDIN-NODE-CONFIG-TRUST-V1`.
2. Assignment requires an administrator to name the expected current signing key and the next
   public key. Ithildin derives and verifies the next key ID; private key material is never accepted.
3. An enrolled Node retrieves the transition with its existing signed-request and durable replay
   contract, verifies it only with its currently pinned configuration trust, stores it atomically as
   `staged_not_active`, and signs an exact transition acknowledgment.
4. Signer activation occurs only through an explicit Gateway configuration change and process
   restart. Ithildin does not rename, overwrite, delete, or generate active key files through an API.
5. After restart, the Node promotes the staged key only when a complete configuration envelope
   verifies under that exact pending trust. The formerly active trust remains recovery-only until
   the signed overlap expiry; it cannot authorize a new next key.
6. Command Center may show Gateway signer, Node-staged next signer, acknowledgment evidence,
   transition expiry, and partial-fleet posture without claiming runner enforcement.

## Required Safety Semantics

- The transition binds Node, principal, workspace, current key ID, next key ID/public key, issue
  time, not-before time, expiry, transition ID, and digest.
- Current and next key IDs must differ. Unknown fields, malformed keys, wrong targets, wrong current
  trust, expired transitions, signature failures, replay, and stale expected-current assignments
  fail closed.
- Assignment and acknowledgment are unavailable while their audit evidence is incomplete.
- A new signer cannot be accepted merely because it appears in a configuration response. The Node
  must already hold the exact old-key-authorized pending trust.
- Previous-key recovery is time bounded and does not silently demote the active key.
- Nodes that did not stage the next trust before Gateway cutover require explicit recovery: restart
  the Gateway with the old signer during overlap, or revoke and re-enroll after operator review.

## Explicitly Not Approved

- automatic rotation, scheduled cutover, bulk/group targeting, quorum-based promotion, or health-
  triggered rollback;
- API access to configuration-signing private keys or arbitrary filesystem mutation;
- accepting an unannounced signer, trusting a key only because the Gateway presents it, or disabling
  monotonic configuration generation checks;
- Node self-update, runner lifecycle control, governed action forwarding, production identity,
  remote MCP, hosted fleet management, or claims that key rotation proves runner enforcement;
- a new governed tool or dependency.

Tests and observed evidence prove only the bounded software behavior. They do not approve production
PKI, HSM/KMS integration, unattended rotation, production deployment, or compliance claims.
