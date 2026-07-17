# Track B Node Version Posture Implementation Plan

Status: approved bounded implementation plan.

Current governed tool count: `24`.

## NVER-001 — Contract And Gate

- Record the closed version grammar, truth sources, state machine, claims, and non-approvals.
- Add a release prerequisite that rejects self-update, package, process-control, fleet-rollout, or
  runner-lifecycle expansion.

## NVER-002 — Transactional Observation

- Add `last_node_version` to the local-preview Node store using the existing additive SQLite
  compatibility pattern.
- Persist it only inside a successfully authenticated heartbeat transaction.
- Keep failed signatures, replay, skew, revocation, and incomplete evidence from mutating it.
- Apply the same closed grammar to new enrollment, heartbeat, and desired minimum-version input.

## NVER-003 — Authoritative Posture

- Read the current signed desired configuration for each Node.
- Derive the closed state machine in the API, returning both source values and explicit narrow
  evidence labels.
- Cover missing assignment, never observed, below/equal/above minimum, invalid legacy data,
  evidence pending, revocation, restart, and downgrade observation.

## NVER-004 — Command Center

- Add version posture to fleet attention counts and each Node card.
- Keep reported version, desired minimum, posture, and operator-managed maintenance wording
  distinct from runner health, package authenticity, and enforcement.
- Verify desktop and narrow layouts, keyboard disclosure, and zero console errors.

## NVER-005 — Observed Synthetic Maintenance

- On a fresh loopback Gateway, enroll one synthetic Node and assign a signed desired minimum.
- Observe a below-minimum signed heartbeat, an operator-managed higher-version heartbeat, Gateway
  restart persistence, and an operator-managed lower-version heartbeat.
- Reject invalid grammar, replay, tampering, and post-revocation traffic without version mutation.
- Export only safe version/posture, record identifiers, hashes, and explicit non-claims.

## Validation

Run focused store/API/UI tests first, then lint, typecheck, UI build/tests, decision/evidence checks,
`make agent-workflow-check`, `make release-check`, an exact clean commit, and
`make review-candidate`.

Stop if implementation requires Node self-update, package transfer, service-manager or process
control, automatic rollback, fleet rollout, runner lifecycle control, remote transport, a new
governed tool, or a new dependency.

