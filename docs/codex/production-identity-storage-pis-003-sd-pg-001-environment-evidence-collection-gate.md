# Production Identity And Storage PIS-003 SD-PG-001 Environment Evidence Collection Gate

Status: environment-evidence-collection gate candidate prepared; exact-candidate source review is
pending, no external target or receipt is selected or collected, and all live authority remains
false.

Gate ID: `PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-ENVIRONMENT-EVIDENCE-COLLECTION-GATE`.

Parent environment-execution-gate review record:
`71774c6161161d46bd2778c653179c9a9be44fac`.

Gate baseline commit: `71774c6161161d46bd2778c653179c9a9be44fac`.

Current governed tool count: `24`.

Validate this gate with:

```sh
make production-identity-storage-pis-003-sd-pg-001-environment-evidence-collection-gate-check
```

The authoritative closed contract is
`docs/codex/production-identity-storage-pis-003-sd-pg-001-environment-evidence-collection-gate.json`.
Its candidate inventory, protected hashes, eleven evidence requirements, collection contract,
future ceiling, live authority, and next action are closed. Prose cannot broaden the contract.

## Purpose And Boundary

The reviewed environment-execution gate established what evidence a future isolated PostgreSQL
connection proof would require. This successor gate defines the smallest reviewable boundary for a
later external target-selection and signed-receipt collection phase. It does not start that phase.

No target is selected or provisioned. No intake directory is created. No ambient environment
variable, credential, DSN, binding key, driver, service, container, database, or host configuration
is enumerated or inspected. No receipt, trust record, manifest, endpoint, certificate, SBOM, or
license artifact is collected. The harness remains check-only and dormant.

The repository will never provision the target, own the signing keys, or create database roles,
grants, services, or containers for this evidence slice. A future external operator must select one
dedicated, nonproduction, quarantined, empty target and must retain custody of all credentials and
private keys. Ithildin may later receive only explicit, secret-free evidence files through a
separately reviewed intake candidate.

## Closed Collection Contract

The future intake root is named but is not created:
`var/review-runs/pis-003-sd-pg-001-external-environment-evidence`. All future inputs must be
explicit file references. Ambient environment discovery, repository-local or output-local receipt
sources, symlinks, writable receipts, private signing keys, plaintext credentials, DSNs, binding
keys, passwords, tokens, and connection strings are forbidden.

The future collection phase must preserve the existing harness formats and patterns for safe target
labels, issuer IDs, run IDs, SHA-256 digests, and HMAC commitments. It may accept one to three
read-only Ed25519 trust records and exactly the two preconnection receipt types:
`preconnection_rollback_receipt` and `target_owner_quarantine_receipt`. Canonical JSON, signature
verification, freshness, exact candidate/run/target/source binding, and complete-set validation are
required. The final discard receipt can exist only after a separately reviewed future connection
and therefore is a requirement, not a present input.

The eleven required evidence categories remain unchanged from the reviewed parent gate. Their
presence fields are all false. The DSN and 32-byte target-binding key are external custody material,
not evidence files; they may not be collected, logged, hashed as plaintext identifiers, rendered,
or placed in any repository or evidence root.

## Narrow Post-Review Ceiling

A zero-finding exact review may raise only a future ceiling for selecting one external quarantined
target by safe label and collecting the closed signed evidence set. It may not permit activation-
candidate preparation, credential inspection, DSN or binding-key consumption, driver loading,
connections, migrations, PostgreSQL services, containers, runtime PostgreSQL, production identity,
release, promotion, or UAT.

This candidate does not raise that ceiling. The live values remain:

- `external_target_selection_allowed: false`;
- `external_environment_receipt_collection_allowed: false`;
- `activation_candidate_preparation_allowed: false`;
- `host_credential_inspection_allowed: false`;
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
- `arbitrary_host_control_allowed: false`;
- `release_allowed: false`;
- `production_promotion_allowed: false`;
- `uat_complete: false`; and
- `uat_required_now: false`.

## Protected Boundary

The reviewed parent gate, dormant connection harness, importer, storage schema, Alembic environment
and revision, API configuration and stores, dependency locks, manifest lock, and 24-tool surface are
protected. The parent validator is repaired only to freeze its historical candidate inventory at
review-record commit `71774c6161161d46bd2778c653179c9a9be44fac`; its reviewed candidate hashes
remain bound to `c1ed12cb98ce263a57cf37f17c6b45ff4fb8596f`.

This gate candidate is limited to twelve paths: common Makefile/README/docs/release wiring, the
decision register and review index, this document and contract, the historical parent-validator
repair, the new validator, and focused release-readiness tests. It adds no runtime import, API,
policy, dependency, schema, migration, tool, executor, or arbitrary host-control surface.

## Authority And Next Action

This gate records:

- `environment_evidence_collection_gate_prepared: true`;
- `exact_candidate_source_review_required: true`;
- `exact_candidate_source_review_complete: false`; and
- every target-selection, collection, activation, execution, runtime, release, promotion, and UAT
  authority listed above as false.

The next required action is
`obtain_independent_sol_xhigh_exact_candidate_review_for_pis_003_sd_pg_001_environment_evidence_collection_gate`.
That review must bind the exact twelve-path candidate and its protected hashes. Sol Ultra is not
required. No review result alone selects a target, collects evidence, activates the harness, or
authorizes execution.
