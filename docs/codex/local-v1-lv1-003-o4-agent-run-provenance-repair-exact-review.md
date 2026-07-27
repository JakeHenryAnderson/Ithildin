# Local v1 LV1-003 O4 AgentRun Provenance Repair Exact Review

Status: `GO`

Date: 2026-07-26

## Exact Candidate

- Commit: `73fb131f1f89e4b12374dac26a3f8efe231f5c31`
- Tree: `d64f5fb43e118c072b099ab2877a34cd287de695`
- Parent commit: `468ae2deaba2c55e05997662aeb20f58f3fa91cd`
- `scripts/local_v1_lv1_003_o4_producer.py`:
  `sha256:4b940650e66e34bd56f56ff933c3364452d1fa7854919f5316fd091e455745af`
- `tests/test_local_v1_lv1_003_o4_producer.py`:
  `sha256:597ba6c3325a521a9dacc65b5c5019090dd998ac9f2b217b4cec6d6d545c72b4`

The candidate changes exactly those two paths. The worktree and exact diff were
clean at review.

## Review Result

- Critical: 0
- High: 0
- Medium: 0
- Low: 0

The exact-candidate disposition is `GO`.

## Reviewed Trust Contract

The producer now validates the persisted AgentRun record as the authoritative
source for the exact run, session, principal, workspace, server-derived Node
identity and display name, authorization profile, configuration generation and
digest, closed offline and runner-enforcement posture, mission identity, claim
identity, envelope digest, and Gateway-validated mission-binding source.

Completed timeline events are validated against the real AgentRunContext
quartet: run, session, workspace, and principal. They no longer require
duplicated mission, claim, or envelope fields that the live event records do not
store. Mission, claim, and envelope values enter the resulting run and
operation bindings only after the authoritative AgentRun record matches.
Existing journey checks continue to enforce exact run and event correlation,
uniqueness, request bindings, tool ordering, and result bindings.

The fake API matches the live `/runs/{run_id}` record and event-context shape.
Negative coverage rejects six missing or conflicting AgentRun provenance cases
and mismatches for each of the four event-context fields.

## Validation

- 331 producer and constrained-journey tests passed centrally.
- The independent reviewer reran 12 focused positive and negative cases.
- Ruff passed for both changed paths.
- Strict mypy passed for the producer centrally.
- Agent-workflow, 24-tool invariant, no-new-powers, and diff checks passed
  centrally.
- The independent review did not inspect private evidence or run a producer,
  Docker, provider, tag, commit, push, or broad release suite.

Only known non-failing temporary-directory cleanup warnings were observed.

## Evidence Limits And Authority

This review proves only that the exact two-path repair matches the live
AgentRun persistence contract and fails closed on provenance or event-context
drift. It does not prove a future live mission will succeed, reproduce an
Attempt 019 Gateway projection, or establish release, promotion, production,
or UAT readiness.

This `GO` permits preparation of a separate exact Attempt 020 one-shot
authorization gate only. It does not create a review tag, grant live execution
authority, reopen or retry Attempts 001 through 019, permit concurrent or
automatic invocation, add a governed tool or power, or authorize arbitrary
host, shell, filesystem, Docker, network, provider, release, promotion,
production, credential-custody, or UAT activity.
