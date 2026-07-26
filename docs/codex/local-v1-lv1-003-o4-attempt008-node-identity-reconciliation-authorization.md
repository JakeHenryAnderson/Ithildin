# Attempt 008 Node Identity Reconciliation Authorization

Status: **authorized, unconsumed, exact one-shot preparation candidate**
Reconciliation: `LV1-003-O4-ATTEMPT-008-NODE-IDENTITY-RECONCILIATION-001`

## Exact Candidate

This authorization applies only to an exact six-path allowlist in one clean immediate child of
parent `457da3b4d245d38862f07c64a117aa69fc5874c7`, whose tree is
`4656f76ad6769d96916bc5b6d8cbc74ca3b91d5a`. The validator derives and checks the child commit and
tree after the candidate is committed. The attempt budget is one, the tracked state is unconsumed,
and retry authority is false.

The six paths are `Makefile`, `README.md`, this JSON/Markdown pair, the reconciliation script, and
its focused test module. No API, Node, schema, migration, policy, manifest, deployment, or UI source
is in scope.

## Authorized Read

The one live operation may open only
`var/local-v1-lv1-003-o4-runtime/20260726T001909Z-d801f37b/var/db/ithildin.sqlite3`.
It must:

- write an exclusive owner-only consumption receipt before opening the database;
- traverse only fixed descriptor-relative path components with no symlink following and no
  directory enumeration;
- reject SQLite journal, WAL, and shared-memory sidecars;
- take a bounded, stable held-descriptor snapshot without changing the source;
- deserialize that snapshot into memory with query-only and untrusted-schema posture;
- use only fixed structural `integrity_check`, `table_list`, and `table_info` queries, which inspect
  no application row content, to require real tables with the exact ordered column contract;
- allow only closed safe-column reads through the SQLite authorizer; and
- write the raw Node identity only to a private `0600` result receipt.

The projection may classify one relationally bound identity as
`identity_bound_active_quarantine_required` or `identity_bound_revoked`. Zero rows, multiple rows,
schema drift, unexpected activity, pending evidence, corruption, descriptor drift, or any mismatch
must become `identity_unresolved_reconciliation_required`. It must never infer Node absence.

The operation does not read `code_hash`, `public_key`, `descriptor_json`, enrollment output,
`compose.env`, audit logs, Node private state, signing material, unrelated tables, or adjacent
runtime files. It does not use Docker, processes, ports, sockets, a network, an API, a provider, or
ambient credentials. Static validation reads no retained runtime or receipt content.

## Authority Boundary

This projection alone does not authorize quarantine. It does not authorize revocation. It does not authorize cleanup.
It does not authorize Attempt 010 or any successor O4 execution. A successful
active-identity projection requires a separate exact-project quarantine and audited-revocation
candidate before another mission attempt can be considered.

The governed tool count remains 24; release remains false; UAT remains false. Evidence from this
lane does not authorize promotion, acceptance, or deletion of retained runtime or evidence.

## Commands

Fixture-only validation:

```sh
make local-v1-lv1-003-o4-attempt008-node-identity-reconciliation-check
```

The separately reviewed one-shot operator entrypoint is:

```sh
make local-v1-lv1-003-o4-attempt008-node-identity-reconciliation-run
```

The run command must not be invoked until the exact candidate is committed, independently reviewed
GO, and pushed. The live entrypoint must refuse before receipt creation or database access if the
exact candidate gate is not valid.
