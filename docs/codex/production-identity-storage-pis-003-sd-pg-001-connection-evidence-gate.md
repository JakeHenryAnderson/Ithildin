# Production Identity And Storage PIS-003 SD-PG-001 Connection Evidence Gate

Status: committed connection-evidence-gate candidate pending exact-candidate source review; no
connection implementation or execution authority is active.

Gate ID: `PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-CONNECTION-EVIDENCE-GATE`.

Parent review: `PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-OFFLINE-IMPLEMENTATION-REVIEW`.

Reviewed offline candidate: `ba60478ede66abce519e134981fcabcb3f68482f`.

Gate baseline commit: `bf26418b5f27b1fcd08552758e4387867b5eafe0`.

Evidence slice: `PIS-003-SD-PG-001-CONNECTION-EVIDENCE`.

Gate outcome: `select_bounded_connection_evidence_candidate_pending_gate_review`.

Current governed tool count: `24`.

Validate this candidate with:

```sh
make production-identity-storage-pis-003-sd-pg-001-connection-evidence-gate-check
```

The closed companion contract is
`docs/codex/production-identity-storage-pis-003-sd-pg-001-connection-evidence-gate.json`. Its exact
path boundary, evidence schema, environment prerequisites, authority map, and next action are
authoritative. Prose cannot broaden the closed contract.

The gate candidate itself changes exactly eleven paths: the Makefile and README wiring, this closed
document and contract, the decision register and review index, docs/release registration, the gate
validator, and focused release-readiness tests. The validator computes the baseline-to-worktree
tracked plus untracked inventory and requires exact equality with that closed list. An unrelated
path makes the gate invalid.

## Purpose And Phase Boundary

The reviewed offline candidate proves deterministic PostgreSQL DDL, strict source validation, and
an importer that accepts only a caller-owned SQLAlchemy `Connection`. It does not prove the
Psycopg/system-`libpq` path, TLS posture, an online migration, a real transaction, or target
discard. This gate selects the smallest test-only implementation that can later produce that
evidence without changing Ithildin runtime behavior.

This candidate is a gate, not the harness. A clean exact-candidate gate review may authorize the
bounded harness, environment-receipt generator, frozen synthetic SQLite snapshot reader, and
caller-owned Alembic online path to be implemented. It does not authorize those paths to execute.
The implemented harness must receive a second exact-candidate source review, and a separate
environment-specific execution preflight must validate every required receipt before the first
driver load or database connection.

No single green validator flips both implementation and execution authority. Generated receipts
and test results are evidence only; they do not authorize runtime PostgreSQL, production identity,
release, promotion, or UAT.

## Current Environment Observation

The preparation host is macOS `26.5.2` on `arm64`, with repository Python `3.12.13`, `uv 0.11.12`,
and the exact non-default `pis3` lock already reviewed. A Docker CLI is present, but `pg_config`,
`psql`, `postgres`, and `initdb` are absent. No system-`libpq` source/version/patch receipt, target,
DSN, PostgreSQL service, or database connection is present or claimed.

The system TLS root source is `/etc/ssl/cert.pem`; its existence is observational only. A future
environment receipt must bind the exact certificate-source digest used by the driver. The gate
does not authorize Docker, Podman, Colima, Homebrew, a package installer, a PostgreSQL service, or a
container lifecycle. An agent- or operator-supplied isolated target remains external to the
Ithildin runtime and must be governed by the execution preflight.

## Closed Implementation Boundary

After a zero-finding exact gate review, the connection-evidence implementation may change only the
closed contract's `implementation_allowed_paths`. It may:

- replace the always-refusing test harness contract with a dedicated test-only harness module;
- change Alembic online mode only to accept a caller-owned SQLAlchemy `Connection` through
  `config.attributes`, never a URL or engine factory;
- read one synthetic frozen SQLite source snapshot in immutable read-only mode and verify its digest
  before and after the run;
- create a synchronous SQLAlchemy engine with `NullPool` only inside the harness;
- define environment, rollback, connection-attempt, semantic-import, transaction-rollback,
  negative-failure, and target-discard receipt schemas;
- accept the primary test DSN only from `ITHILDIN_PIS3_TEST_DSN`, never from a command-line argument,
  file, repository configuration, generated packet, log, or receipt;
- emit only secret-free structured evidence beneath the ignored connection-evidence run root; and
- add focused tests, implementation evidence, validation, documentation, and gate wiring.

The current importer and schema are protected exact artifacts. The implementation may call them
but may not alter them. API startup, configuration, current SQLite storage, descriptor behavior,
audit ordering, public routes, Node, Mission Control, deployment, policy, manifests, and the
24-tool surface remain protected.

## Environment-Specific Execution Preflight

Even after a clean implementation review, the harness must refuse before importing Psycopg,
reading a DSN, constructing an engine, or opening a socket unless an execution manifest and all
referenced receipts validate as one closed set. The set must bind:

- the exact reviewed harness commit and artifact hashes;
- a safe non-secret target label and a dedicated nonproduction/quarantined purpose statement;
- a preconnection rollback receipt bound to that candidate and target label;
- the target owner and named discard owner;
- the exact Python, SQLAlchemy, Alembic, Psycopg, system `libpq`, and OpenSSL versions;
- the `libpq` and native TLS-backend distribution sources, package receipts, patch provenance,
  architectures, loaded-library paths, and digests;
- `PSYCOPG_IMPL=python` and rejection of `psycopg-c`, `psycopg-binary`, and `psycopg-pool`;
- the TLS-root source path and SHA-256 digest without certificate private material;
- a dependency SBOM and license receipt matching the reviewed Python lock and the native `libpq`
  and TLS dependency closure;
- the synthetic immutable SQLite source digest and expected record digest;
- DSN posture assertions for TLS verification, without persisting the DSN, user, password, host,
  database name, query parameters, or arbitrary driver text;
- a secret-scan marker set provided only for in-memory/output checking; and
- an empty-target/quarantine attestation whose freshness window is no more than fifteen minutes.

The environment receipt is exact-candidate and exact-target evidence. Reusing it for a different
commit, driver, TLS root, target, or source snapshot is invalid. Current environment observations
in this planning gate are not a substitute for that receipt.

### DSN-to-target binding

After every signed prerequisite receipt validates but before importing Psycopg, the harness may read
the DSN and `ITHILDIN_PIS3_TARGET_BINDING_KEY` once into memory solely to validate target binding.
It must reject every ambient `libpq` connection variable, including host, port, database, user,
password, passfile, service, service-file, options, application-name, TLS, GSS/Kerberos, channel-
binding, timeout, target-session, load-balancing, peer, and system-configuration overrides.
The machine rule rejects every present environment key matching `^PG[A-Z0-9_]+$`, with an empty
allowlist, so a newer `libpq` variable cannot bypass a stale enumeration.

The DSN must be one explicit `postgresql+psycopg` URI with one host, one numeric port, one database
path segment, explicit user and password material, no fragment, and exactly four query keys:
`sslmode=verify-full`, `sslrootcert` equal to the approved TLS-root path,
`application_name=ithildin-pis3-evidence`, and `connect_timeout=5`. Multi-host forms, Unix sockets,
IPv6 zone identifiers, `service`, `passfile`, `options`, client key/certificate parameters,
GSS/Kerberos parameters, alternate TLS roots, unknown query keys, and implicit/default connection
fields are rejected before driver load.

The externally signed target-owner receipt contains an HMAC-SHA-256 commitment over the canonical
normalized target/TLS tuple, run ID, target label, and exact reviewed candidate. The harness
recomputes that commitment in memory using the externally held 32-byte binding key and the actual
DSN, compares it in constant time, then discards the key and normalized fields. Neither the key,
DSN, normalized fields, nor HMAC input may be written to evidence. A plain unkeyed DSN hash is not
accepted.

The version-1 HMAC payload is a closed object containing exactly schema version, run ID, target
label, reviewed candidate, scheme, lowercase ASCII DNS hostname, integer port, UTF-8 NFC database,
user and password, TLS mode, TLS-root real path and SHA-256, application name, and integer timeout.
The HMAC input is the ASCII domain `ITHILDIN-PIS3-DSN-BINDING-V1\n` followed by Ithildin canonical
JSON (`sort_keys=True`, separators `,` and `:`, `ensure_ascii=False`) encoded as UTF-8 with no BOM or
trailing newline. The output is `hmac-sha256:` plus 64 lowercase hex characters.

URI parsing is fail-closed: the raw URI is ASCII; user, password, database, and query values must be
strict UTF-8 NFC with one canonical uppercase percent-encoding; duplicate user-info delimiters,
duplicate query keys, empty keys or values, noncanonical escapes, slashes inside the decoded
database, IP literals, IDNA conversion, trailing-dot or non-lowercase hostnames, leading-zero or
out-of-range ports, and any alternate representation are rejected. This gives the external issuer
and harness one byte-identical HMAC payload definition.

For URI components, the only raw safe bytes are RFC 3986 unreserved ASCII
`A-Z a-z 0-9 - . _ ~`. Every other UTF-8 byte is encoded as `%HH` with uppercase hexadecimal;
percent-encoded unreserved bytes, lowercase escapes, raw reserved bytes, and raw non-ASCII bytes are
rejected. Userinfo contains exactly one literal `:` and one literal `@` delimiter. Query syntax uses
only literal `=` and `&`, with the four unique pairs in lexicographic order. These delimiter bytes
inside values must be percent-encoded.

The primary positive run permits exactly two connection attempts: the transaction/migration/import
attempt and the explicitly authorized post-rollback absence check. Each negative network scenario
uses its own exact signed manifest, run ID, target receipt, DSN, and one-attempt budget. A negative
target cannot be added to the positive manifest or share its connection budget.

### External receipt authenticity

Rollback, target-owner/quarantine, and final target-discard receipts must be canonical JSON signed
with Ed25519 by an external issuer. Each receipt binds the schema version, safe issuer ID, issuance
and expiration times, provenance, run ID, target label, exact reviewed candidate, source digest, and
receipt-specific assertion. The external verifier trust record binds the issuer, public key,
fingerprint, allowed receipt types, and validity window before the run.

Ed25519 private-key custody never enters Ithildin. The HMAC key is generated externally, then
disclosed ephemerally to the harness only for recomputation and constant-time comparison; it is not
verification material, is never persisted, and is discarded immediately afterward. The harness
cannot generate or substitute the trust record and cannot create, edit, or overwrite an external
receipt. Required receipts and the trust record must originate from read-only paths
outside both the repository and the harness output root. The final discard receipt must be issued
after the last connection closes; a separate evidence finalizer verifies it before the evidence set
can be complete.

The separately reviewed execution manifest binds the external trust-record SHA-256 and allowed
issuer public-key fingerprint. Each signed receipt has a closed type-specific assertion schema:
rollback binds the disposition and no-activation posture; target ownership binds dedicated
nonproduction purpose, quarantine, emptiness, the DSN-target HMAC commitment, attempt budget, and
discard owner; final discard binds the last-connection time, discard time, discarded state, and
proof that activation never occurred.

Every receipt is a two-key envelope, `payload` plus `signature`. The signed bytes are the ASCII
domain `ITHILDIN-PIS3-CONNECTION-RECEIPT-V1\n` followed by the exact Ithildin-canonical JSON payload
encoded as UTF-8 without a BOM or newline. The signature object contains only algorithm `Ed25519`,
the SHA-256 fingerprint key ID, and a base64url-no-padding 64-byte signature. The trust record
contains only issuer ID, base64url-no-padding 32-byte public key, SHA-256 fingerprint of those raw
32 bytes, unique allowed receipt types, and canonical UTC validity bounds. Trust-record issuer IDs
use the same closed safe-label pattern as receipt issuers, and both validity timestamps use the exact
second-precision `+00:00` pattern before their ordering and window relationships are checked.

Payload and assertion objects reject extra or duplicate keys and enforce exact JSON types. Receipt
parsing is strict UTF-8 without a BOM, rejects non-finite constants, distinguishes integers from
booleans, caps the canonical assertion at 4,096 bytes, and requires canonical round-trip equality.
Receipt provenance is a closed value for the matching external target owner or discard owner.
The signed `issuer_id` of the final `target_discard_receipt` must exactly equal the
`discard_owner_id` named by the earlier `target_owner_quarantine_receipt`; an otherwise trusted
issuer authorized for the receipt type cannot substitute for that named discard owner.
Receipt and discard times use second-precision `+00:00` text, are strictly ordered, stay within the
15-minute freshness and trust windows, and bind the exact run, target, candidate, and source digest.
Security
booleans are fixed truth values: rollback is prebound and source-preserving with activation false;
the target is dedicated, quarantined, and empty; and final discard is true with activation never
occurring. Attempt budgets are exact integers, digests/HMACs/fingerprints are prefixed 64-character
lowercase hex, and receipt type must match both its closed assertion schema and the issuer's allowed
types.

## Harness Transaction And Migration Contract

The test-only harness owns the engine, connection lifetime, explicit outer transaction, rollback,
and disposal. The importer continues to own none of them. The harness must:

1. validate the synthetic source snapshot and every non-secret manifest field before driver load;
2. read the DSN once from `ITHILDIN_PIS3_TEST_DSN` without persisting or rendering it;
3. require the plain synchronous Psycopg Python implementation and exact system-`libpq` receipt;
4. construct one SQLAlchemy engine using `NullPool`, with no retry wrapper or application pool;
5. open one connection and begin one explicit non-autocommit outer transaction;
6. pass only that connection to Alembic online mode and then to the reviewed importer;
7. prove one migration head, an initially empty application target, stable semantic import
   verification, and an uncommitted receipt;
8. roll the outer transaction back, never commit it;
9. reconnect only if separately authorized for rollback verification, then prove that no imported
   application row or activated target remains;
10. dispose the engine; and
11. require a separately supplied target-discard receipt before the evidence set can be complete.

Immediately after driver load and before migration execution, the harness must confirm that the
actually loaded `libpq` and native TLS library source, version, patch, architecture, real path, and
SHA-256 digest exactly match the signed preflight receipts. A mismatch stops before the first SQL
statement. The native SBOM/license evidence includes both libraries and their resolved native
dependency closure; the Python lock alone is insufficient.

The harness may not create or drop a database, create a role, grant privileges, manage a service or
container, run a downgrade, repair a target, reverse-import, dual-write, activate a backend, or
retry ambiguous work. Any connection loss after an uncertain commit boundary is
`ambiguous_commit`; the run stops for reconciliation and is never replayed as fresh work.

## Failure Evidence And Secret Safety

Negative evidence must prove at least TLS-verification failure, authentication/authorization
failure, unavailable target, nonempty target, migration failure, semantic mismatch, transaction
loss, and invalid/missing receipt rejection. External targets for deliberate negative connections
must be isolated and explicitly listed in the execution manifest.

The harness must map failures to a closed safe category and stage. It must not serialize `repr()` or
`str()` from SQLAlchemy, Psycopg, `libpq`, Alembic, or the database; raw exception chaining must be
suppressed at the evidence boundary. Evidence may contain only safe target labels, fixed categories,
boolean posture, exact package/certificate/artifact hashes, counts, descriptor IDs, canonical UTC
times, and Ithildin-owned digests. It may not contain a DSN, credential, hostname, address, database
name, role name, certificate subject, raw SQL parameters, payload JSON, environment dump, or
arbitrary server/driver message.

A final scan must search the complete output tree for the in-memory secret marker set and common
connection-string/credential forms. A scan pass is necessary but not sufficient evidence of safe
handling.

## Required Evidence And Completion

Connection evidence is not complete until the exact contract's ordered evidence list passes. The
minimum positive evidence includes gate and implementation reviews; environment/preconnection
receipts; immutable source identity; exact driver, `libpq`, TLS, SBOM, and license identity; one
caller-owned online migration; empty-target proof; semantic import/readback; outer-transaction
continuity; explicit rollback; post-rollback absence; secret-safe failures; target discard; clean
output scan; unchanged protected hashes; the 24-tool invariant; focused checks; and the applicable
full repository gates.

The run must label itself `isolated_nonproduction_connection_evidence_only`. It proves neither an
operational runtime backend nor production identity/storage readiness. The runtime continues to use
SQLite, and the descriptor-commit-then-audit-write residual remains deferred to PIS-006.

## Rollback And Target Disposal

Rollback remains `revert_exact_candidate_and_discard_isolated_target_before_activation`.

Before the first connection, the execution manifest must include the validated rollback receipt,
safe target label, exact reviewed candidate, source digest, and discard owner. The target remains
quarantined throughout the run. The transaction is rolled back, the synthetic SQLite source remains
unchanged, and the external owner must discard the isolated target. The target-discard receipt must
bind the same target label and run ID, be created after the last connection is closed, and state
that activation never occurred.

If the target cannot be proved discarded, any source hash changes, credentials appear in evidence,
the target is not dedicated and nonproduction, or authority-bearing data is discovered, the
evidence is invalid and work stops. There is no in-place repair, downgrade, reverse import, dual
write, runtime failback, or production-data handling in this slice.

## Closed Authority And Next Action

This gate candidate records:

- `pis_003_sd_pg_001_connection_evidence_gate_recorded: true`;
- `connection_evidence_candidate_selected: true`;
- `offline_candidate_review_prerequisite_satisfied: true`;
- `exact_candidate_source_review_required: true`;
- `exact_candidate_source_review_complete: false`;
- `connection_evidence_implementation_allowed: false`;
- `environment_receipt_implementation_allowed: false`;
- `test_harness_implementation_allowed: false`;
- `online_alembic_caller_connection_implementation_allowed: false`;
- `psycopg_plain_sync_use_allowed: false`;
- `external_dsn_consumption_allowed: false`;
- `isolated_test_connection_allowed: false`;
- `database_connections_allowed: false`;
- `migration_execution_allowed: false`;
- `postgres_service_allowed: false`;
- `runtime_behavior_changes_allowed: false`;
- `runtime_postgres_allowed: false`;
- `production_identity_allowed: false`;
- `enterprise_rbac_allowed: false`;
- `new_power_classes_allowed: false`;
- `release_allowed: false`;
- `production_promotion_allowed: false`;
- `uat_complete: false`; and
- `uat_required_now: false`.

The next required action is
`review_pis_003_sd_pg_001_connection_evidence_gate_exact_candidate`. A zero-finding review may
grant only the closed implementation ceiling. That ceiling permits implementation of the test-only
harness and evidence/preflight machinery; it keeps driver use, DSN consumption, connections,
migration execution, service lifecycle, runtime, production identity, release, promotion, and UAT
false. The implemented exact candidate must then be independently reviewed before an
environment-specific execution preflight may be prepared.

## Stop Lines

Stop for a changed path outside the closed implementation boundary; any mutation of the reviewed
importer/schema; default-enabled dependency; `psycopg-c`, `psycopg-binary`, `psycopg-pool`, async
driver, ORM/session, application pool, embedded DSN, raw driver error in evidence, repository or
product service/container lifecycle, database/role creation, runtime import, startup migration,
current SQLite or audit change, second aggregate, API behavior, production identity/RBAC, new tool
or power, public security claim, release/promotion claim, or UAT claim.

Also stop on a critical/high trust-boundary finding or the same authoritative gate failure three
times.

Passing the gate check proves only this exact planning artifact and false execution authority.
