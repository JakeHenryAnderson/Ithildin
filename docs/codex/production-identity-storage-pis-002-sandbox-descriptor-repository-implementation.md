# Production Identity And Storage PIS-002 Sandbox Descriptor Repository Implementation

Status: implemented bounded `PIS-002-SD-001` candidate; independent exact-candidate source review
and release checkpoint pending.

Parent decision: `PRD-PROD-IAM-STORAGE-PIS-002-ENTRY`.

Implementation baseline commit: `934ebaa4ccd5d03032e269473198e7c94755c13c`.

Selected aggregate: `sandbox_descriptors`.

Current governed tool count: `24`.

Validate the bounded implementation with:

```sh
make production-identity-storage-pis-002-sandbox-descriptor-repository-check
```

This candidate introduces the Ithildin-owned `SandboxDescriptorRepository` protocol and makes the
existing `SandboxDescriptorStore` its sole concrete SQLite implementation. The application and
trusted-host promotion service now depend on the internal protocol for typing and injection. The
runtime object, database path, SQL statements, public routes, response shapes, audit writer, and
authority calculations remain unchanged.

## Implemented Seam

The protocol freezes the existing operations:

- `initialize()`;
- `create()` returning `SandboxDescriptorRecord`;
- `list(limit=...)`;
- `get(descriptor_id)`;
- `authority_record(descriptor_id)`; and
- `status()`.

`SandboxDescriptorStore` remains the only runtime implementation. This slice adds no backend
selection, connection factory, session abstraction, transaction manager, compatibility layer, dual
write, or generic repository framework. The seam is intentionally shaped by current aggregate
behavior and can be reviewed before any dependency or PostgreSQL decision.

## Frozen Runtime Behavior

The implementation preserves:

- the single `sandbox_descriptors` table and `idx_sandbox_descriptors_created_at` index;
- canonical JSON persistence, SHA-256 payload hashes, `sdesc_` IDs, `accepted` status, and current
  timestamp behavior;
- list clamping to `1..200`, `created_at DESC` ordering, status summaries, and the exact not-found
  error label;
- authenticated public routes and safe response/error bodies;
- the exact `SandboxAuthorityRecord` payload hash and generation digest consumed by trusted-host
  promotion;
- `AuditEventType.SANDBOX_DESCRIPTOR_SUBMITTED` and the current minimized audit metadata field set;
  and
- read/write restart compatibility with a database created by the entry-baseline implementation.

### Preserved audit residual

The route still commits the descriptor before the separate audit write. An injected audit failure
therefore returns a server failure while the descriptor remains committed. The focused parity test
records this deliberately preserved behavior. It is evidence of compatibility, not a claim that
cross-store atomicity has been solved. Changing that ordering requires a separate transaction and
audit trust-boundary decision.

## Focused Evidence

`tests/test_sandbox_descriptor_repository.py` proves the protocol against the SQLite adapter,
including persisted canonical bytes and hashes, exact authority derivation, limit/order behavior,
exact missing-record behavior, schema/index invariance, and entry-baseline database restart.

Focused API coverage proves:

- authentication and response parity;
- exact audit event type and minimized metadata keys;
- redaction exclusions; and
- `audit_failure_ordering_parity`, including the retained descriptor after the injected audit
  failure.

The implementation check also verifies dependency and lock hashes, the 24-tool lock, the exact
SQLite table/index shape produced by initialization, consumer protocol typing, docs/release wiring,
and the continued validity of the parent entry decision. Its candidate scope is bound to the exact
`934ebaa..HEAD` Git inventory, rejects renames and copies, and requires a clean tree for release
evidence. Protocol, consumer, adapter, and focused-test claims are derived from parsed source and
runtime type inspection rather than success constants or comment-sensitive substring checks.

Generated evidence proves only the tested candidate behavior. It does not prove PostgreSQL
portability, cross-store atomicity, production identity, enterprise RBAC, backup/restore, retention,
remote administration, release readiness, production promotion, or UAT acceptance.

## Invariance And Rollback

`pyproject.toml`, `uv.lock`, and `tool-manifests.lock.json` remain byte-identical to the entry
baseline. No schema, migration, stored representation, public API, audit ordering, or governed tool
changed.

Rollback remains `revert_interface_and_adapter_commit_without_schema_or_data_conversion`. Reverting
the protocol, consumer annotations, and parity tests restores direct concrete-store typing. Existing
SQLite rows require no conversion, reverse migration, dual-write drain, or repair command.

## Stop Line And Next Gate

This implementation does not authorize SQLAlchemy, another dependency, a second aggregate,
PostgreSQL, migrations, production identity, enterprise RBAC, remote administration, a new governed
tool or power class, release, promotion, or UAT acceptance.

The next required action is `review_pis_002_sd_001_exact_candidate`. Independent review must bind to
one clean implementation commit, verify the changed-path boundary and required parity evidence, and
record all findings. PIS-003 and any second PIS-002 aggregate remain blocked even if this candidate
is cleared.
