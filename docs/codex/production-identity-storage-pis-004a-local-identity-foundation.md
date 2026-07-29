# PIS-004A Local Identity, Session, And Authorization Foundation

Status: candidate implemented; independent review required.

Decision ID: `PIS-004A`.

Source commit: `e86f5a19e4e067d73141246f78304597e6cc28a0`.

Branch: `codex/enterprise-e2-pis004a-local-identity`.

Current governed tool count: exactly `24`.

The machine-readable entry and implementation contract is
[`production-identity-storage-pis-004a-entry-and-implementation-contract.json`](production-identity-storage-pis-004a-entry-and-implementation-contract.json).
Validate this bounded lane from the repository root:

```sh
make production-identity-storage-pis-004a-check
```

## Entry decision and reconciliation

This record is the separate `PIS-004` entry decision requested by the Enterprise E2 preparation
lane, narrowed to `PIS-004A`. It authorizes working, local-only foundation code for `E2-ID-001`
through `E2-ID-004`. It does not rewrite or reinterpret the earlier preparation record.

PIS-004A reuses, without modifying, the standing architecture in:

- [`production-identity-storage-architecture.md`](production-identity-storage-architecture.md);
- [`production-identity-storage-pis-001-threat-model-and-dependency-decision.md`](production-identity-storage-pis-001-threat-model-and-dependency-decision.md); and
- [`enterprise-e2-production-identity-preparation.md`](enterprise-e2-production-identity-preparation.md).

Their exact SHA-256 digests are pinned by the JSON contract. The existing `PIS-003` route remains
`await_external_operator_target_and_signed_receipt_inputs_before_separate_collection_action_authority`.
This lane does not select an operator target, inspect credentials, load a PostgreSQL driver, consume
a DSN or binding key, connect, migrate an external database, start a service, or fabricate a
receipt. A local-only identity foundation can proceed independently without routing around that
wait.

## Authorized foundation

The bounded implementation may add:

- an exact `(organization_id, provider_configuration_id, exact_issuer, subject)` identity mapping
  with random Ithildin principal IDs;
- server-owned organization and workspace memberships, roles, identity generations, and membership
  generations;
- opaque high-entropy sessions whose client handle is never stored, with keyed lookup digests,
  non-authenticating audit IDs, idle/absolute expiry, rotation, family revocation, and generation
  invalidation;
- atomic one-use preauthentication transactions, allowed-origin validation, and session-bound CSRF;
- authorization snapshots derived only from current server state and bound to principal,
  organization, workspace, identity and membership generations, session, authentication method,
  recent-auth state, and policy generation;
- explicit human-versus-Node/service approval, separation-of-duty, self-approval, listing, and bulk
  scope rules;
- a synthetic, zero-network OIDC fixture seam with exact issuer/redirect, state, nonce, PKCE,
  asymmetric algorithm, key, audience, time, skew, replay, and malformed-input denial; and
- an additive local SQLite schema migration plus the exact dependency delta approved below.

There is no sign-in route, cookie route, remote administration endpoint, live provider
configuration, general-purpose HTTP client, or production identity mode in this authorization.
Any later API integration must be additive, disabled by default, and local-preview/loopback only.
The current local bearer-admin behavior remains the compatibility baseline.

The candidate adds no API route, browser import, cookie, feature-enabled configuration, effect
consumer, or governed tool. Identity/session/authorization modules remain unreferenced by the
existing application service, and authorization snapshots explicitly carry
`effect_authority: false`. Schema-5 activation creates only local authority tables and does not
enable a sign-in path. Existing API and local bearer-admin behavior remain the runtime default.

## Authlib dependency and provenance gate

The fresh 2026-07-29 gate approves Authlib only as a fixture adapter dependency:

| Package | Exact version | License | Reviewed role |
| --- | --- | --- | --- |
| Authlib | `1.7.2` | BSD-3-Clause | bounded OAuth/OIDC and PKCE primitives; no client integration |
| JOSERFC | `1.7.4` | BSD-3-Clause | Authlib's maintained JOSE primitive for fixed local fixtures |

The existing `cryptography` floor satisfies both packages. The expected new lock graph is exactly
those two packages. The contract pins the reviewed wheel and source-distribution hashes and the
source tags. An exact-version vulnerability screen observed no advisories at the time of review;
that is point-in-time screening, not a security or production claim.

The dependency may not own sessions, identity mappings, memberships, roles, or authorization. It
may not perform discovery, JWK retrieval, authorization redirects, callback HTTP, dynamic
registration, token persistence, or any other network activity. There is no hand-rolled fallback:
dependency removal disables the fixture adapter.

The implemented seam retains the Authorization Code with PKCE profile selected by PIS-001; it does
not switch to an OIDC hybrid or implicit flow. Captured discovery and public-JWK bytes become
immutable adapter configuration. The synthetic callback code is bound by a configured,
domain-separated digest, and the captured authorization-request challenge is checked against the
protected server-side verifier. Code and ID-token replay digests are committed atomically while the
organization/provider configuration is rechecked under the same SQLite writer transaction. Only
the public fixture JWK and pre-signed synthetic tokens are stored in the repository; the ephemeral
fixture private key was discarded.

The adapter has no route, HTTP transport, high-level Authlib client, framework session, or runtime
consumer. Its assertion has no effect authority. A future live Authorization Code exchange must
perform its own separately authorized token-endpoint and code/verifier validation; this fixture
seam is not evidence that such an exchange exists.

## Persistence, migration, and rollback

SQLite remains the only runtime backend. PIS-004A may move the coordinated local schema from
version `4` to `5`, create a private pre-v5 backup before upgrading an existing version-4 database,
and set minimum writer `5` after activation. Migration is atomic and verified against exact table
and index definitions. Older writers must fail closed.

The read-only Attempt-008 Node identity projector retains its exact schema-4 profile and adds a
separate schema-5 compatibility profile. Schema 5 is bound to the domain-separated fingerprint
`sha256:39c49742d0bb0aec44cc238f4d122028a2bdcc9bd5c20d4c67b250c52c119bdd`.
The profile compares complete normalized table and index DDL against a freshly generated expected
schema, rejects unexpected `identity_*` objects and foreign-key failures, and rechecks metadata
after installing its read-only authorizer. Same-column removal of primary-key, foreign-key,
unique, not-null, or check constraints therefore fails closed. The projector cannot read the new
identity tables and grants no revocation, cleanup, execution, UAT, or release authority.

Rollback is restore-only:

1. keep or return the feature to disabled;
2. stop the schema-5 writer;
3. restore the verified pre-v5 SQLite backup; and
4. revert `pyproject.toml` and `uv.lock` exactly if the fixture adapter is removed.

There is no automated down migration and no destructive table drop. Restoring the pre-v5 backup
discards only post-migration local PIS-004A state; that data-loss boundary requires an explicit
operator decision. No external system or production data is in scope.

The schema structurally omits OIDC authorization codes, access tokens, ID tokens, refresh tokens,
raw claims, and raw session handles. Audit output is limited to random local references, coarse
reason codes, generations, and timestamps. It must not contain raw subjects, claims, customer
names, credentials, handles, CSRF values, or tokens.

## Test and candidate procedure

The focused gate owns the exact negative inventory in the JSON contract. It must cover authority
spoofing, exact-issuer and redirect confusion, subject remapping, session/audit-ID confusion,
expiry, rotation/replay, family revocation, generation drift, preauthentication replay,
origin/CSRF failure, missing key generations, cross-scope access, non-human approval, self-approval,
listing/bulk isolation, OIDC algorithm/key/claim/time/replay failures, malformed input, attempted
network use, and sensitive audit fields.

After focused and broader checks pass, a separate reviewer should reproduce the candidate from a
clean detached worktree:

```sh
git fetch origin refs/heads/codex/enterprise-e2-pis004a-local-identity:refs/remotes/origin/codex/enterprise-e2-pis004a-local-identity
git worktree add --detach /tmp/ithildin-pis004a-review <candidate_commit>
cd /tmp/ithildin-pis004a-review
make production-identity-storage-pis-004a-check
```

The gate accepts the exact authorized implementation branch or a clean detached `HEAD` that equals
the freshly fetched authorized remote branch tip. A different detached commit, any dirty detached
state, and every other named branch fail closed.

A clean candidate and passing automated checks are not independent review, human UAT, release
acceptance, or production promotion. The next action is
`reproduce_exact_candidate_in_clean_detached_worktree_then_record_independent_review_before_any_e2_id_005_entry`.

## E2-ID-005 stop line

The authoritative E1 contract still records `human_uat_complete: false`. PIS-004A therefore does
not implement Command Center sign-in, revocation, break-glass, or other identity UI. A bounded
[E2-ID-005 next-ticket and acceptance contract](production-identity-storage-pis-004a-e2-id-005-next-ticket.md)
records the blocked future boundary and will consume eventual E1 findings. It may not treat a
future human PASS as production identity, release, or credential authority.

## Explicit nonclaims

PIS-004A is not live IdP integration, production identity, enterprise RBAC, remote administration,
multi-tenant hosting, runtime PostgreSQL, production credential or signing-key custody, supported
scale, performance certification, human UAT completion, release acceptance, or
enterprise-production readiness.
