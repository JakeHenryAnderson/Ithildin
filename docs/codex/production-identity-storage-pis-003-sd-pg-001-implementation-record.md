# Production Identity And Storage PIS-003 SD-PG-001 Offline Implementation Record

Status: bounded offline `PIS-003-SD-PG-001` implementation candidate complete; exact-candidate
source review pending.

Implementation ID: `PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-OFFLINE-IMPLEMENTATION`.

Parent gate review:
`PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-IMPLEMENTATION-GATE-REVIEW`.

Implementation baseline commit: `21cc758e2dd438c10f852574528f3ea971825b55`.

Implementation outcome:
`offline_implementation_complete_connection_evidence_gate_pending_exact_source_review`.

Current governed tool count: `24`.

Validate this candidate with:

```sh
make production-identity-storage-pis-003-sd-pg-001-implementation-check
```

The closed machine-readable implementation authority contract is
`docs/codex/production-identity-storage-pis-003-sd-pg-001-implementation-authority.json`. Its exact
schema, hashes, evidence, path inventory, Boolean types, authority ceiling, and next action are
authoritative. Prose cannot broaden the closed contract.

## Implemented Offline Slice

The candidate changes exactly the twenty paths selected by the reviewed gate. It adds the exact
non-default `pis3` group and reviewed lockfile delta, without making those dependencies application
runtime requirements. The direct pins remain SQLAlchemy `2.0.51`, Alembic `1.18.5`, and plain
synchronous Psycopg `3.3.4`; the exact preview digests are reproduced.

`apps/api/src/ithildin_api/storage_schema.py` defines one SQLAlchemy Core application table,
`sandbox_descriptors`, with the existing six logical fields, bounded identifier/status/digest
lengths, timezone-aware timestamps, PostgreSQL JSONB, the primary key, five named checks, and only
the existing `idx_sandbox_descriptors_created_at` index. It defines no default, sequence, identity,
foreign key, extension, trigger, extra uniqueness, second aggregate, engine, pool, or runtime
integration. Its PostgreSQL DDL compiler requires no URL, driver, or connection and is deterministic.

`db/alembic/` contains one linear revision head, `0001_sandbox_descriptors`. The environment has no
`sqlalchemy.url`, renders PostgreSQL SQL through `dialect_name="postgresql"`, and fails closed in
online mode. Downgrade does not attempt destructive in-place rollback; it directs the operator to
discard the quarantined target. The Alembic version table is migration metadata, not a second
Ithildin aggregate.

`apps/api/src/ithildin_api/storage_import.py` separates pure source-snapshot validation from the
caller-owned connection importer. Source rows must have the exact six exported fields and pass
descriptor ID, accepted status, canonical JSON, current `SandboxDescriptorPayload`, payload digest,
strict canonical UTC timestamp, timestamp order, duplicate-key, duplicate-ID, and stable ordering
checks before any connection method can be reached.

The importer accepts only a validated snapshot, a caller-owned SQLAlchemy `Connection`, an exact
candidate/target/rollback context, and a caller-supplied UTC verification time. It requires the
PostgreSQL dialect, an already-open non-nested outer transaction, and an empty target. It performs
one Core bulk insert, reads back in explicit descriptor-ID order, and compares source/target
semantic digests. It cannot accept a DSN, construct an engine or pool, begin/commit/roll back,
retry, repair, activate, or expose a driver object through an aggregate protocol.

The immutable receipt includes the candidate commit, safe target label, rollback-receipt digest,
explicit descriptor IDs and UTC timestamps, source/target record digests, caller-supplied verified
time, transaction ownership/state, quarantine posture, and `database_commit_performed: false`. It
contains no payload, DSN, credentials, host, URL, or connection error.

## Test-Only Connection Contract

`tests/test_storage_schema_import.py` declares the future harness signature with an external DSN,
preconnection rollback receipt, and `NullPool`, but its executable body always raises
`ConnectionEvidenceGateRequired`. It contains no `create_engine` call and is never invoked. The
offline implementation therefore does not load or use Psycopg, consume a DSN, create an engine,
open a connection, execute an online migration, or control a PostgreSQL service.

A separately reviewed connection-evidence gate must change the harness and Alembic online boundary
before any such action. That future gate must bind a real nonproduction target label, exact reviewed
candidate commit, rollback receipt, system `libpq`, TLS roots, SBOM/license receipt, Psycopg Python
implementation, secret-safe failure evidence, semantic import verification, and target discard.

## Focused Evidence And Invariance

The focused suite proves the exact schema metadata, five checks, one index, direct and Alembic SQL
determinism, one Alembic head, pure order-independent snapshot digest, strict negative fixtures,
recording-fake statement order, empty-target and explicit-transaction requirements, semantic
round-trip receipt, no importer transaction control, fail-closed harness contract, driver absence,
runtime import isolation, and 24-tool invariance.

The current SQLite schema, stored representation, descriptor repository, public API, startup,
configuration, audit ordering residual, policy, manifests, Node, Mission Control, and governed tool
surface remain unchanged. The descriptor-commit-then-audit-write residual remains deliberately
unrepaired and is still deferred to the separate PIS-006 work.

These checks prove offline code and artifacts only. They do not prove a database service, live
migration, import against PostgreSQL, connection security, operational rollback, runtime backend,
production identity, enterprise RBAC, release, promotion, or UAT acceptance.

## Rollback And Authority

Rollback remains `revert_exact_candidate_and_discard_isolated_target_before_activation`. The
candidate implements and tests a secret-free receipt contract that must bind the exact candidate
commit and safe target label before a future connection. No target or connection is authorized or
present now, so no live receipt is fabricated. The SQLite source is not modified, and no reverse
import, dual write, in-place repair, migration downgrade, activation, or runtime failback exists.

This candidate records:

- `pis_003_sd_pg_001_offline_implementation_recorded: true`;
- `pis_003_sd_pg_001_offline_candidate_complete: true`;
- `exact_candidate_source_review_required: true`;
- `exact_candidate_source_review_complete: false`;
- `dependency_lock_delta_implemented: true`;
- `offline_schema_implemented: true`;
- `offline_migration_implemented: true`;
- `validated_importer_implemented: true`;
- `refusing_test_harness_contract_implemented: true`;
- `psycopg_plain_sync_dependency_installed: true`;
- `psycopg_plain_sync_use_allowed: false`;
- `test_harness_execution_allowed: false`;
- `database_connections_allowed: false`;
- `migration_execution_allowed: false`;
- `postgres_service_allowed: false`;
- `runtime_behavior_changes_allowed: false`;
- `runtime_postgres_allowed: false`;
- `production_identity_allowed: false`;
- `new_power_classes_allowed: false`;
- `release_allowed: false`;
- `production_promotion_allowed: false`;
- `uat_complete: false`; and
- `connection_evidence_gate_required: true`.

The next required action is `review_pis_003_sd_pg_001_offline_candidate_exact_commit`. Only a
zero-finding independent review may clear preparation of a separate connection-evidence gate. This
candidate itself does not grant connection, migration execution, service, runtime, identity,
release, promotion, or UAT authority.
