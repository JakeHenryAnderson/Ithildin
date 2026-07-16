# Track B Node Manual Rollback Implementation Plan

Status: approved bounded runtime implementation plan.

Current governed tool count: `24`.

## NCFG-RB-001 — Contract Gate

- Freeze fresh-generation, compare-and-set, audit-lineage, single-Node, and non-enforcement rules.
- Add the decision checker to `release-check` before treating runtime work as complete.

## NCFG-RB-002 — Immutable History And Rollback Primitive

- Persist assignment kind and optional rollback source without rewriting existing generations.
- Add a read-only administrator history endpoint.
- Add a manual rollback endpoint requiring source and expected-current generations.

## NCFG-RB-003 — Audit And Negative Coverage

- Add a distinct rollback-assigned audit event with source/current/new lineage.
- Test wrong Node, missing/incomplete source, revoked Node, stale expected generation, audit failure,
  restart persistence, and continued monotonic Node verification.

## NCFG-RB-004 — Command Center Canary UX

- Load history only for the selected Node action surface.
- Require explicit confirmation of source and current generation.
- Refresh inventory after assignment and label the result as fresh signed desired state,
  `stored_not_enforced`, with enforcement unknown.

## Validation Order

1. decision gate;
2. store and API tests;
3. audit-failure, concurrency, restart, and Node-client negative tests;
4. UI tests and responsive browser verification;
5. observed one-Node rollback evidence;
6. 24-tool invariant, policy parity, full release check, and exact review candidate.

Stop if implementation requires bulk/group rollout, automatic health decisions, a new tool,
self-update, runner action, production identity, or remote transport.
