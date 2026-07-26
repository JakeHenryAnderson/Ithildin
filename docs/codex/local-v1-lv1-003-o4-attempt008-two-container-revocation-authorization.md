# Attempt 008 Exact Two-Container Revocation Authorization

Status: **authorized, unconsumed, exact resumable one-shot preparation candidate**

Recovery `LV1-003-O4-ATTEMPT-008-TWO-CONTAINER-REVOCATION-001` is a new operation. It does not
resume, amend, retag, or mutate the closed four-container recovery. Its exact eight-path candidate
must be a clean immediate child of `cbf304512965fbd10df6b72b78777750ac4cc6d5`, tree
`654193cf9456433bcafc6da7c5dc6d2d076af54e`, and live execution additionally requires fixed review
tag `ithildin/lv1-003-o4-attempt008-two-container-revocation-reviewed` to bind that child commit and
tree.

The operation validates the closed predecessor receipt leaves, then queries only Compose project
`ithildin-local-v1-o4-d801f37b`. It requires exactly the public-disposition-bound API and UI
container identities, both with reviewed images and both exited. It has no Docker mutation or stop
command. Node and Hermes may be described only as
`not_observed_in_exact_project_query_at_preinspection`, while their historical status remains
`not_targeted_by_prior_recovery`. No generic absence or host-wide exclusivity is claimed.

The reviewed Attempt 008 topology gives only the API a bind mount to the retained Gateway database
and audit mirror. The operation repeatedly rechecks the exact two-container projection immediately
before and after Node revocation, audit append, evidence completion, and the durable
final-disposition intent. The terminal disposition receipt is written only after the post-intent
check. The trusted single operator must not perform concurrent lifecycle or alternate storage
access.

Storage authority remains limited to descriptor-bound aliases for the exact retained SQLite
database and canonical JSONL mirror. The operation may transition only the privately reconciled
Node from `enrolled/complete` to `revoked/pending`, append one deterministic existing-semantics
`node.revoked` event, and mark `revoked/complete` only after a clean SQLite/JSONL audit lifecycle.
It never initializes, migrates, repairs, adopts, truncates, or deletes evidence.

A nonblocking owner-only lock permits one active invocation. A legal durable prefix may continue
only as the same operation; retry authority remains false. Docker configuration is created beneath
the new owner-only receipt root and does not depend on ambient `TMPDIR`.

This authorization denies container stop/start/restart/exec/delete, Compose, generic Docker or
process discovery, ports, credentials, providers, cleanup, old-receipt mutation, `uv`-lock deletion,
audit repair, migration, arbitrary SQL, successor O4 execution, release, and UAT. The governed tool
count remains 24.

Fixture-only validation:

```sh
make local-v1-lv1-003-o4-attempt008-two-container-revocation-check
```

The standalone live target must not run until the exact candidate is committed, pushed,
independently reviewed `GO`, and bound by its fixed review tag:

```sh
make local-v1-lv1-003-o4-attempt008-two-container-revocation-run
```
