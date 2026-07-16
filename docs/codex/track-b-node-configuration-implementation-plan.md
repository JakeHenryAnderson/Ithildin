# Track B Ithildin Node Signed Configuration Implementation Plan

Status: approved limited local-preview runtime implementation plan.

Current governed tool count: `24`.

## NCFG-001 — Decision And Contract Gate

- Freeze the configuration fields, signing domain, target binding, state labels, and non-claims.
- Wire a release prerequisite that confirms 24 tools and rejects action-path or production claims.

## NCFG-002 — Dedicated Signing Trust Root

- Add explicit key generation/status commands and configured private/public paths.
- Require matching Ed25519 keys for assignment and expose only the public key/key ID at enrollment.
- Fail configuration enrollment/assignment safely when the trust root is unavailable.

## NCFG-003 — Immutable Desired Generations

- Add append-only per-Node configuration generations and desired/stored fields to SQLite.
- Bind the signed envelope to Node, principal, workspace, policy digest, manifest-lock digest, time
  window, and closed configuration.
- Hold assignment as evidence-incomplete until its audit event succeeds.

## NCFG-004 — Authenticated Retrieval And Local Storage

- Reuse signed Node timestamp/nonce authentication without changing caller identity.
- Verify key ID, signature, target, digest, manifest lock, time window, and monotonic generation in
  the Node client.
- Store the verified bundle with same-directory atomic replacement and mode `0600`.

## NCFG-005 — Signed Acknowledgment And Drift

- Accept only `stored_not_enforced` for the exact current generation and digest.
- Hold acknowledgment as evidence-incomplete until its audit event succeeds.
- Derive desired/stored/drift labels without claiming policy enforcement or runner health.

## NCFG-006 — Command Center And Observed POC

- Show desired generation, Node-stored generation, drift, signing key ID, and evidence state.
- Exercise assignment, retrieval, storage, acknowledgment, superseding generation, drift,
  replay denial, restart persistence, wrong-target/signature denial, and revocation.
- Preserve raw key/config fixtures only under ignored local evidence paths and export safe checks.

## Validation Order

1. decision and contract check;
2. signing, persistence, and client negative tests;
3. API replay, evidence failure, restart, and revocation tests;
4. UI tests and responsive browser verification;
5. observed synthetic POC and redacted checker;
6. 24-tool invariant, 24/24 policy parity, full release check, and exact review candidate.

Stop if implementation requires a new governed tool, dependency, runner execution, group rollout,
self-update, remote transport, production identity, or broader host powers. Record such work as a
later decision rather than silently expanding this slice.
