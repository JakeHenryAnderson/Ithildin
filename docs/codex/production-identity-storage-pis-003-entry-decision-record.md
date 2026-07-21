# Production Identity And Storage PIS-003 Entry Decision Record

Status: committed `PIS-003` entry-decision candidate pending exact-candidate source review and a
separate implementation gate.

Decision ID: `PRD-PROD-IAM-STORAGE-PIS-003-ENTRY`.

Parent decision: `PRD-PROD-IAM-STORAGE-PIS-002-CONTINUATION`.

Entry baseline commit: `159bf93b4b1e3975d7cab615ef51d2e951f9a80a`.

Decision outcome: `select_bounded_isolated_postgresql_schema_import_slice_pending_review_and_gate`.

Proposed implementation slice: `PIS-003-SD-PG-001`.

Current governed tool count: `24`.

Current `ERG-006` status: `planning_only`.

Current `ERG-007` status: `planning_only`.

This record selects the dependency and transaction design for one future, non-serving isolated
schema-and-import proof. It does not authorize dependency or lockfile changes, implementation,
migration execution, a database service, Psycopg use, runtime PostgreSQL, runtime schema changes, production
identity, enterprise RBAC, release, promotion, or UAT. Exact-candidate source review must clear this
record, then a separate committed `PIS-003-SD-PG-001` implementation gate must bind the allowed paths,
dependency lock delta, evidence, and rollback before code changes begin.

The closed companion contract is
`docs/codex/production-identity-storage-pis-003-entry-decision.json`. Its exact dependency snapshot,
transaction semantics, proposed slice, protected hashes, authority values, and next action are
authoritative. Prose cannot broaden the closed contract.

## Why PIS-003 Starts With An Offline Schema Contract

`PIS-002-SD-001` proved one Ithildin-owned repository seam without changing SQLite behavior. The
PIS-002 continuation inventory then showed that the remaining stores depend on SQLite-specific
connections, `BEGIN IMMEDIATE`, `rowid`, JSON extraction, caller-owned transactions, or
cross-store recovery. Repeating dependency-free protocols would freeze those mechanics as an
accidental portability contract.

The smallest useful next step is therefore not a second repository and not a running PostgreSQL
adapter. It is a reviewable schema/transaction contract for the already characterized
`sandbox_descriptors` aggregate, rendered for an isolated PostgreSQL target with production startup
disabled. This creates a concrete dialect surface without granting serving authority or exposing
credentials, network access, migration execution, or a second backend to the application.

## Dependency Decision Snapshot

Dependency metadata was rechecked on `2026-07-20` against the official PyPI project records and a
Python 3.12 universal resolver preview. Selection is for a later gated implementation only.

### SQLAlchemy 2.0 Core — selected for the proposed slice

- Proposed tooling-group requirement: `SQLAlchemy==2.0.51`.
- Role: Core schema metadata, dialect-aware SQL construction, and offline PostgreSQL DDL rendering.
- Boundary: Core only. ORM mapping, sessions, identity maps, lazy loading, autoflush, async engines,
  runtime pools, and application startup imports are excluded.
- Current official snapshot: `2.0.51`, MIT, Python `>=3.7`. The `2.1` line is prerelease and outside
  the selected pin.
- SQL logging must remain disabled for values and credentials; literal-binds output is forbidden for
  sensitive data.

### Alembic — selected for offline migration artifacts only

- Proposed tooling-group requirement: `alembic==1.18.5`.
- Role: one linear revision lineage and deterministic offline PostgreSQL SQL rendering for the
  isolated candidate schema.
- Boundary: no application import, no startup upgrade, no live connection, no autogenerate-as-
  authority, no branch/merge heads, and no downgrade claim across an irreversible boundary.
- Current official snapshot: `1.18.5`, MIT, Python `>=3.10`.
- Autogenerate may be used only to produce an untrusted draft for review; checked-in revision code
  and rendered SQL are the reviewed artifacts.

### Psycopg 3 — selected as plain synchronous package for isolated verification

- Proposed tooling-group requirement: `psycopg==3.3.4`.
- Current official snapshot: `3.3.4`, LGPL-3.0-only, Python `>=3.10`.
- The pure-Python package requires externally supplied `libpq`; the `c` and `binary` extras change
  native-build, bundled-library, redistribution, patching, and SBOM ownership.
- The selected flavor is the plain pure-Python package with an operator-owned system `libpq` and
  `PSYCOPG_IMPL=python` verified by tests. The exact supported `libpq` package/version, patching,
  TLS roots, and SBOM receipt must be bound by the later implementation gate and environment.
- `psycopg-c`, `psycopg-binary`, `psycopg-pool`, asyncpg, async connections, and runtime pools are
  rejected for this slice. No PostgreSQL connection is authorized by this entry-decision candidate.

### Resolver preview and provenance

The read-only resolver preview produced:

| Package | Preview version | License metadata | Role |
| --- | --- | --- | --- |
| SQLAlchemy | `2.0.51` | MIT | selected tooling dependency, Core only |
| Alembic | `1.18.5` | MIT | selected tooling dependency, offline only |
| psycopg | `3.3.4` | LGPL-3.0-only | selected tooling dependency, plain Python implementation |
| greenlet | `3.5.3` | MIT AND PSF-2.0 | conditional SQLAlchemy transitive dependency |
| Mako | `1.3.12` | MIT | Alembic template dependency |
| MarkupSafe | `3.0.3` | BSD-3-Clause | Mako dependency |
| typing-extensions | `4.16.0` | PSF-2.0 | shared resolver result; currently already locked at `4.15.0` |

The future implementation gate must reproduce the complete `uv.lock` delta, package URLs, hashes,
markers, licenses, and dependency graph. Resolver output here is a selection snapshot, not install
authority. Any additional direct or transitive package, prerelease, VCS source, alternate index,
binary Psycopg extra, or license mismatch stops the slice for a new decision.

Official dependency references:

- [SQLAlchemy on PyPI](https://pypi.org/project/SQLAlchemy/)
- [Alembic on PyPI](https://pypi.org/project/alembic/)
- [Psycopg on PyPI](https://pypi.org/project/psycopg/)

All three direct requirements belong in a non-default `pis3` dependency group. They must not become
ordinary application runtime dependencies.

## Selected Schema And Import Contract

The proposed slice is limited to `sandbox_descriptors` and an isolated, non-serving schema epoch.
It may later define:

- the existing primary identifier, accepted status, UTC timestamps, payload digest, and payload;
- a closed accepted-status constraint and the existing created-at index;
- a PostgreSQL JSONB representation with a canonical-JSON digest verification boundary;
- strict UTC timestamp parsing with round-trip verification; and
- deterministic offline PostgreSQL DDL and one linear Alembic revision head.

The candidate schema is not the current SQLite runtime schema and must not be imported by the API.
It cannot alter the SQLite database, current table/index inventory, stored bytes, public responses,
audit ordering, or trusted-host authority derivation. JSONB does not preserve source JSON bytes, so
import verification must compare the canonical reserialization and stored SHA-256 digest rather
than database physical representation. No implementation may depend on physical row order.

## Transaction And Repository Ownership Contract

The following semantics are selected for later PIS-003/PIS-006 work even though
`PIS-003-SD-PG-001` may not implement a runtime transaction adapter:

1. Ithildin application services own the outer transaction boundary. Repositories never commit or
   roll back independently and never expose or accept `sqlite3.Connection`, SQLAlchemy
   `Connection`, Psycopg connection/cursor, session, or dialect objects in aggregate protocols.
2. A future Ithildin-owned synchronous transaction handle is scoped to one request/operation and
   one connection. It is not shared across threads or retained by records. Async transaction APIs
   are out of scope until a separately demonstrated need exists.
3. Authoritative mutation paths use one explicit outer transaction. Nested authority transactions
   and savepoints are denied; helper functions join the caller-owned handle. Read-only operations
   cannot be silently upgraded to writes.
4. SQLite mutation characterization retains explicit `BEGIN IMMEDIATE` where currently required.
   PostgreSQL must use explicit constraints, compare-and-set predicates, row/advisory locking, and
   a selected isolation level; it must not emulate `BEGIN IMMEDIATE` with a process-local lock.
5. SQLAlchemy autobegin is not application authority. A future coordinator must explicitly open,
   commit, or roll back the transaction and reject a connection already carrying unexpected state.
6. No general transparent retry is allowed. A later gate may permit a small bounded retry only for
   identified serialization/deadlock failures before external effects and under a durable
   idempotency key. Connection loss during or after commit is `ambiguous_commit`; it is never
   replayed as fresh work and must enter reconciliation/recovery-required handling.
7. Ordering is expressed through explicit stable keys. SQLite `rowid`, insertion/physical order,
   and an order-by timestamp without an explicit tie-breaker cannot become portable authority.
8. Constraints must close identifiers, status values, foreign keys, uniqueness, nullability, and
   compare-and-set preconditions in both repository predicates and the database where appropriate.
   Dialect-specific differences must fail tests rather than be normalized silently.
9. Canonical evidence digests are computed by Ithildin over canonical JSON. PostgreSQL JSONB may be
   used for queryable content only when the separately stored digest and import verification prove
   semantic equivalence.
10. An isolated import starts from a frozen, known-version SQLite source, requires an empty
    PostgreSQL target, commits all imported descriptor rows in one transaction, and then verifies
    source/target IDs, counts, constraints, canonical payload bytes, payload hashes, timestamps, and
    authority-generation inputs. Any mismatch or interruption quarantines/discards the target; no
    in-place repair, activation flag, reverse import, or dual write exists.
11. The Phase 1 target remains one transaction for domain mutation, authoritative audit event, and
    export-outbox row. The current descriptor-commit-then-audit residual remains unchanged until
    the separately gated PIS-006 audit/outbox work; `PIS-003-SD-PG-001` must neither hide nor repair it.

## Proposed `PIS-003-SD-PG-001` Scope

After exact source review and a separate implementation gate, the proposed slice may be limited to:

- adding only the three selected exact requirements to a non-default `pis3` tooling group and the
  reviewed lock delta;
- adding an offline-only schema metadata module for `sandbox_descriptors`;
- adding an offline Alembic environment with one linear candidate revision;
- producing deterministic PostgreSQL DDL without a driver or database connection;
- adding a synchronous Core/Psycopg importer that accepts only an externally supplied isolated test
  connection, enforces an empty target, uses `NullPool`, and produces a secret-free verification
  receipt while leaving the target non-activatable;
- tests for exact table, constraint, index, type, head, and rendered-SQL invariants;
- tests proving no API/startup import, no database connection, no SQLite schema/runtime change, no
  ORM use, and no second aggregate; and
- documentation, validator, and review evidence for that exact slice.

The future implementation gate must enumerate every allowed path. The default proposed code roots
are `apps/api/src/ithildin_api/storage_schema.py`,
`apps/api/src/ithildin_api/storage_import.py`, `db/alembic/`, and
`tests/test_storage_schema_import.py`, plus `pyproject.toml`, `uv.lock`, and bounded gate/docs
files. `apps/api/src/ithildin_api/app.py`, current store modules, current SQLite migrations, public
routes, deployment files, manifests, policies, Node code, Mission Control, and audit writer code
remain protected.

## Required Evidence Before Implementation Completion

The later implementation gate must require:

- exact direct/transitive dependency lock, source, hash, marker, and license inventory;
- Core-only import inspection and absence of ORM/session/async/runtime-pool imports;
- one Alembic head, deterministic offline PostgreSQL SQL, and no live URL or credential handling;
- exact schema object, primary key, status check, timestamp, JSONB, digest, and index assertions;
- canonical payload and UTC timestamp round-trip fixtures, including rejection of malformed,
  duplicate, unknown-status, digest-mismatch, naive-time, and non-object JSON records;
- exact plain-Psycopg implementation and system-`libpq`/TLS/SBOM receipt; no binary/C/pool extra;
- real isolated PostgreSQL import verification through an externally supplied test DSN, with no
  repository-controlled service lifecycle, embedded credentials, or application startup migration;
- unchanged current SQLite schema, behavior, audit residual, public API, dependency-unrelated code,
  policy, manifests, and 24-tool surface;
- clean focused tests, lint, mypy, docs, no-new-powers, release check, and exact-candidate review; and
- rollback proof before any target activation or runtime data exists.

Generated or compiled DDL is evidence only. It does not authorize execution, a database service,
an import, runtime PostgreSQL, production custody, release, promotion, or the next PIS slice.

## Rollback

The proposed rollback is
`revert_pis_003_sd_pg_001_and_discard_isolated_target_before_activation`.

Rollback removes the schema/import artifacts and exact dependency lock delta and discards the
isolated PostgreSQL target. The source SQLite database remains untouched. No reverse import,
in-place repair, dual write, runtime failback, or activation is allowed. If any authority-bearing
target was activated or any production/runtime data was used, this rollback contract is invalid and
the work must stop as an out-of-scope incident.

## Closed Authority And Next Gate

This entry-decision candidate records:

- `pis_003_entry_decision_recorded: true`;
- `pis_003_sd_pg_001_selected: true`;
- `exact_candidate_source_review_required: true`;
- `implementation_gate_required: true`;
- `pis_003_sd_pg_001_implementation_allowed: false`;
- `dependency_changes_allowed: false`;
- `sqlalchemy_allowed: false`;
- `alembic_allowed: false`;
- `psycopg_use_allowed: false`;
- `offline_schema_artifact_implementation_allowed: false`;
- `migration_execution_allowed: false`;
- `database_connections_allowed: false`;
- `runtime_postgres_allowed: false`;
- `production_identity_allowed: false`;
- `new_power_classes_allowed: false`;
- `release_allowed: false`;
- `production_promotion_allowed: false`;
- `uat_complete: false`; and
- `uat_required_now: false`.

The next required action is `review_pis_003_entry_decision_exact_candidate`. A clean validator does
not flip any false authority. A zero-finding review may allow preparation of the separate
`PIS-003-SD-PG-001` implementation gate; it may not authorize implementation directly.

## Stop Lines

Stop before changing dependencies, lockfiles, runtime code, schemas, migrations, deployment,
database services, or credentials until the exact entry-decision review and separate implementation
gate are committed and valid. Stop for any Psycopg installation or use before that gate,
SQLAlchemy ORM/session/async use, live
Alembic connection outside the gated isolated tooling command, startup migration, automatic
migration, repository-controlled Docker/socket service lifecycle, second aggregate, current SQLite schema
change, API behavior change, audit-ordering change, production identity, enterprise RBAC, remote
administration, backup/restore runtime, retention enforcement, new governed power, public security
claim, release/promotion claim, or UAT claim.

Also stop on a critical/high trust-boundary finding or the same authoritative gate failure three
times.

## Validation

Validate this decision from the repository root with:

```sh
make production-identity-storage-pis-003-entry-decision-check
```

Passing proves only the exact planning decision, selected future slice, protected baseline,
dependency snapshot, transaction contract, 24-tool boundary, and false implementation authority.
