# Production Identity And Storage PIS-003 SD-PG-001 Implementation Gate

Status: committed implementation-gate candidate pending exact-candidate source review; no
implementation authority is active.

Gate ID: `PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-IMPLEMENTATION-GATE`.

Parent review: `PRD-PROD-IAM-STORAGE-PIS-003-ENTRY-REVIEW`.

Gate baseline commit: `ebb656ac8e5b0f428641092135d7e99b5845fa85`.

Implementation slice: `PIS-003-SD-PG-001`.

Gate outcome: `select_exact_bounded_candidate_pending_gate_review`.

Current governed tool count: `24`.

This gate binds the exact file boundary, dependency lock preview, transaction ownership, evidence,
rollback, and stop lines for one isolated `sandbox_descriptors` PostgreSQL schema/import proof. It
does not authorize implementation, dependency changes, package use, database connections,
migration execution, a PostgreSQL service, application startup integration, runtime PostgreSQL,
production identity, release, promotion, or UAT. A separate exact-candidate source review must
clear this gate before any implementation path may change.

The closed companion contract is
`docs/codex/production-identity-storage-pis-003-sd-pg-001-implementation-gate.json`. Its exact
path sets, preview hashes, package inventory, authority map, and next action are authoritative.
Prose cannot broaden the closed contract.

## Exact Dependency-Lock Preview

The preview was generated from the unchanged gate baseline in a detached temporary worktree using
`uv 0.11.12` and `uv lock`. The preview changed only `pyproject.toml` and `uv.lock`, added five and
217 lines respectively, changed no existing locked version, and removed no package.

The only direct additions are a non-default `pis3` group containing:

- `SQLAlchemy==2.0.51`;
- `alembic==1.18.5`; and
- `psycopg==3.3.4`.

The exact resulting preview digests are:

- `pyproject.toml`: `8f260ab9cc8508cbe856258e86bc7960a7ee073156fe4c2981e0f6854e381627`;
- `uv.lock`: `a0ea98764d069193226a9debe837f37655ee707cb17dcdf6731b922883a4dafb`.

The complete added package set is SQLAlchemy `2.0.51`, Alembic `1.18.5`, psycopg `3.3.4`,
greenlet `3.5.3`, Mako `1.3.12`, MarkupSafe `3.0.3`, and Windows-only tzdata `2026.3`. The preview
does not upgrade typing-extensions; it retains the existing `4.15.0` lock. The entry-decision's
universal resolver snapshot listed typing-extensions `4.16.0` and did not list tzdata. This gate
intentionally supersedes that preview detail with the exact repository `uv.lock` delta while
preserving the same three selected direct pins.

The `uv.lock` preview digest binds all registry URLs, artifact hashes, markers, and dependency
edges. Any different digest, added or removed package, changed existing version, VCS source,
alternate index, prerelease, `psycopg-c`, `psycopg-binary`, `psycopg-pool`, asyncpg, or unexpected
license requires a new gate decision. The dependency group remains non-default and must not become
an application runtime dependency.

Psycopg remains the plain synchronous pure-Python package. `PSYCOPG_IMPL=python` is required for
future driver evidence. No supported system `libpq` is present in the current gate-preparation
environment, so this gate does not pretend that a connection can be proved here. This gate cannot
authorize a connection even if environment evidence later appears. A separate connection-evidence
gate must bind the operator-supplied nonproduction target, exact `libpq` version/source, patch
provenance, TLS-root source, SBOM/license receipt, target-discard owner, and rollback receipt before
the first isolated connection.

## Phase-Aware Validator Transition

Predecessor PIS validators preserve their own historical truth through exact Git-object identity;
they do not require mutable HEAD dependency files to remain frozen after a separately reviewed
successor gate. This gate validator accepts exactly two dependency states:

1. `preimplementation`: baseline `pyproject.toml` and `uv.lock` hashes with the selected packages
   absent; or
2. `post_review_implementation`: the exact preview hashes, but only when the durable gate-review
   validator is present, valid, bound to the reviewed gate commit, reports zero findings, and grants
   no authority beyond the closed post-review ceiling.

Any other dependency or lock state fails closed. The successor implementation validator must also
enforce the exact lock delta and implementation path inventory. Mutation evidence must prove that
the exact reviewed transition keeps every required predecessor and `release-check` gate valid while
unapproved dependency drift remains invalid.

## Exact Implementation Boundary

After a clean exact gate review, implementation may change only the closed contract's
`implementation_allowed_paths`. The slice may:

- add the exact non-default dependency group and lock delta;
- define SQLAlchemy Core metadata for only the `sandbox_descriptors` aggregate;
- add one linear Alembic revision and deterministic offline PostgreSQL DDL rendering;
- add a synchronous importer that accepts only a caller-owned SQLAlchemy `Connection`, requires an
  empty quarantined target, and never creates an engine/pool or commits/rolls back;
- add a test-only harness whose code accepts an external-DSN parameter and defines synchronous
  `NullPool` ownership, without invoking that harness, loading the driver, opening a connection, or
  executing a migration under this implementation gate;
- emit a secret-free verification receipt over explicit IDs, counts, UTC timestamps, canonical
  JSON bytes, and Ithildin-owned SHA-256 digests; and
- add bounded tests, implementation evidence, validators, and documentation wiring.

The protected runtime paths include the API application and configuration, current SQLite storage
and descriptor service, tool manifest lock, policies/manifests, public routes, Node, Mission
Control, deployment, and audit-writer behavior. They cannot change in this slice. No implementation
file may be imported by API startup.

## Transaction And Connection Contract

- The caller/application service owns the explicit outer transaction; repositories and importers
  never commit or roll back.
- Aggregate protocols do not expose SQLAlchemy, Psycopg, SQLite, session, cursor, engine, or dialect
  objects.
- SQLAlchemy Core is allowed only in the isolated schema/import modules. ORM, Session, async APIs,
  runtime pools, implicit application authority through autobegin, nested authority transactions,
  savepoints, and transparent retries are forbidden.
- The importer accepts a caller-owned SQLAlchemy `Connection` only. It cannot accept a DSN, create
  an engine or pool, open a connection, or control a service lifecycle.
- The test harness implementation alone may define an externally supplied isolated-test DSN
  parameter. It uses `NullPool` by construction and never persists or logs the DSN or credentials,
  but executing that path remains forbidden until a separate connection-evidence gate.
- Alembic offline rendering must not require a URL or connection. Online migration evidence, if
  later authorized by a separate connection-evidence gate, may receive only the caller-owned
  connection from the test harness.
- Connection loss during or after commit is `ambiguous_commit`; it requires reconciliation and is
  never replayed as fresh work.

## Evidence And Done-When

Offline implementation is not complete until the closed offline evidence list passes. In
particular it must prove
the exact dependency delta; one Alembic head; deterministic offline SQL; exact schema objects,
constraints, JSONB and index contract; Core-only imports; canonical JSON and strict UTC round trips;
negative fixture rejection; no runtime/startup import; unchanged SQLite behavior; unchanged audit
residual; unchanged policy, manifests, public API, and 24-tool count; phase-aware predecessor
validity; rollback bound before any connection; and proof that the test harness and driver were not
executed.

This implementation gate ends at
`offline_implementation_complete_connection_evidence_gate_pending`. Real isolated PostgreSQL import
evidence is a later separately reviewed gate. Offline implementation may be exact-candidate
reviewed and closed on its own evidence, but cannot claim database verification, full PIS-003
completion, runtime readiness, or production readiness.

The deferred connection-evidence list requires the separate gate, exact system-libpq/TLS/SBOM
receipt, externally supplied isolated target, secret-safe failure evidence, real empty-target import
verification, and target discard before activation or runtime use. None is an offline implementation
completion condition and none is authorized here.

Focused checks run before broader repository gates. Before an implementation candidate is
committed for review, it must pass its focused tests, Ruff, mypy, docs checks,
`make agent-workflow-check`, `make release-check`, and `make review-candidate`. Generated SQL,
receipts, tests, and green gates are evidence only; they do not authorize runtime use, release,
promotion, or UAT.

## Rollback

Rollback is `revert_exact_candidate_and_discard_isolated_target_before_activation`.

Before any database connection, the implementation must materialize and validate a secret-free
rollback receipt bound to the exact candidate and target label. If an isolated target is used, it
must remain empty or quarantined until verification and must be discarded before any activation or
runtime use. Rollback removes the exact dependency delta and all slice artifacts; the SQLite source
is never modified. There is no reverse import, dual write, in-place repair, activation, runtime
failback, or production data handling. If any authority-bearing target is activated, the rollback
contract is invalid and work stops as an out-of-scope incident.

## Closed Authority And Next Action

This gate candidate records:

- `pis_003_sd_pg_001_implementation_gate_recorded: true`;
- `pis_003_sd_pg_001_candidate_selected: true`;
- `exact_candidate_source_review_required: true`;
- `pis_003_sd_pg_001_implementation_allowed: false`;
- `dependency_changes_allowed: false`;
- `sqlalchemy_core_use_allowed: false`;
- `alembic_offline_use_allowed: false`;
- `psycopg_plain_sync_use_allowed: false`;
- `offline_schema_artifact_implementation_allowed: false`;
- `offline_migration_artifact_implementation_allowed: false`;
- `isolated_importer_implementation_allowed: false`;
- `test_harness_implementation_allowed: false`;
- `isolated_test_connection_allowed: false`;
- `migration_execution_allowed: false`;
- `database_connections_allowed: false`;
- `postgres_service_allowed: false`;
- `runtime_postgres_allowed: false`;
- `production_identity_allowed: false`;
- `new_power_classes_allowed: false`;
- `release_allowed: false`;
- `production_promotion_allowed: false`;
- `uat_complete: false`; and
- `uat_required_now: false`; and
- `connection_evidence_gate_required: true`.

The next required action is
`review_pis_003_sd_pg_001_implementation_gate_exact_candidate`. A clean validator does not flip any
false authority. Only a zero-finding exact-candidate gate review may grant the bounded
post-review authority ceiling: the exact non-default dependency delta, SQLAlchemy Core/offline
Alembic artifact work, importer implementation, and test-harness implementation. That ceiling keeps
Psycopg driver use, external DSN consumption, connections, migration execution, PostgreSQL
services, runtime, production, release, promotion, and UAT authority false. A separate
connection-evidence gate remains required.

The closed post-review ceiling is:

- `pis_003_sd_pg_001_implementation_allowed: true`;
- `dependency_changes_allowed: true`;
- `sqlalchemy_core_use_allowed: true`;
- `alembic_offline_use_allowed: true`;
- `psycopg_plain_sync_dependency_allowed: true`;
- `psycopg_plain_sync_use_allowed: false`;
- `offline_schema_artifact_implementation_allowed: true`;
- `offline_migration_artifact_implementation_allowed: true`;
- `isolated_importer_implementation_allowed: true`;
- `test_harness_implementation_allowed: true`;
- `isolated_test_connection_allowed: false`;
- `migration_execution_allowed: false`;
- `database_connections_allowed: false`;
- `postgres_service_allowed: false`;
- `runtime_postgres_allowed: false`;
- `production_identity_allowed: false`;
- `release_allowed: false`;
- `production_promotion_allowed: false`;
- `uat_complete: false`;
- `uat_required_now: false`; and
- `connection_evidence_gate_required: true`.

## Stop Lines

Stop for any changed path outside the closed implementation boundary; lock-preview drift; system
package or PostgreSQL service installation; repository-controlled Docker/socket lifecycle;
embedded, persisted, or logged DSN/credential; default-enabled dependency; ORM/session/async/pool
use; startup migration; current SQLite or audit-ordering change; second aggregate; API behavior;
runtime PostgreSQL; production identity/RBAC; remote administration; new governed tool or power;
public security claim; release/promotion claim; or UAT claim.

Also stop on a critical/high trust-boundary finding or the same authoritative gate failure three
times.

## Validation

Validate this gate candidate from the repository root with:

```sh
make production-identity-storage-pis-003-sd-pg-001-implementation-gate-check
```

Passing proves only the exact planning gate, preview hashes, file boundary, rollback, evidence
requirements, 24-tool boundary, and false implementation authority.
