# Track B Node Configuration Trust Rotation Implementation Plan

Status: implemented and observed in the bounded local-preview runtime.

Current governed tool count: `24`.

## NCFG-TRUST-001 — Contract Gate

- Freeze the signing domain, exact envelope, trust states, overlap rules, recovery behavior, and
  non-claims.
- Add the decision checker to `release-check` before runtime completion.

## NCFG-TRUST-002 — Immutable Transition Store And API

- Add per-Node immutable transition assignment and acknowledgment rows.
- Add administrator history/assignment and signed Node retrieval/acknowledgment endpoints.
- Record distinct assigned, retrieved, and acknowledged audit events with no key material beyond
  public keys and fingerprints.

## NCFG-TRUST-003 — Atomic Node Trust State

- Extend mode-0600 Node state with optional pending and previous recovery trust.
- Verify K1-signed transitions and atomically stage K2 before acknowledging `staged_not_active`.
- Select configuration verification trust by signed key ID, but accept only active, unexpired
  pending, or unexpired previous recovery trust.
- Promote K2 only after a valid K2-signed higher configuration; never promote from transition
  retrieval or acknowledgment alone.

## NCFG-TRUST-004 — Fleet Posture UX

- Show current Gateway signer, staged next signer, acknowledgment status, expiry, and Nodes not yet
  staged.
- Keep assignment one Node at a time and require explicit confirmation.
- Preserve `stored_not_enforced`, runner-health-unknown, and policy-enforcement-unknown language.

## NCFG-TRUST-005 — Observed Rotation And Recovery Evidence

- Run K1 enrollment/configuration, K2 transition stage/ack, real Gateway restart on K2, K2
  configuration promotion, and K1 restart recovery during overlap.
- Reject unannounced K2, wrong target/current key, tampering, stale compare-and-set, expired pending
  trust, K1 after overlap, replay, revoked Node, and incomplete audit evidence.
- Verify restart persistence, mode-0600 files, private-key absence, audit chain, 24 tools, policy
  parity, responsive UI, full release check, and exact review candidate.

Stop if implementation requires automatic key-file changes, bulk rollout, private-key upload, a new
tool, runner action, production PKI, production identity, or remote transport.
