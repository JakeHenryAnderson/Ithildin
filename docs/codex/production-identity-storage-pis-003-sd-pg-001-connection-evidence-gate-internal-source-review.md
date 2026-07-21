# Production Identity And Storage PIS-003 SD-PG-001 Connection Evidence Gate Internal Source Review

Status: `PIS-003-SD-PG-001` connection-evidence gate exact-candidate source review complete; no
open findings.

Review ID: `PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-CONNECTION-EVIDENCE-GATE-REVIEW`.

Review disposition: `cleared_for_connection_evidence_implementation_only`.

Reviewed exact commit: `86b2074493410019914b8190e1cc9e079c0ce929`.

Superseded NO-GO commit: `08937f3f83321d64bd6b1604d9af8012b8d9f5aa`.

Gate baseline commit: `bf26418b5f27b1fcd08552758e4387867b5eafe0`.

Review method: independent read-only GPT-5.6 Sol xhigh review. Sol Ultra was not used.

Critical findings: `0`.

High findings: `0`.

Medium findings: `0`.

Low findings: `0`.

Open findings: `0`.

Current governed tool count: `24`.

Validate this disposition with:

```sh
make production-identity-storage-pis-003-sd-pg-001-connection-evidence-gate-internal-review-check
```

The closed machine-readable review authority contract is
`docs/codex/production-identity-storage-pis-003-sd-pg-001-connection-evidence-gate-review-authority.json`.
Its exact schema, Boolean types, findings, reviewed identity, path hashes, next action, and
allow/deny values are authoritative. Prose cannot broaden the closed contract.

## Exact Candidate And Review History

The reviewed candidate is the two-commit gate lineage from original candidate
`08937f3f83321d64bd6b1604d9af8012b8d9f5aa` through repaired successor
`86b2074493410019914b8190e1cc9e079c0ce929`. The baseline-to-successor inventory contains exactly
the eleven declared gate, contract, validator, documentation, wiring, and readiness-test paths.

The first exact-commit review returned NO-GO with one medium finding. The target-owner/quarantine
receipt named a `discard_owner_id`, but the final discard receipt was not machine-bound to that
owner; any otherwise trusted issuer allowed to sign the receipt type could substitute.

The repaired successor requires the signed `target_discard_receipt.issuer_id` to equal the earlier
`target_owner_quarantine_receipt.assertion.discard_owner_id`. The trusted issuer record therefore
binds the named operational discard owner to the exact Ed25519 key that signs final discard.
Adversarial removal and permissive-substitution mutations both fail closed. The independent
re-review found no critical, high, medium, low, or open finding.

## Verified Evidence

The review verified:

- exact baseline, superseded candidate, repair lineage, eleven-path inventory, and candidate path
  hashes;
- canonical URI parsing, fail-closed ambient `PG*` rejection, and the closed HMAC target-binding
  payload and ephemeral-key custody;
- Ed25519 envelope, payload, assertion, trust-record, fingerprint, time-window, provenance, and
  named discard-owner relationships;
- native system-`libpq`, TLS backend, SBOM, license, real-path, digest, architecture, and post-load
  identity requirements;
- exact positive and negative connection-attempt budgets, rollback/discard ordering, safe failure
  categories, and secret-free evidence rules;
- protected implementation hashes, the unchanged 24-tool surface, and the separation between
  implementation authority and execution authority;
- nine focused connection-evidence tests, two predecessor regression tests, independent
  owner-binding removal/substitution mutations, Ruff, strict mypy, and `git diff --check`; and
- the full exact-candidate release gate, including 1,659 Python tests and 59 UI tests.

Only deterministic offline Alembic SQL rendering occurred. No DSN was consumed, Psycopg driver
loaded, engine constructed, database connection opened, online migration executed, or PostgreSQL
or container service started or controlled.

## Authority And Next Gate

This disposition records:

- `exact_candidate_source_review_complete: true`;
- `connection_evidence_implementation_allowed: true`;
- `environment_receipt_implementation_allowed: true`;
- `test_harness_implementation_allowed: true`;
- `synthetic_snapshot_reader_implementation_allowed: true`;
- `online_alembic_caller_connection_implementation_allowed: true`;
- `failure_evidence_implementation_allowed: true`;
- `execution_preflight_implementation_allowed: true`;
- `psycopg_plain_sync_use_allowed: false`;
- `external_dsn_consumption_allowed: false`;
- `test_harness_execution_allowed: false`;
- `database_connections_allowed: false`;
- `migration_execution_allowed: false`;
- `postgres_service_allowed: false`;
- `container_lifecycle_allowed: false`;
- `runtime_behavior_changes_allowed: false`;
- `runtime_postgres_allowed: false`;
- `production_identity_allowed: false`;
- `release_allowed: false`;
- `production_promotion_allowed: false`;
- `uat_complete: false`; and
- `uat_required_now: false`.

The next allowed action is `implement_pis_003_sd_pg_001_connection_evidence_candidate`. It may
implement only the closed test-only harness, environment receipt and execution-preflight machinery,
synthetic frozen-snapshot reader, caller-owned Alembic online path, secret-safe evidence, tests,
documentation, and validators within the gate's exact implementation boundary.

It may not load or use Psycopg, read an external DSN or binding key, execute the harness, open a
database connection, run a migration, install or manage PostgreSQL or a container, alter runtime
behavior, enable production identity or RBAC, release, promote, or mark UAT complete. The implemented
harness requires another exact-candidate source review and a separate environment-specific execution
preflight before any driver load or connection can be considered.
