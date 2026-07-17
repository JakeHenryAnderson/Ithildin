# Track B Node Identity-Key Rotation Implementation Plan

Status: implemented and observed in the bounded local-preview runtime.

Current governed tool count: `24`.

## NID-ROT-001 — Contract Gate

- Freeze authority, proof domain, lifecycle, crash recovery, rejection rules, and non-claims.
- Add the decision checker to `release-check` before runtime completion.

## NID-ROT-002 — Immutable Gateway Transition

- Add a one-Node expiring challenge store and closed request models.
- Add current-key-authenticated challenge and activation routes.
- Verify new-key proof of possession and atomically compare-and-set the active public key.
- Record challenge-issued and activated audit events with fail-closed evidence transitions.

## NID-ROT-003 — Atomic Node Identity State

- Extend mode-0600 Node state with a complete optional pending identity-key transition.
- Generate and persist pending K2 before sending activation.
- Allow signed activation-status recovery with pending K2.
- Promote K2 locally only after the Gateway confirms the exact transition and fingerprint.

## NID-ROT-004 — Operator Posture

- Return active-key fingerprint and bounded pending/latest rotation state in admin Node detail.
- Preserve Gateway identity truth, Node connectivity, runner state, and provider state as separate
  sources and claims.

## NID-ROT-005 — Adversarial And Observed Evidence

- Cover success, same-key, wrong target, bad proof, tampering, expiry, replay, revoked Node,
  concurrent change, audit failure, restart persistence, and crash-after-activation recovery.
- Verify mode 0600, private-key absence from API/audit/evidence, chain integrity, and 24 tools.
- Run focused tests, release check, review candidate, and exact-candidate evidence.

Stop if implementation requires private-key custody, retired-key fallback, administrator-forced key
replacement, production PKI, remote transport, fleet rollout, runner control, or a new governed tool.
