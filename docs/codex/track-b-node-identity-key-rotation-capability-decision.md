# Track B Node Identity-Key Rotation Capability Decision

Status: **approved for bounded local-preview implementation** under the project owner's continuing
enterprise-governance goal.

Current governed tool count: `24`.

## Decision

Ithildin may rotate one enrolled Node's Ed25519 request-authentication key without transferring a
private key to the Gateway. Rotation requires both:

- a replay-protected request authenticated by the Node's currently active key; and
- proof of possession by the proposed next key over an exact, Gateway-issued, target-bound
  transition challenge.

This is current-key authorization plus next-key proof of possession. The Gateway atomically promotes
the proposed public key only after both proofs validate. The retired
key immediately loses all ordinary Node request authority. The Node persists the proposed private
key locally before activation and may finish local promotion after a crash by authenticating a
status request with that pending key.

## Allowed Runtime Change

- Persist immutable, expiring, one-Node rotation challenges and their evidence state.
- Derive public-key fingerprints from exact raw Ed25519 public keys.
- Add signed Node challenge, activation, and activation-status requests outside the governed MCP
  tool registry.
- Persist a pending private key only in the Node's mode-0600 local state, then atomically promote it.
- Record challenge issuance and successful activation in the audit chain without recording a
  private key, signature, nonce, or reusable secret.
- Expose active-key fingerprint and bounded rotation posture to an authenticated administrator.
- Exercise restart, replay, tamper, expiry, revocation, audit-failure, and crash-recovery cases with
  synthetic local-preview evidence.

## Recovery Decision

Before Gateway activation, the current key remains active and a failed or expired attempt may be
discarded locally. After activation, only the new key is authoritative. A Node that loses both its
active and persisted pending key must be revoked and re-enrolled as a new Gateway-derived identity.

The retired key is never a recovery key. Ithildin does not silently roll identity authority backward,
and an administrator cannot upload or select a replacement public key for an enrolled identity.

## Explicit Non-Approvals

This decision does not approve private-key upload or escrow, administrator-forced key replacement,
retired-key fallback, certificate or production-PKI enrollment, HSM/KMS integration, mTLS, remote
transport, fleet-wide rotation, automatic rotation scheduling, process or service control, runner authority
or runner lifecycle control, arbitrary host control, or a new governed tool.

Public keys and their fingerprints are identity metadata, not secrets. Evidence proves only the
bounded local-preview transition and does not establish hardware-backed custody, binary identity,
runner health, model-provider health, production readiness, release approval, or UAT acceptance.
