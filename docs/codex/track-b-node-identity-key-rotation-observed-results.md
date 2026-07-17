# Track B Node Identity-Key Rotation: Observed Results

Status: observed local-preview POC evidence; not production readiness or UAT approval.

Observed on: `2026-07-16`.

Current governed tool count: `24`.

## Accepted Evidence

A fresh loopback Gateway on `127.0.0.1:8015` used a dedicated SQLite database, signed audit chain,
configuration-signing keypair, and one newly enrolled synthetic Hermes Node. The ignored evidence
root is `var/node-identity-key-rotation-poc-20260716/` and can be checked without printing private
or public key material:

```sh
make track-b-node-identity-key-rotation-evidence-check
```

The observed run established:

- K1 authenticated a one-Node, expiring challenge request;
- the Node generated K2 locally and persisted its complete pending transition in a mode-0600 state
  file before activation;
- K1 authorized activation while K2 proved possession over the exact target-bound transition;
- the Gateway atomically made K2 authoritative and immediately denied a K1-signed heartbeat;
- the client deliberately did not persist the successful activation response, modeling a lost
  response or exit after Gateway promotion;
- Gateway restart preserved the activated K2 record and replay state;
- the restarted Node authenticated activation status with its pending K2, promoted K2 locally, and
  then completed a K2-signed heartbeat;
- Gateway and Node public-key fingerprints matched after recovery;
- revocation denied a later K2-signed heartbeat;
- challenge and activation audit events remained in a valid chain;
- private and public key material remained absent from safe evidence and audit; and
- the manifest remained at 24 governed tools.

Focused automated coverage also rejected incomplete-evidence challenges, same-key transitions,
invalid K2 proof, expiry, replay, retired K1, and revoked identities. A simulated synchronous audit
failure compensated the uncompleted K2 swap back to K1 and labeled the attempt `audit_failed`; a
crash inside the narrower pre-evidence interval remains fail closed rather than restoring authority
without reconciliation.

## Claim Boundary

The accepted claim is limited to one local-preview Node's two-proof Ed25519 request-key transition,
Gateway restart persistence, and pending-key crash recovery. The Gateway never received either
private key, and the retired key retained no ordinary request authority after completed activation.

This does not prove production workload identity, certificate rotation, mTLS, HSM/KMS custody,
hardware attestation, remote transport, fleet rollout, scheduled rotation, unattended disaster
recovery, runner or model-provider health, policy enforcement, production readiness, release
approval, or UAT acceptance.
