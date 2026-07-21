# Production Identity And Storage PIS-003 SD-PG-001 Environment Execution Gate

Status: environment-execution-gate candidate prepared; exact-candidate source review and external
environment evidence are pending, and all execution authority remains false.

Gate ID: `PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-ENVIRONMENT-EXECUTION-GATE`.

Reviewed connection-evidence candidate:
`5d929d8e24e4f529cea08796e614fbf544d066bc`.

Parent review-record commit: `8da9ac630b191a36a2782e5febb45d739030cd48`.

Gate baseline commit: `8da9ac630b191a36a2782e5febb45d739030cd48`.

Current governed tool count: `24`.

Validate this gate with:

```sh
make production-identity-storage-pis-003-sd-pg-001-environment-execution-gate-check
```

The closed companion contract is
`docs/codex/production-identity-storage-pis-003-sd-pg-001-environment-execution-gate.json`.
Its exact path inventory, protected hashes, environment-evidence requirements, execution-candidate
contract, Boolean authority, post-review ceiling, and next action are authoritative. Prose cannot
broaden the closed contract.

## Purpose And Phase Boundary

The reviewed test-only harness now has a zero-finding exact-candidate review and a full release-gate
transcript. That proves the dormant implementation is reviewable; it does not prove that an
external PostgreSQL target, native dependency chain, DSN, binding key, or signed receipt set exists.

This gate creates the separately committed phase boundary required before any environment is
selected or any activation candidate is prepared. It does not change the harness, add a run mode,
load Psycopg, inspect connection environment variables, construct an engine, open a socket, execute
Alembic, or manage a PostgreSQL service or container. `EXECUTION_AUTHORITY_ACTIVE` remains `false`
and the CLI remains check-only.

No green check in this phase authorizes execution. A zero-finding exact review may allow only
selection of an externally managed quarantined target, collection of the closed signed environment
evidence, and preparation of a separate activation candidate. That later candidate must bind its
exact commit and complete receipt set and must receive its own exact review before a single run.

## Gate Environment Evidence State

No target is selected by this gate. No safe target label, trust record, rollback receipt,
target-owner receipt, native dependency receipt, TLS-root receipt, SBOM/license receipt, execution
manifest, DSN, or target-binding key is supplied to or recorded by this gate. The validator does
not enumerate ambient environment variables or infer that credentials are absent from the host.
Psycopg is not loaded by the gate, no connection is attempted, and no online migration executes.
Therefore `environment_execution_ready` is `false`.

The repository will not create that environment. Docker socket access, repository-controlled
service or container lifecycle, package installation, database or role creation, and production
credentials remain outside this gate. The future target and receipt issuers must be external to the
Ithildin runtime and the evidence output root.

## Required External Environment Evidence

Before an activation candidate can be valid, one closed set must provide:

- a safe label for one dedicated, nonproduction, quarantined, empty PostgreSQL target;
- a read-only external Ed25519 trust record with private-key custody outside Ithildin;
- a fresh preconnection rollback receipt bound to the exact candidate, run, target, and source;
- a target-owner/quarantine receipt binding the DSN HMAC, attempt budget, and discard owner;
- exact Python, SQLAlchemy, Alembic, pure-Python Psycopg, loaded `libpq`, and loaded `libssl`
  identity, source, version, architecture, real-path, and digest receipts;
- the exact TLS-root path and digest and the Python/native SBOM and license closure;
- immutable synthetic SQLite source and expected semantic-record digests;
- an externally custodied DSN and 32-byte target-binding key supplied only through the two closed
  environment variables after every non-secret preflight check passes;
- one signed execution manifest with a freshness window no longer than fifteen minutes and a
  confined ignored output root; and
- the named external discard owner available to issue the final post-connection discard receipt.

Missing, malformed, stale, mismatched, duplicated, writable, repository-local, or output-local
evidence fails closed. The DSN and binding key are not evidence artifacts and may never be written,
hashed as plain identifiers, logged, rendered, or accepted from CLI arguments, files, repository
configuration, receipts, or generated packets.

## Selected Future Execution Candidate

Only after this gate receives a zero-finding review and the external evidence set exists may a
separate commit prepare one test-only activation candidate. The selected ceiling is:

1. keep the harness outside all runtime imports and preserve the 24-tool surface;
2. validate the exact candidate, source, manifest, trust record, receipts, native identities,
   output root, and freshness before driver load or connection-environment access;
3. permit one positive run with exactly two attempts: the migration/import transaction and the
   separately budgeted post-rollback absence check;
4. keep each negative network scenario in a separate signed run with exactly one attempt;
5. use one explicit outer transaction, never commit, revalidate its identity, roll it back, prove
   post-rollback absence, and dispose the engine;
6. rehash the immutable source after every outcome and again before final discard acceptance;
7. scan the complete output tree for secret markers and connection strings; and
8. require the named external discard owner's fresh signed receipt before evidence completion.

No transparent retry, target activation, database/role creation, repository-managed service,
runtime PostgreSQL, production identity, reverse import, dual write, in-place repair, release,
promotion, or UAT is within the ceiling.

## Protected Boundary

The exact reviewed harness, implementation record, importer, schema, Alembic environment and
revision, current SQLite stores, API configuration/routes, policy, manifests, dependencies, lock,
and 24-tool surface are protected by the companion contract. The only predecessor change in this
gate makes its 17-path inventory historical at review-record commit
`8da9ac630b191a36a2782e5febb45d739030cd48`; it does not relax any harness or execution check.

This gate candidate is limited to twelve paths: Makefile and README wiring, this document and
contract, the decision register and review index, docs/release registration, the historical
predecessor-validator repair, the new validator, and focused release-readiness tests.

## Authority And Next Action

This gate records:

- `environment_execution_gate_prepared: true`;
- `exact_candidate_source_review_required: true`;
- `exact_candidate_source_review_complete: false`;
- `external_target_selection_allowed: false`;
- `external_environment_receipt_collection_allowed: false`;
- `activation_candidate_preparation_allowed: false`;
- `test_harness_execution_allowed: false`;
- `driver_load_allowed: false`;
- `external_dsn_consumption_allowed: false`;
- `target_binding_key_consumption_allowed: false`;
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
`review_pis_003_sd_pg_001_environment_execution_gate_exact_candidate`. A zero-finding review may
raise only the companion contract's post-review ceiling: external target selection, external
receipt collection, and preparation of a separately committed activation candidate. It may not
authorize the harness to execute or consume a DSN, binding key, driver, connection, migration,
service, container, production identity, runtime PostgreSQL, release, promotion, or UAT.
