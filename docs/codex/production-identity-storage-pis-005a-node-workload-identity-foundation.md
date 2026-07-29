# PIS-005A Local Node Workload Identity Foundation

Status: bounded implementation authorized and in progress.

Decision ID: `PIS-005A`.

Source commit: `e8e6a75ca3d76a233243f5e890091f3c95731da9`.

Security prerequisite: `83db1196213b0e4e7de5d97ab0fb37b934ca4ab7`.

Branch: `codex/enterprise-e2-pis005a-node-identity`.

Current governed tool count: exactly `24`.

The machine-readable authority is
[`production-identity-storage-pis-005a-entry-and-implementation-contract.json`](production-identity-storage-pis-005a-entry-and-implementation-contract.json).
Validate the bounded lane from the repository root:

```sh
make production-identity-storage-pis-005a-check
```

## Entry decision

PIS-005A is the first, deliberately non-serving part of the architecture's `PIS-005` work package.
It authorizes local SQLite foundation code and synthetic fixture conformance for `E2-NODE-001`
through `E2-NODE-004`. It does not authorize `E2-NODE-005`, a TLS listener, live mTLS, certificate
issuance, CA or Node private-key custody, remote transport, runtime PostgreSQL, or production
identity.

The PIS-003 external-input wait remains unchanged. PIS-005A does not select or connect to a
PostgreSQL target, consume credentials or a DSN, inspect external infrastructure, or fabricate
receipts. Its exact standing action remains
`await_external_operator_target_and_signed_receipt_inputs_before_separate_collection_action_authority`.
The reviewed PIS-004A identity/session foundation remains default-off. The E1 contract still
records `human_uat_complete: false`; release acceptance and production promotion remain false.

## Security prerequisite and compatibility

Before this entry decision, PIS-005A-000 repaired a high-severity public-key identity ambiguity:
strict Base64 decoding alone accepts noncanonical Ed25519 pad-bit aliases. Node identity and
configuration-trust ingress, transitions, public verification, persisted recovery state, and Node
client state now require decode/re-encode equality and compare raw key material for same-key
rotation. An independent read-only review found no open Critical, High, Medium, or Low finding.

Existing canonical key IDs remain byte-for-byte compatible. PIS-005A does not redefine them:

- canonical public key:
  `AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8=`;
- legacy canonical-text key ID:
  `sha256:c13217bb5694185919fa9b0bb7d18759c8dd4006aa0de169d29e9480d38f7bcd`;
- new explicitly versioned raw-key fingerprint:
  `sha256:630dcd2966c4336691125448bbb25b4ff412a49c732db2c8abc1b8581bd710dd`;
- fingerprint scheme: `ed25519_raw_sha256_v1`.

There is no global key-ID migration. The new raw fingerprint is a separate cross-binding field.

## Authorized foundation

The bounded implementation may add:

- server-generated deployment, Node, principal, and enrollment-transaction identifiers;
- one-use enrollment secrets returned to the caller once and stored only as generation-indexed
  keyed HMAC digests;
- a synthetic, injected, dedicated Node-CA trust anchor and an exact Ed25519 client-certificate
  profile with `clientAuth`, leaf-only basic constraints, digital-signature key usage, bounded
  validity, and exact Node/organization/workspace/deployment/enrollment SAN bindings;
- proof by both the certificate private key and a distinct application private key over one
  canonical enrollment binding, without Manager custody of either private key;
- atomic creation of a Node principal, organization/workspace memberships, certificate binding,
  application-key binding, and independent identity/certificate/application/configuration
  generations;
- revocation that increments generations, disables the principal and memberships, and requires
  replacement with a new Node ID and both new keys rather than restoration; and
- a non-serving request verifier that re-resolves every current binding, validates the application
  signature and presented certificate, consumes a durable nonce atomically, and returns only a
  snapshot carrying `effect_authority: false`.

The implementation module must remain unreferenced by application routes and startup. No endpoint,
cookie, browser import, MCP surface, general HTTP client, TLS socket, executor, or governed tool is
added.

The exact leaf profile has an empty subject and only four extensions: critical
`basicConstraints`, critical `keyUsage`, non-critical `extendedKeyUsage`, and critical
`subjectAltName`. Unknown extensions, non-URI general names, duplicate or additional SANs,
`serverAuth`, CA leaves, non-digital-signature key use, noncanonical DER, wrong trust anchors,
not-yet-valid or expired leaves, and validity beyond 86,400 seconds fail closed. The certificate's
inner and outer signature `AlgorithmIdentifier` values and its subject-public-key algorithm must
all be exact parameter-absent Ed25519 encodings; parser-differential inner/outer OID mismatches fail
closed even when the outer signature verifies. The five URI SANs are treated as an exact
order-independent set.

Enrollment secrets are generated directly with the standard-library cryptographic RNG at 256 bits,
have a maximum one-hour lifetime, and are returned once. Fixture certificate DER is capped at
65,536 bytes. Request envelopes are capped at 1 MiB, use a 300-second trusted-clock window, retain
one-use nonce digests for 600 seconds, and bind the computed body digest plus every current
deployment/identity/certificate/application/configuration generation. These bounds describe the
local conformance seam only and are not transport or supported-scale claims.

Security time is sampled only after the SQLite `BEGIN IMMEDIATE` write lock is acquired, so lock
wait cannot preserve a pre-expiry enrollment, request timestamp, or certificate-validity result.
An expired replacement enrollment is atomically terminalized before retry. A partial unique index
permits only one pending replacement for a revoked Node while retaining expired history; concurrent
replacement issuance therefore has exactly one winner.

Safe evidence is emitted only through closed server-owned reason codes and an exact disjoint field
inventory. Rendered Pydantic validation errors suppress input values, but raw `errors()` and
`json()` structures are explicitly forbidden as evidence because Pydantic retains the rejected
input there. The only evidence-safe validation projection is the module's fixed summary containing
an error count, server-owned reason code, and timestamp; malformed enrollment secrets, signatures,
certificate bytes, nonces, and request bodies never enter that summary.

## Persistence and rollback

PIS-005A moves the coordinated local SQLite schema to version `7` and minimum writer `7`. It adds
only exact `node_workload_*` objects. Existing `nodes`, `node_nonces`, and other local-preview
tables are not silently promoted into enterprise identity authority.

Migration from schema 6 takes a private verified pre-v7 backup before the atomic schema change.
The migration verifies exact table and index SQL, columns, constraints, unexpected prefixed
objects, and foreign keys. Older writers fail closed on schema 7.

The historical Attempt 008 reconciliation projection recognizes schema 7 only when both the
PIS-004A and PIS-005A fingerprints verify exactly and all six `node_workload_*` tables are empty.
Its original target schema, parent commit/tree, one-shot budget, and candidate-identity checks are
unchanged, so this compatibility read does not authorize a rerun or widen that historical
operation.

Rollback is restore-only:

1. keep the feature unimported/default-off;
2. stop the schema-7 writer;
3. restore the verified pre-v7 SQLite backup; and
4. revert the candidate code.

There is no automated down migration or destructive table drop. A schema-6 backup cannot be used
as a current writer after schema-7 state has been created; restoring it explicitly discards all
post-migration fixture-only workload identity state.

## Required negative and concurrency evidence

The focused gate must cover noncanonical application keys, identical certificate/application keys,
wrong or unavailable digest-key generations, expired/revoked/replayed enrollment, trust-anchor and
certificate-profile drift, inner/outer certificate algorithm mismatch, wrong proof of possession,
cloned keys, scope/generation mismatch, signature and request-digest mismatch, timestamp and nonce
replay, concurrent enrollment and request replay, lock-boundary expiry, revocation races,
replacement expiry/retry and concurrent issuance, replace-not-restore behavior, exact migration
DDL/constraint drift, interruption/backup/old-writer behavior, authority-anchor and review-lifecycle
mutation, exact evidence vocabulary, validation-error redaction, and database/evidence canaries.

After focused and broader checks pass, a separate reviewer should reproduce the exact pushed
candidate in a clean detached worktree:

```sh
git fetch origin refs/heads/codex/enterprise-e2-pis005a-node-identity:refs/remotes/origin/codex/enterprise-e2-pis005a-node-identity
git worktree add --detach /tmp/ithildin-pis005a-review <candidate_commit>
cd /tmp/ithildin-pis005a-review
make production-identity-storage-pis-005a-check
```

The pushed review candidate records `candidate_independent_review_pending` without trying to embed
its own commit hash. The descendant review-record commit binds that exact candidate commit and
tree, proves it is an ancestor, and is restricted to the contract, review record, status document,
and no executable registration path. This avoids circular self-hashing while preventing any
post-review implementation change from being hidden in the review-record commit.

Automated checks and synthetic fixtures are evidence only. They do not establish live transport,
private-key custody, production identity, human UAT, release acceptance, or production promotion.

## Explicit nonclaims

PIS-005A is not a live TLS listener, live mTLS, certificate issuance or CA private-key custody,
Node private-key custody or non-exportability, remote Node transport, production identity, remote
administration, multi-tenant hosting, runtime PostgreSQL, enterprise RBAC, effect execution,
supported scale or performance certification, human UAT completion, release acceptance, or
production promotion.

## Explicit next stop

After an exact candidate is independently reviewed, PIS-005A stops. The separate
[`E2-NODE-005 next-ticket contract`](production-identity-storage-pis-005a-remote-transport-next-ticket.md)
must be explicitly authorized before any TLS listener, mTLS integration, CA signing operation,
remote namespace, production custody provider, rotation overlap, or remote deployment work.
