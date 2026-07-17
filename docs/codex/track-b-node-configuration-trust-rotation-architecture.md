# Track B Node Configuration Trust Rotation Architecture

Status: approved architecture for bounded restart-based signer rotation.

Current governed tool count: `24`.

## Trust Sequence

```text
Gateway signer K1 -> signed per-Node transition(K1, K2, overlap expiry)
Node              -> verify with pinned K1 -> atomic stage K2 -> staged_not_active ack
operator          -> point Gateway at K2 keypair -> explicit process restart
Gateway signer K2 -> fresh higher configuration generation signed by K2
Node              -> verify exact staged K2 -> promote K2; retain K1 recovery-only until expiry
```

Possession of K2 is insufficient before the K1-signed transition is staged. A K1 transition is
insufficient to claim activation. Activation evidence is the Node's later signed configuration
acknowledgment after verifying and storing a K2-signed generation.

## Persistence

- SQLite stores immutable transition assignments with `pending` then `complete` audit-evidence
  state and an exact staged acknowledgment.
- Node state stores active, pending, and optional previous recovery trust in one mode-0600,
  same-directory atomic file.
- The configuration bundle remains separate from Node identity/trust state. Replacing one cannot
  partially replace the other.
- Restart preserves Gateway assignments, Node staged trust, acknowledgment, replay nonces, and
  configuration generation history.

## Failure And Recovery

- Assignment uses `BEGIN IMMEDIATE` and an expected-current-key compare-and-set.
- Only the current active Gateway signer may create a transition. A transition cannot chain from a
  pending or previous recovery key.
- A Node with an expired pending transition rejects K2 and keeps K1 active.
- After K2 promotion, a K1-signed configuration may be verified only during the signed overlap and
  does not change active trust back to K1. Operator rollback of the Gateway signer therefore remains
  possible during overlap without silent Node demotion.
- After overlap expiry, recovery requires an operator-reviewed new transition or re-enrollment; no
  fail-open key discovery exists.

## Non-Claims

This slice is not production PKI, certificate rotation, HSM/KMS custody, automated fleet rollout,
runner enforcement, production identity, remote transport security, or unattended disaster
recovery. It is the local-preview trust continuity primitive those later deployments require.
