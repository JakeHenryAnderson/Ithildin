# Production Identity And Storage PIS-002 Continuation Decision Record

Status: committed PIS-002 continuation decision after the cleared `PIS-002-SD-001` exact
candidate.

Decision ID: `PRD-PROD-IAM-STORAGE-PIS-002-CONTINUATION`.

Parent decision: `PRD-PROD-IAM-STORAGE-PIS-002-ENTRY`.

Decision baseline commit: `308735a670a6bfbe3032de7658366539fe9a3686`.

Reviewed implementation commit: `887de154aeb4c047325eed2372c83deda1fda251`.

Decision outcome:
`close_dependency_free_pis_002_after_one_proven_seam_prepare_pis_003_entry_decision_only`.

Current governed tool count: `24`.

Current `ERG-006` status: `planning_only`.

Current `ERG-007` status: `planning_only`.

This record ends additional dependency-free PIS-002 implementation after the one cleared sandbox
descriptor repository seam. It allows preparation of a separate PIS-003 entry decision only. It
does not authorize PIS-003 implementation, a dependency change, SQLAlchemy, Psycopg, Alembic,
PostgreSQL, schemas, migrations, production identity, release, promotion, or UAT.

## Authoritative Inputs

- The PIS-001 threat/dependency decision keeps SQLite as the compatibility baseline through
  PIS-002 and requires explicit Ithildin repository/transaction boundaries before a second backend.
- The PIS-002 entry decision authorized only `PIS-002-SD-001`, selected
  `SandboxDescriptorStore`, and prohibited a general transaction manager or another aggregate.
- Exact implementation commit `887de154aeb4c047325eed2372c83deda1fda251` introduced
  `SandboxDescriptorRepository` with `SandboxDescriptorStore` as the sole runtime implementation.
- The exact-candidate source review recorded zero critical, high, medium, low, or open findings and
  allowed only this continuation decision to be prepared.
- Exact successor `308735a670a6bfbe3032de7658366539fe9a3686` binds the cleared review to a
  closed authority contract and immutable review-document digest.

The closed companion contract is
`docs/codex/production-identity-storage-pis-002-continuation-decision.json`. Its exact keys, types,
decision identities, inventory, unresolved boundaries, next action, and Boolean authority values
are authoritative. Prose cannot broaden the closed contract.

## What PIS-002 Proved

The completed slice is `PIS-002-SD-001`.

It proved that one meaningful persisted aggregate can be consumed through an Ithildin-owned
repository protocol while preserving the SQLite runtime exactly. The evidence covers:

- all six repository operations through the concrete SQLite adapter;
- canonical stored payload bytes, SHA-256 digest, authority-generation digest, safe details, and
  grouped status behavior;
- authenticated public-route responses, validation, safe failures, limits, and ordering;
- unchanged table and index inventory across an entry-baseline database restart;
- the identical repository object used by the application and trusted-host authority consumer;
- exact minimized audit metadata and redaction exclusions; and
- the deliberately preserved descriptor-commit-then-audit-failure residual.

That evidence is sufficient for the dependency-free seam. It is not evidence for another aggregate,
a portable transaction layer, a second backend, PostgreSQL parity, cross-store atomicity, migration,
production identity, or custody-grade audit.

## Remaining Direct-SQLite Inventory

The current runtime has `13` direct-SQLite modules across the API and audit packages. The remaining
candidate areas are not equivalent low-risk repetitions of the sandbox descriptor seam.

| Area | Current coupling | Continuation disposition |
| --- | --- | --- |
| Agent runs | Timeline reads `audit_events`, uses SQLite `rowid` ordering, and correlates JSON metadata. | Do not freeze a repository shape before ordering and cross-store semantics are decided. |
| Approvals | Compare-and-set and expiry behavior plus `insert_on_connection(sqlite3.Connection)` for caller-owned transactions. | Do not encode a driver-specific transaction object as a nominally backend-neutral interface. |
| Nodes | Enrollment, authentication, replay, revocation, heartbeat, and key rotation use multi-table `BEGIN IMMEDIATE` transitions. | Require a later explicit transaction and authority-state contract. |
| Node configuration and trust | Signed generation, rollback, acknowledgment, and trust-transition state use immediate transactions. | Keep current SQLite behavior until portable locking and generation semantics are decided. |
| Missions and reports | Multi-table staged/finalized state coordinates audit IDs, hashes, completion, and recovery-required outcomes. | A protocol alone would not prove interruption or cross-store recovery equivalence. |
| Patch proposals | Proposal and apply-attempt state combines approval, audit, filesystem effects, and recovery. | Database rollback cannot stand in for external-effect rollback. |
| Trusted-host promotions | Proposal/approval atomic insertion, execution reservation, placement outcomes, and audit completion use several immediate transactions. | Preserve the reviewed coordinator until a portable transaction design is separately gated. |
| Audit | Serialized hash-chain writes depend on `BEGIN IMMEDIATE`, `rowid`, and SQLite/JSONL lifecycle consistency. | Reserve canonical audit and outbox design for its later reviewed storage work. |
| Migration and backup utilities | Existing-database verification, backup, and trusted-host version migration directly use SQLite. | These are schema, migration, and recovery concerns, not another dependency-free repository seam. |

## Continuation Decision

No second PIS-002 aggregate is selected. No runtime candidate follows this decision.

Extracting another `Protocol` now would either repeat the already-proven injection pattern or expose
SQLite-specific connection, ordering, locking, and recovery mechanics as if they were portable.
That would create an accidental abstraction before the database dialect, transaction, migration,
and import contracts are selected.

The next required action is `prepare_pis_003_entry_decision_record`.

PIS-003 entry-decision preparation may evaluate the exact dependency, dialect, transaction,
schema/migration, isolated test-service, and import-verification design. It may not install or use a
dependency, start PostgreSQL, create or migrate a schema, change runtime behavior, or authorize a
second backend. Any implementation still requires a separate committed PIS-003 implementation
gate after dependency, license, provenance, packaging, rollback, and failure evidence are reviewed.

## Required PIS-003 Entry Questions

A future PIS-003 entry decision must answer all of the following before implementation:

1. whether SQLAlchemy 2.0 Core is selected and its exact pinned line, transitive inventory, license,
   provenance, upgrade policy, SQL-logging posture, and Core-only boundary;
2. whether Psycopg 3 is selected, including pure-Python, local-build, or binary packaging, libpq and
   OpenSSL ownership, TLS `verify-full`, credential handling, redistribution, and SBOM impact;
3. whether Alembic is selected as an offline/operator migration surface, with one linear head,
   generated-SQL review, migration-role isolation, lock behavior, and irreversible boundaries;
4. the backend-neutral transaction handle and repository ownership model without driver objects in
   application aggregate contracts;
5. which one aggregate and transaction path is first, with SQLite characterization before any
   second-backend adapter is exercised;
6. exact SQLite/PostgreSQL parity for ordering, compare-and-set behavior, constraints, serialization,
   cancellation, connection loss before/after commit, ambiguous outcome, restart, and rollback;
7. isolated schema/import verification with production startup disabled and no dual-write or
   synthesized authority; and
8. the exact implementation paths, protected artifacts, rollback boundary, source-review gate, and
   stop conditions.

## Closed Authority

This decision records:

- `pis_002_sd_001_source_review_complete: true`;
- `pis_002_dependency_free_interface_phase_complete: true`;
- `additional_pis_002_aggregate_implementation_allowed: false`;
- `pis_003_entry_decision_preparation_allowed: true`;
- `pis_003_implementation_allowed: false`;
- `dependency_evaluation_allowed: true` for decision preparation only;
- `dependency_changes_allowed: false`;
- `sqlalchemy_allowed: false`;
- `psycopg_allowed: false`;
- `alembic_allowed: false`;
- `schema_changes_allowed: false`;
- `database_migrations_allowed: false`;
- `runtime_postgres_allowed: false`;
- `production_identity_allowed: false`;
- `new_power_classes_allowed: false`;
- `release_allowed: false`;
- `production_promotion_allowed: false`;
- `uat_complete: false`; and
- `uat_required_now: false`.

## Stop Lines

Stop before changing any runtime file, persisted aggregate, generic connection/session/transaction
abstraction, cross-store coordinator, SQL/DDL, schema, migration/backup behavior, public route,
error label, audit ordering, storage representation, policy, manifest, or governed tool.

Also stop before adding or changing dependencies or lockfiles; starting a database service;
introducing PostgreSQL, OIDC, enterprise RBAC, remote administration, hosted trust, SIEM delivery,
compliance automation, release/promotion authority, public security-product positioning, or UAT
claims; or continuing past a critical/high trust-boundary finding.

## Validation

Validate this decision from the repository root with:

```sh
make production-identity-storage-pis-002-continuation-decision-check
```

Passing this check proves only the exact planning/governance decision, the protected PIS-002
evidence, the 13-module inventory, the 24-tool boundary, and the authority denials above. It does not
approve PIS-003 implementation or any runtime, dependency, schema, migration, identity, release,
promotion, production-readiness, or UAT claim.
