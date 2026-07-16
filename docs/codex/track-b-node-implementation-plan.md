# Track B Ithildin Node Vertical-Slice Implementation Plan

Status: approved limited runtime implementation plan.

Current governed tool count: `24`.

## NODE-001 — Decision And Contract Gate

- Record project-owner authority without mutating historical external-review state.
- Freeze allowed APIs, persistence, audit fields, cryptographic message, and non-claims.
- Add a release prerequisite that fails if the packet broadens into tool execution, remote MCP,
  runner lifecycle, or production claims.

Done when the decision check passes and the existing capability gate remains honestly blocked.

## NODE-002 — Enrollment Store And Admin Issuance

- Add SQLite stores for one-time enrollment codes, Nodes, and consumed nonces.
- Generate codes using `secrets`; persist only SHA-256 digests.
- Enforce expiry, single use, bounded labels, and atomic consumption with Node creation.
- Add admin-only issuance, list, detail, and revocation APIs.

## NODE-003 — Signed Node Authentication

- Verify Ed25519 signatures over the frozen canonical request message.
- Enforce timestamp skew, nonce shape, durable replay rejection, revocation, and stored public key.
- Derive Node and principal identity only from the authenticated stored record.

## NODE-004 — Closed Heartbeat

- Accept only the closed heartbeat schema.
- Persist safe posture fields and last accepted heartbeat transactionally with nonce consumption.
- Emit safe audit events with identifiers and hashes but no code, key, host metadata, or request
  body.
- Hold each mutation in an evidence-incomplete state until its append-only audit event succeeds;
  reject later transitions while evidence is incomplete.

## NODE-005 — Command Center Posture

- Add a fleet/Nodes surface backed only by admin read APIs.
- Present enrollment, revocation, never-observed, recently observed, stale, and evidence-incomplete
  states.
- Label connectivity as Gateway-observed and explicitly separate it from runner/model health.

## NODE-006 — Observed Synthetic POC

- Build a minimal Node CLI using current dependencies.
- Enroll, heartbeat, restart the Gateway, reject replay, revoke, and reject post-revocation traffic.
- Preserve the observed audit/database evidence locally and export a redacted deterministic report.

## Validation Order

1. decision and architecture checks;
2. store and cryptographic unit tests;
3. API negative tests and restart/replay tests;
4. UI tests and responsive browser verification;
5. manifest/tool-surface and policy-parity gates;
6. `make agent-workflow-check` and `make release-check`;
7. exact clean commit and `make review-candidate`.

Stop if a new governed tool, remote MCP, broad host access, runner lifecycle control, private-key
custody, production identity, or a dependency becomes necessary. Record that need as a later slice
instead of silently broadening this one.
