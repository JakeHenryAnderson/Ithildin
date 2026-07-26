# Attempt 008 Exact-Project Quarantine And Revocation Authorization

Status: **authorized, unconsumed, exact resumable one-shot preparation candidate**
Recovery: `LV1-003-O4-ATTEMPT-008-QUARANTINE-REVOCATION-001`

## Exact Candidate

This authorization applies only to an exact six-path allowlist in one clean immediate child of
parent `66c85f8af3e2db11fd8556a9cbbf33ed826e991b`, whose tree is
`d2ef30bac1c2ac8ddb58db400b31ff98c6b785e4`. The validator derives and checks the child commit and
tree after the candidate is committed. The attempt budget is one and retry authority is false.
A valid consumed journal prefix may continue only as same-operation resume; it is not another
attempt.

Live execution additionally requires the fixed Git tag
`ithildin/lv1-003-o4-attempt008-quarantine-revocation-reviewed` to resolve to that same child commit
and tree. The tag is an external exact-content binding created only after independent review; moving
it is not authorized. Parent-plus-path validation alone is preparation evidence, not exact reviewed
content authorization.

The six paths are `Makefile`, `README.md`, this JSON/Markdown pair, the recovery script, and its
focused test module. No API, Node, audit-core, schema, migration, policy, manifest, deployment, or
UI source is in scope.

## Authorized Operation

The one live operation may:

- validate only the exact owner-only reconciliation receipts whose sizes and SHA-256 digests are
  bound in the JSON authorization;
- keep the raw Node ID private and emit only its domain-separated digest;
- inspect only containers with Compose project
  `ithildin-local-v1-o4-d801f37b`;
- stop only the exact four retained services `ithildin-api`, `ithildin-ui`, `ithildin-node`, and
  `hermes`, after binding their container and reviewed image identities;
- require all four containers stopped immediately before and after each Node, audit, and evidence
  mutation phase, then inspect them again before final disposition;
- bind private hard-link aliases to only the exact retained SQLite database and canonical audit
  JSONL mirror;
- use the existing `NodeStore` transition `enrolled/complete` to `revoked/pending`;
- append exactly one existing-semantics `node.revoked` event through `AuditWriter`; and
- mark the privately selected Node `revoked/complete` only after a clean, exact SQLite/JSONL audit
  lifecycle is observed.

The operation never calls `NodeStore.initialize()` or `AuditWriter.initialize()`. A durable
revocation plan precedes mutation. One nonblocking owner-only operation lock is held before journal
or live access, so only a single active invocation may use a legal prefix. A later invocation may
reconcile the same exact stop or revocation operation after the prior process exits, without
duplicating a stop, Node transition, or audit event.

If SQLite and JSONL evidence are missing, divergent, partial, or ambiguous, the operation stops
fail closed. This authorization does not authorize audit-lifecycle repair, JSONL truncation,
evidence adoption, or deletion. A Node left `revoked/pending` remains recovery-required until a
separately reviewed audit-lifecycle decision exists.

## Authority Boundary

This operation does not authorize container start, restart, exec, deletion, Compose, project down,
volume/network/image deletion, generic Docker queries, processes, ports, credentials, tokens,
providers, network access, database migration, schema repair, arbitrary SQL, or multiple-Node
mutation.

It does not authorize cleanup. It does not authorize Attempt 010 or any successor O4 execution.
The fixed database and audit aliases remain private recovery evidence until separately reconciled.
The governed tool count remains 24; release remains false; UAT remains false.

## Commands

Fixture-only validation:

```sh
make local-v1-lv1-003-o4-attempt008-quarantine-revocation-check
```

The separately reviewed live entrypoint is:

```sh
make local-v1-lv1-003-o4-attempt008-quarantine-revocation-run
```

The live target is standalone and must not be invoked until the exact candidate is committed,
pushed, independently reviewed `GO`, and bound by the fixed review tag. It uses frozen offline
dependency resolution. Static validation reads no runtime, receipt, Docker, credential, process,
port, socket, network, provider, database, or audit content.
