# Production Identity And Storage PIS-002 Entry Decision Record

Status: committed `PIS-002` entry decision for one bounded dependency-free repository-interface implementation slice.

Decision ID: `PRD-PROD-IAM-STORAGE-PIS-002-ENTRY`.

Parent decision: `PRD-PROD-IAM-STORAGE-PIS-001`.

Decision outcome: `approved_for_bounded_dependency_free_repository_interface_implementation`.

Implementation slice: `PIS-002-SD-001`.

Entry baseline commit: `1f3945b116be9c68c282d0b8f191f39fb9787006`.

Current governed tool count: `24`.

Current `ERG-006` status: `planning_only`.

Current `ERG-007` status: `planning_only`.

Validate this decision with:

```sh
make production-identity-storage-pis-002-entry-decision-check
```

This record selects exactly one current SQLite aggregate and authorizes a narrow internal repository
interface and parity-test implementation over the existing SQLite behavior. It does not authorize a
new dependency, SQLAlchemy, a second aggregate, a public API change, a schema or migration change,
runtime PostgreSQL, production identity, enterprise RBAC, remote administration, a new governed
tool or power class, production promotion, public security-product positioning, or UAT acceptance.

The closed machine-readable companion contract is
`docs/codex/production-identity-storage-pis-002-entry-decision.json`. Its allow and deny booleans,
selected aggregate, baseline hashes, evidence set, and rollback statement are authoritative. Prose
cannot broaden them.

## Reviewed Inputs And Selection Method

- Cleared PIS-001 threat/dependency decision:
  `production-identity-storage-pis-001-threat-model-and-dependency-decision.md`.
- Closed PIS-001 contract: `production-identity-storage-pis-001-decision.json`.
- Zero-open-finding exact-candidate review:
  `production-identity-storage-pis-001-internal-source-review.md`.
- Phase 1 architecture: `production-identity-storage-architecture.md`.
- Current source inventory at entry baseline `1f3945b`.

Candidate stores were compared by table count, direct SQLite connection scopes, explicit transaction
and row-order dependencies, cross-store coordination, audit coupling, authority sensitivity,
existing parity coverage, and migration-free rollback. `SandboxDescriptorStore` is the smallest
meaningful persisted aggregate: it has one table, ordinary parameterized SQLite operations, no
`BEGIN IMMEDIATE`, no `rowid` dependency, and no caller-owned coordinator transaction. It is still
meaningful because authenticated API routes expose it and trusted-host promotion consumes its
workspace, sandbox, payload-hash, and generation authority.

The following were rejected as the first slice:

- audit events because the hash chain depends on serialized writes, `rowid`, JSONL lifecycle, and
  verification/export behavior;
- agent runs because the timeline reads the audit table and depends on `rowid` ordering;
- approvals and trusted-host promotions because they participate in compare-and-set and
  caller-owned multi-store transactions;
- patches because proposals and apply attempts form an approval/filesystem recovery state machine;
- missions, Nodes, configuration, and trust transitions because they use multi-table state,
  nonces, evidence-completion recovery, and `BEGIN IMMEDIATE` transitions.

## Selected Aggregate And Exact Seam

The selected aggregate is `sandbox_descriptors`.

- Current store: `ithildin_api.sandbox_descriptors.SandboxDescriptorStore`.
- Current table: `sandbox_descriptors`.
- Public routes: `POST /sandbox-descriptors`, `GET /sandbox-descriptors`, and
  `GET /sandbox-descriptors/{descriptor_id}`.
- Authority consumers: `TrustedHostPromotionService.create_proposal` and
  `TrustedHostPromotionService._authority_snapshot`.
- Current audit ordering: `descriptor_commit_then_audit_write`.

The allowed implementation is an Ithildin-owned repository protocol implemented by the existing
SQLite adapter. Consumer annotations or injection may target the protocol, but the concrete SQLite
adapter remains the only runtime implementation. A general transaction manager, second backend,
dual write, compatibility shim for PostgreSQL, or speculative cross-aggregate abstraction is not
allowed in `PIS-002-SD-001`.

## Frozen Behavior And Parity Contract

The implementation must preserve all of the following exactly unless this decision is superseded:

1. `sdesc_` identifier shape, `accepted` status, UTC ISO timestamp shape, payload canonicalization,
   SHA-256 payload digest, and safe-detail/summary fields.
2. One `sandbox_descriptors` table and the existing `created_at` index, with no DDL, schema-version,
   backfill, or migration change.
3. Parameterized SQLite statements, explicit current commit points, and SQLite as the only supported
   runtime backend.
4. List limit clamping to `1..200`, `created_at DESC` ordering with its current lack of a secondary
   tie-breaker, grouped status counts, and the existing not-found error label.
5. The exact `SandboxAuthorityRecord` descriptor ID, payload hash, and generation digest used by
   trusted-host proposal authority snapshots.
6. Existing public response bodies, authentication requirements, safe error bodies, and redaction
   posture.
7. Exact `AuditEventType.SANDBOX_DESCRIPTOR_SUBMITTED` emission plus the current minimized
   `safe_audit_metadata` field set and excluded-category/redaction posture.
8. Existing-database restart behavior: a database created before the interface extraction remains
   readable and writable without conversion.

### Deliberately preserved audit residual

The current API commits the descriptor and then writes
`AuditEventType.SANDBOX_DESCRIPTOR_SUBMITTED` through a separate audit transaction. Therefore an
audit failure can leave the descriptor committed while the request fails. That is not the Phase 1
target atomicity model, but changing it in this first interface-only slice would alter observable
failure behavior and cross the audit/transaction trust boundary.

`PIS-002-SD-001` must prove `audit_failure_ordering_parity`: the descriptor remains committed after
an injected post-create audit failure exactly as it does at the entry baseline. A later separately
reviewed transaction-coordination slice must replace this residual; this decision neither hides nor
repairs it.

## Dependency Decision

Interface work begins without a dependency change.

- Use `typing.Protocol`, existing dataclasses/models, and the current `sqlite3` adapter.
- SQLAlchemy 2.0 Core remains `recommended_deferred` until the first aggregate implementation has
  an exact-candidate review and demonstrates that the interface is not shaped around accidental
  SQLite mechanics.
- `pyproject.toml`, `uv.lock`, package manifests, Dockerfiles, and dependency metadata may not
  change in this slice.
- Psycopg, Alembic, PostgreSQL services, connection pools, drivers, migration runners, and provider
  SDKs remain PIS-003-or-later decisions.

## Allowed Implementation Scope

The only code paths that may change for `PIS-002-SD-001` are:

- `apps/api/src/ithildin_api/sandbox_descriptors.py`;
- `apps/api/src/ithildin_api/app.py`, only for repository typing or injection;
- `apps/api/src/ithildin_api/trusted_host_promotions.py`, only for repository typing;
- `tests/test_sandbox_descriptor_repository.py`; and
- `tests/test_api_service.py`, only for route, audit-ordering, restart, and authority parity.

Documentation, validator, and release-gate files may change only to record and verify this exact
slice. No other persisted aggregate, audit writer, policy evaluator, manifest, MCP surface, Node,
mission, approval, patch, trusted-host transition, or placement behavior is in scope.

## Required Evidence

Before the implementation may be called complete, all of these must pass:

- repository-contract parity over the SQLite adapter;
- persisted-record parity, including canonical bytes and payload hash;
- authenticated public-route and safe-error parity;
- audit-failure ordering parity;
- exact audit-event type, minimized metadata, and redaction parity;
- trusted-host authority-record and mismatch-denial parity;
- restart against an entry-baseline database fixture;
- dependency, lockfile, table/index, manifest, and 24-tool invariance;
- focused sandbox-descriptor and trusted-host tests;
- lint, typecheck, docs, no-new-powers, and tool-surface gates; and
- a clean exact-candidate release/review checkpoint with zero critical/high findings.

Generated evidence proves only the tested candidate behavior. It does not authorize another
aggregate, PostgreSQL, production identity, release, production promotion, or UAT acceptance.

## Rollback And Recovery

Rollback is `revert_interface_and_adapter_commit_without_schema_or_data_conversion`.

Because this slice cannot alter schema or stored representation, rollback removes the interface and
adapter seam and restores direct use of the existing SQLite store. Existing rows remain valid; no
reverse migration, data copy, dual write, or repair tool is permitted. If parity cannot be shown,
the candidate is reverted and the entry-baseline implementation remains authoritative.

## Stop Conditions

Stop before implementation or during review if the slice requires any of the following:

- a dependency or lockfile change, including SQLAlchemy;
- a schema, migration, stored-representation, public API, or error-contract change;
- different transaction, commit, audit, ordering, retry, or failure semantics;
- a second aggregate or a general cross-store transaction manager;
- runtime PostgreSQL, OIDC, production identity, enterprise RBAC, remote administration, backup,
  restore, retention, hosted telemetry, SIEM, compliance automation, or remote MCP behavior;
- a new governed tool, manifest change, power class, or public security-product claim; or
- a critical/high trust-boundary finding or the same authoritative gate failure three times.

## Authority Disposition And Next Gate

This entry decision records:

- `pis_002_bounded_implementation_allowed: true` for `PIS-002-SD-001` only;
- `additional_aggregate_implementation_allowed: false`;
- `runtime_behavior_changes_allowed: false`;
- `dependency_changes_allowed: false`;
- `sqlalchemy_allowed: false`;
- `schema_changes_allowed: false`;
- `audit_ordering_changes_allowed: false`;
- `runtime_postgres_allowed: false`;
- `production_identity_allowed: false`;
- `new_power_classes_allowed: false`; and
- `uat_required_now: false`.

The next allowed action after this record passes its focused validator and independent source review
is `implement_pis_002_sandbox_descriptor_repository_boundary`. Passing that implementation does not
authorize PIS-003 or a second PIS-002 aggregate.
