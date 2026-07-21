# Production Identity And Storage PIS-003 SD-PG-001 Connection Evidence Implementation Record

Status: bounded test-only `PIS-003-SD-PG-001` connection-evidence implementation candidate
complete; exact-candidate source review pending and all execution authority false.

Implementation ID:
`PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-CONNECTION-EVIDENCE-IMPLEMENTATION`.

Parent review:
`PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-CONNECTION-EVIDENCE-GATE-REVIEW`.

Implementation baseline commit: `c84c9f9f97ee9716e1466944e26e206e85b4b729`.

Current governed tool count: `24`.

The closed machine-readable implementation authority is
`docs/codex/production-identity-storage-pis-003-sd-pg-001-connection-evidence-implementation-authority.json`.
Its exact schema, path inventory, protected hashes, implementation facts, Boolean authority, and
next action are authoritative. Prose cannot broaden the closed contract.

Validate this candidate with:

```sh
make production-identity-storage-pis-003-sd-pg-001-connection-evidence-implementation-check
```

## Implemented Boundary

The candidate replaces the test-local always-refusing placeholder with the dedicated
`scripts/production_identity_storage_pis_003_sd_pg_001_connection_evidence.py` harness. The module
is test-only and is not imported by API, Node, Mission Command, Gateway, MCP, startup, or current
SQLite behavior.

The implemented layers are:

- a strict canonical JSON execution-preflight reader with duplicate-member, non-finite value,
  extra-field, Boolean/integer, exact-path, digest, freshness, and closed-schema rejection;
- external read-only Ed25519 trust-record and receipt verification with exact canonical payloads,
  type-specific assertions, fifteen-minute validity, run/target/source/candidate binding, and a
  named discard-owner relationship;
- a canonical single-host `postgresql+psycopg` URI parser and ephemeral HMAC-SHA-256 target binding
  that reject every ambient environment key matching `^PG[A-Z0-9_]+$`;
- an immutable read-only synthetic SQLite snapshot reader that validates the file digest before and
  after use and passes canonical rows to the protected reviewed importer;
- a pure-Python Psycopg, system-`libpq`, TLS dependency, SBOM/license, certificate-root, architecture,
  real-path, version, and digest preflight/probe contract;
- a synchronous SQLAlchemy `NullPool` engine path owning its connection, explicit non-autocommit
  outer transaction, rollback, disposal, and separately budgeted post-rollback absence check;
- an Alembic online mode that accepts only a caller-owned SQLAlchemy `Connection` already inside a
  non-nested transaction and never accepts a URL or constructs an engine;
- closed safe failure categories that suppress raw driver/server/Alembic exception evidence;
- a separate final target-discard receipt verifier; and
- complete-output secret-marker and connection-string scanning.

The first exact-candidate review of `7c6b5de5ab8055bfbe1d0384c6b1df0d372f4e03`
returned `NO-GO` with `0` Critical, `0` High, `6` Medium, and `2` Low findings. This successor
closes those eight findings by binding negative scenarios to exactly one attempt; revalidating and
rolling back the exact original transaction; consuming the DSN and binding key from the mutable
environment before the driver boundary; resolving the loaded TLS symbol owner to its exact real
path; binding the full-tree secret scan to a canonical marker commitment while rejecting symlinks
and non-regular artifacts; closing the public exception boundary; rejecting Unicode control
characters in DSN identity fields; and preserving contextual manifest, trust, receipt, and discard
failure stages. These are implementation repairs, not a completed successor review.

The reviewed importer, schema, migration revision, runtime stores, configuration, routes, policy,
manifests, lockfiles, and 24-tool surface remain protected and unchanged.

The predecessor offline implementation validator and review now verify their implementation
artifacts at the fixed reviewed commit instead of comparing them with a successor worktree. The
connection-evidence gate likewise verifies its protected inputs at its fixed candidate commit.
These changes preserve historical review truth once the connection-evidence phase changes
Alembic's test-only online boundary; they grant no new implementation or execution authority.

## Execution Is Deliberately Inactive

`EXECUTION_AUTHORITY_ACTIVE` is `false`. The CLI exposes only `--check`. The first line of the run
boundary refuses at `authority_gate` before manifest validation, environment access, Psycopg import,
DSN or binding-key read, engine construction, socket activity, or migration execution.

The implementation contains the later runner so its ownership and cleanup semantics can be
reviewed now, but it cannot be reached until a later exact implementation review and a separate
environment-specific execution gate change that authority deliberately. Its native identity probe
must match the actually loaded pure-Python Psycopg `libpq` and linked TLS library to the signed
preflight before the first SQL statement.

The implementation does not accept a DSN on the command line or from a file, repository setting,
packet, receipt, or log. It does not create or drop a database, role, grant, service, or container.
It cannot commit, downgrade, repair, retry ambiguous work, reverse-import, dual-write, activate a
backend, or manage PostgreSQL lifecycle.

## Offline Validation Evidence

The focused storage/schema/import suite contains `74` passing tests. The added coverage proves:

- authority refusal precedes manifest and environment access;
- strict preflight accepts one fully synthetic, externally located, read-only receipt set;
- candidate, source, attempt-budget, artifact-hash, ambient-allowlist, and extra-key drift fail
  closed;
- the immutable SQLite reader preserves the exact file and semantic record digests;
- canonical DSN/HMAC validation accepts the closed form and rejects target-binding mismatch,
  uppercase hosts, IP literals, leading-zero ports, and noncanonical escapes;
- current and future-looking ambient `PG*` variables are rejected with an empty allowlist;
- output scans reject secret markers and connection-string forms;
- negative scenarios consume exactly one connection attempt and cannot cross into the positive
  two-attempt workflow;
- the exact original outer transaction remains active through migration and import, is explicitly
  rolled back, and cannot be replaced without a closed failure;
- environment-held DSN and binding-key values are consumed before driver import and raw driver,
  engine, rollback, and disposal exceptions cannot escape the public boundary;
- loaded TLS identity is bound to the exact symbol-owning library path rather than a basename;
- the finalizer binds the complete output-tree scan to a canonical secret-marker commitment and
  rejects symlinks, non-regular files, nested markers, and connection strings;
- canonical NFC non-ASCII DSN identity values remain accepted while Unicode control characters are
  rejected;
- malformed manifest, trust, receipt, and discard inputs retain their contextual closed failure
  categories and stages;
- an otherwise trusted final-discard issuer cannot substitute for the named discard owner; and
- Alembic offline rendering remains deterministic while online mode contains no engine, driver, or
  URL construction.

No real DSN or target-binding key was read. Psycopg was not imported. No engine was constructed,
database connection attempted, online migration executed, PostgreSQL/container service started, or
runtime behavior changed.

## Authority And Next Action

This candidate records:

- `connection_evidence_candidate_complete: true`;
- `environment_receipt_implementation_complete: true`;
- `test_harness_implementation_complete: true`;
- `synthetic_snapshot_reader_implementation_complete: true`;
- `online_alembic_caller_connection_implementation_complete: true`;
- `native_dependency_probe_implementation_complete: true`;
- `target_discard_finalizer_implementation_complete: true`;
- `exact_candidate_source_review_complete: false`;
- `psycopg_plain_sync_use_allowed: false`;
- `external_dsn_consumption_allowed: false`;
- `test_harness_execution_allowed: false`;
- `database_connections_allowed: false`;
- `migration_execution_allowed: false`;
- `postgres_service_allowed: false`;
- `container_lifecycle_allowed: false`;
- `runtime_postgres_allowed: false`;
- `production_identity_allowed: false`;
- `release_allowed: false`;
- `production_promotion_allowed: false`;
- `uat_complete: false`; and
- `uat_required_now: false`.

The next required action is
`review_pis_003_sd_pg_001_connection_evidence_candidate_exact_commit`. The review must inspect the
exact committed implementation, authority refusal, receipt and DSN parsing, native identity probe,
transaction ownership, rollback/discard sequencing, secret-safe evidence, protected hashes, and
negative coverage. A zero-finding review may permit only preparation of a separately committed
environment-specific execution gate; it cannot itself authorize driver load, DSN consumption,
connections, migration execution, PostgreSQL or container lifecycle, runtime PostgreSQL,
production identity, release, promotion, or UAT.
