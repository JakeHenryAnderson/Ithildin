# Track B Node Identity-Key Rotation Architecture

Status: approved architecture for bounded local-preview implementation.

Current governed tool count: `24`.

## Trust Sequence

```text
Node K1 -> signed challenge request
Gateway -> immutable challenge(node, K1 fingerprint, nonce digest, expiry)
Node    -> generate K2; atomically persist K2 as pending
Node K1 -> signed activation request(public K2, proof by K2 over exact challenge binding)
Gateway -> verify K1 request + K2 proof; atomically promote public K2; audit; mark complete
Node K2 -> signed activation-status request
Node    -> atomically promote pending K2 locally after Gateway confirms K2 is active
```

The proof message binds protocol version, rotation ID, Node ID, principal ID, workspace ID, current
key fingerprint, next key fingerprint, challenge digest, and expiry. It cannot authorize another
Node, workspace, key pair, or later transition.

## Persistence And Evidence

- `node_identity_key_rotations` stores one immutable transition record with `pending`, `activated`,
  or `expired` lifecycle state and separate pending/complete audit-evidence state.
- A Node may have at most one unexpired pending challenge. Issuing another challenge does not
  overwrite an active one.
- Gateway activation uses `BEGIN IMMEDIATE`, compare-and-set checks for current public key and
  transition state, and a unique replay nonce already enforced by Node authentication.
- The Node writes pending K2 to its existing mode-0600 state before activation. It never sends K2's
  private material.
- While activation evidence is pending, ordinary Node requests fail closed. After the activation
  audit event succeeds, the Gateway marks both the Node and transition evidence complete.
- Administrative summaries expose fingerprints and state, never raw private material.

## Crash And Recovery Matrix

| Failure point | Gateway authority | Local recovery |
|---|---|---|
| Before pending K2 is stored | K1 | Request or discard the challenge |
| After K2 is stored, before activation | K1 | Retry activation with K1 and K2 proof |
| After Gateway activation, before local promotion | K2 | Query activation status signed by pending K2, then promote locally |
| After local promotion | K2 | Ordinary signed requests continue |
| K2 missing after Gateway activation | K2, unavailable locally | Revoke and re-enroll; never restore K1 |

## Rejection Rules

Reject wrong Node or workspace binding, wrong current or next fingerprint, same-key rotation,
malformed key material, invalid proof, expired or incomplete-evidence challenge, duplicate
activation, replayed request nonce, revoked Node, concurrent key change, and any status request not
authenticated by the exact activated key.

## Non-Claims

This is a local-preview request-authentication continuity primitive. It is not certificate rotation,
production workload identity, attestation, HSM/KMS custody, mTLS, remote deployment, runner
enforcement, unattended disaster recovery, or fleet rollout.
