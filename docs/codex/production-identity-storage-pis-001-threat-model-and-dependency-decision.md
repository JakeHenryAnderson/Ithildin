# Production Identity And Storage PIS-001 Threat Model And Dependency Decision

Status: `PIS-001` planning artifact recorded; `PIS-002` entry decision required.

Decision ID: `PRD-PROD-IAM-STORAGE-PIS-001`.

Parent decision: `PRD-PROD-IAM-STORAGE-ARCH-001`.

Decision outcome: `threat_model_frozen_dependency_recommendations_recorded`.

Current governed tool count: `24`.

Current selected runtime capability: `not selected`.

Current `ERG-006` status: `planning_only`.

Current `ERG-007` status: `planning_only`.

`PIS-001` is a planning artifact only. It freezes the Phase 1 security contract and records
dependency recommendations for later entry decisions. It does not add or authorize a dependency,
public API, schema, migration, OIDC integration, production identity, enterprise RBAC, remote
administration, runtime PostgreSQL, backup/restore behavior, retention enforcement, runtime code,
new governed tool, release, production promotion, or UAT acceptance.

## Decision Basis And Integrity Snapshot

- Planning baseline commit: `aa4b296f7b096b6ad0129bdf442a91c45d3d876f`.
- Architecture decision: `PRD-PROD-IAM-STORAGE-ARCH-001` with status
  `approved_for_pis_001_planning_only`.
- Reviewed architecture commit: `88f8e53cc54e599df25da6b14d465a5fb06848d7`.
- Reviewed architecture packet digest:
  `sha256:bdcac6f8cbb1c5a3cec40730eccdf2cb6a3a2d1f9c0ab2a588e3f1afaf378c57`.
- `pyproject.toml` planning-baseline SHA-256:
  `d7f72600511d9a3fbb1777b388dafc58d7ffc5886d0e5d40a95cbd4debc2063d`.
- `uv.lock` planning-baseline SHA-256:
  `431403895950d714cf060923e5e98c77ffb6f927e696ba86e4ac99d005fca2c5`.
- `tool-manifests.lock.json` planning-baseline SHA-256:
  `3834a18a5b8169dd66b3d96d79d6e69d252ebae17a1a9453f93f8686db1edc77`.

Those hashes are a stop line, not a permanent dependency pin. A later dependency or tool change
must have its own committed entry decision and update this record rather than silently making this
planning artifact pass.

External maintenance and licensing facts were checked on 2026-07-20 against primary project
sources. They are not a future version pin. The later dependency gate must repeat vulnerability,
license, provenance, release-line, signature/hash, and transitive-dependency review against the
exact candidate bytes.

## Phase 1 Security Objective

The smallest defensible candidate remains one self-hosted Ithildin Manager deployment for one
organization, multiple human operators, multiple workspaces, and remotely connected Ithildin
Nodes. The security objective is:

> Only a currently authenticated, server-mapped principal or Node identity may exercise authority
> that the Manager derived from its current organization, workspace, policy, configuration,
> identity, session, and deployment epochs; every accepted authoritative mutation must commit its
> domain state, audit binding, and export-outbox record atomically or remain denied/recovery-only.

The Manager is the governance authority. The IdP authenticates a human subject but does not assign
Ithildin authority. A Node authenticates its transport and signs its application request but does
not choose its organization, workspace, roles, policy, or configuration generation. PostgreSQL is
a future canonical state candidate but never becomes a second policy authority. Gateway truth,
Node connectivity, runner-reported state, and model-provider state remain separate.

## Security Invariants

1. Configured issuer, verified discovery issuer, authorization-response issuer where present, and
   token `iss` match exactly. Equivalent-looking issuer strings are denied, not canonicalized into
   authority.
2. The immutable human identity key is `(organization_id, provider_configuration_id,
   exact_issuer, subject)`; email, username, display name, group claims, and raw directory
   attributes never link accounts or grant authority.
3. Principal IDs, organization/workspace scope, roles, membership generation, identity generation,
   policy generation, and authorization decisions are server-owned. Caller-supplied values cannot
   create or override them.
4. Human and Node/service memberships are distinct. A service or agent role cannot satisfy a human
   approval or recent-authentication requirement.
5. Browser sessions use a random opaque handle. Only a keyed lookup digest is stored; the separate
   random `session_audit_id` cannot authenticate or retrieve a session.
6. OIDC access, ID, authorization-code, and refresh tokens are not persisted. Raw claims are not
   retained as evidence.
7. State-changing browser requests require allowed-origin validation plus a session-bound,
   single-purpose CSRF value. CORS alone is not a CSRF control.
8. SQLite remains the only supported runtime backend today. A configured PostgreSQL value must not
   imply that production storage is available.
9. Future PostgreSQL transport requires TLS with server identity verification equivalent to
   `sslmode=verify-full`; default or downgrade-capable TLS posture is rejected.
10. Runtime and migration database identities are distinct, least-privilege, externally managed,
    and absent from evidence. Migration authority is unavailable to the Manager runtime.
11. Domain mutation, authoritative audit event, and export-outbox row commit in one transaction.
    An audit or outbox failure rolls back the domain mutation.
12. Security-sensitive compare-and-set transitions use `SERIALIZABLE` isolation or an explicitly
    proven lock protocol. Transparent retry never surrounds an external effect.
13. Migration is offline and verify-before-activate. There is no dual write and no conversion of
    local labels, sessions, or approvals into production authority.
14. One deployment epoch holds write authority. Lease loss, ambiguous fencing, unreachable prior
    primary, or competing-primary evidence fences writes and Node authority.
15. Restore starts isolated. Promotion requires database integrity, audit, identity/revocation,
    key-epoch, configuration, and external-watermark reconciliation.
16. Node private identity is replaced, not restored. Manager database backup data cannot recreate
    a Node private key.
17. Evidence is secret-free and privacy-safe. It contains random/local references and safe status
    labels, not raw external subjects, customer labels, credentials, tokens, connection strings,
    prompts, response bodies, or private paths.

The closed machine-readable companion contract is
`docs/codex/production-identity-storage-pis-001-decision.json`. It is authoritative for threat-family IDs,
dependency dispositions, accepted-risk state, and all allow/deny booleans. Prose may add rationale
but may not contradict or grant authority absent from that closed contract.

## Assets And Data Classes

| Asset | Data class | Authority or confidentiality requirement |
| --- | --- | --- |
| External identity mapping | restricted identity | Immutable exact-issuer/subject binding; raw subject is never exported. |
| Principal and membership generations | authoritative control state | Server-owned, organization/workspace scoped, revocation-aware. |
| Session handle and lookup digest | secret authentication material | Handle exists only at browser; digest is keyed and never evidence. |
| Session audit reference | restricted evidence metadata | Random, non-authenticating, retention-labelled, unlinkable without Manager state. |
| Approval and recent-authentication state | authoritative control state | Human principal and generation bound; service roles cannot satisfy it. |
| Policy and configuration generations | authoritative control state | Exact digest and signing epoch bound; stale generations denied. |
| Node certificate and application key bindings | restricted workload identity | Both identities resolve to the same active Node and deployment generation. |
| Node private keys | secret authentication material | Generated and retained at Node; never backed up by Manager. |
| Canonical database rows | authoritative operational state | Transactional, constrained, deployment-scoped, encrypted in transit. |
| Audit sequence and chain head | authoritative evidence state | Serialized per deployment epoch and committed with domain mutation. |
| Export outbox | authoritative delivery state | Atomic with mutation; retryable delivery cannot rewrite history. |
| Signed evidence export | derived restricted evidence | Verifiable but never consulted for live authorization. |
| Database backup and WAL | restricted recovery material | Encrypted, complete, key-separated, restored only in isolation. |
| External recovery watermark | external authority anchor | Conditional-write, signed, monotonic, unavailable to database-only rollback. |
| Signing, CA, digest, and backup keys | secret trust roots | External custody decision; key IDs/epochs only may be stored. |

## Actors And Assumptions

| Actor | Permitted role | Explicitly untrusted or constrained behavior |
| --- | --- | --- |
| Human operator | Uses bounded workspace capabilities | Browser and supplied identity/role/scope fields are untrusted. |
| Organization admin | Manages server-owned mappings and memberships | Cannot bypass recent auth, separation rules, audit, or recovery fencing. |
| Ordinary principal | Performs authorized work | Cannot infer or enumerate another workspace or organization. |
| Disabled or stale principal | None | Existing cookie, token, role, or cached membership must fail closed. |
| Node/service principal | Uses its exact signed workload contract | Cannot satisfy human approval, select roles, or become runner/provider truth. |
| Database runtime role | Executes reviewed runtime statements | Cannot migrate schema, manage roles, read external custody, or bypass application constraints. |
| Database migration role | Executes one attributed migration plan | Unavailable to runtime; cannot activate an unverified deployment epoch. |
| Backup operator | Produces and restores encrypted recovery material | Cannot promote a restore or recreate Node/signing identity alone. |
| Enterprise IdP | Authenticates a configured exact issuer and subject | Claims do not directly create Ithildin membership or roles. |
| External custody/watermark service | Holds selected key/anchor authority | Provider remains unselected; outage must fail closed for dependent operations. |
| Local attacker | May read process-adjacent files or steal browser state | Must not gain raw tokens, database credentials, keys, or cross-workspace authority. |
| Network attacker | May observe, redirect, replay, partition, or terminate traffic | TLS/issuer/request bindings and idempotency must prevent downgrade and replay. |
| Compromised dependency | Executes in Manager process if installed | Dependency footprint is minimized; inputs and outputs remain independently constrained and tested. |
| Stale/restored Manager | May have internally consistent old state | Has no write/Node authority until external epochs and watermark reconcile. |

## Trust Boundaries And Entry Points

| Boundary or entry point | Untrusted input | Required validation and failure posture |
| --- | --- | --- |
| Browser to Manager sign-in start | return target, cookie state | Allowlisted relative return target, fresh state/nonce/PKCE, secure cookie; deny malformed state. |
| IdP discovery and authorization callback | discovery JSON, issuer, code, state, nonce, ID token/JWK | Exact issuer/redirect URI equality, HTTPS, outbound destination allowlist, size/time limits, response-issuer and mix-up defense, algorithm/key/claim validation, one-use state/code; deny ambiguity. |
| Manager session store | opaque cookie handle, CSRF value, clock | Keyed lookup, expiry, generation/revocation, allowed origin, constant-time comparison; deny key/time uncertainty. |
| API authorization | path/body/query plus any claimed principal/scope | Resolve identity and memberships server-side; ignore or reject caller authority fields. |
| Manager to PostgreSQL | SQL parameters, connection settings, result rows | Parameter binding, `verify-full`, role separation, pool isolation, explicit transactions; deny ambiguous outcome. |
| Manager to Node ingress | certificate, application signature, nonce, request metadata | Certificate/key/Node/config/deployment cross-binding and replay protection; deny mismatch or stale generation. |
| Database to backup/WAL | backup stream, WAL segments, receipts | Complete encrypted archive, separated key custody, integrity and restore-point verification; never auto-promote. |
| Manager to KMS/CA/watermark | key IDs, signing requests, conditional-write generations | Explicit provider adapter, authenticated response, generation compare-and-set; ambiguous result remains pending/fenced. |
| Migration/import boundary | SQLite export, canonical transfer records, schema metadata | Versioned duplicate-rejecting schema, empty isolated target, full inventory/digest verification; discard failed import. |
| Export to external verifier | evidence metadata and signed bundle | Redaction, data-class allowlist, sequence/head/digest/key-epoch binding; export is never authorization input. |
| Operator recovery action | restore selection, fence/promote decision | Recent attributed human authority, external anchor, isolated state, explicit state machine; no implicit retry. |

## Authority Transitions

Every transition below is a server-owned state machine, not a convenience endpoint:

- OIDC callback -> mapped principal authentication generation;
- authenticated principal -> opaque Manager session;
- membership/policy generation -> request authorization decision;
- one-time Node enrollment -> certificate and application-key binding;
- key/certificate rotation -> new active workload-identity generation;
- governed request -> approval reservation -> effect -> terminal result;
- domain mutation -> audit sequence reservation -> export-outbox record -> atomic commit;
- migration import -> verified isolated epoch -> externally fenced activation;
- backup restore -> isolated reconciliation -> conditional watermark -> explicit promotion; and
- key or authority loss -> fence/revoke -> replace or attributed recovery.

No transition may accept caller-supplied terminal status, resurrect an earlier generation, or infer
success from connectivity alone.

## Abuse-Case And Control Matrix

| Abuse case | Preventive/containment rule | Required negative or interruption proof |
| --- | --- | --- |
| Exact-issuer confusion and response mix-up | Compare configured, discovery, authorization-response, and token issuers byte-for-byte; bind state to provider configuration and redirect URI; reject aliases and normalization. | Slash, case, Unicode, punycode, userinfo, DNS alias, wrong callback host, forwarded-host confusion, and mixed discovery/response/token issuer. |
| Subject remap/account linking | Immutable provider/exact-issuer/subject key; attributes never link accounts. | Reused email/name, subject change, provider-config change, disabled mapping. |
| Caller-role or scope spoofing | Reject/ignore authority fields and load server-owned generations. | Body/header/query role, organization, workspace, principal, and generation injection. |
| Membership drift | Bind session to identity and membership generations; revoke on change. | Removed role with live cookie, concurrent membership update, stale cache. |
| Session fixation/theft/replay | Rotate after auth/authority change; opaque high-entropy handle; bounded expiry and revocation. | Pre-auth fixation, copied cookie, retired digest key, idle/absolute expiry, concurrent rotation. |
| CSRF/login CSRF | State/nonce/PKCE plus origin and session-bound CSRF on mutations. | Missing/wrong/replayed state, cross-origin POST, stale CSRF after rotation. |
| Cross-workspace/organization access | Deployment and workspace predicates in every repository operation and uniqueness constraint. | Known object ID from another workspace, missing scope predicate, bulk/list enumeration. |
| Disabled-principal reuse | Disable increments identity generation and revokes sessions. | Existing session, callback race, cached membership, queued approval after disable. |
| Node key cloning | mTLS plus Ed25519 key cross-binding; replace-not-restore; generation revocation. | Same application key on two certificates/Nodes, restored old key, overlapping rotation misuse. |
| Stale configuration or policy | Exact generation/digest binding and minimum version gate. | Replay older signed bundle, downgrade after restart, conflicting Manager generation. |
| Replay/idempotency collision | Durable, scope-bound idempotency key and nonce state. | Same key with different payload/scope, response loss, restart replay, expired nonce. |
| Split brain | One deployment epoch with external fence/watermark; lease ambiguity disables authority. | Network partition, old primary return, concurrent promotion, unreachable prior primary. |
| Ambiguous transaction result | No success claim; reconcile by durable request/idempotency evidence. | Commit acknowledgement loss, connection drop before/after commit, serialization failure. |
| Partial/incorrect migration | Offline empty-target import; canonical digests and inventories; no dual write. | Duplicate keys, partial rows, unknown schema, interrupted import, old writer after activation. |
| Audit-head race/truncation | Locked epoch head and atomic domain/audit/outbox commit. | Concurrent writers, failed audit insert, missing sequence, modified prior head, outbox failure. |
| Outbox loss or duplicate delivery | Outbox row commits atomically; delivery is idempotent and history-preserving. | Crash before/after delivery mark, duplicate send, backlog pressure, corrupt export. |
| Stale restore/watermark rollback | Isolated restore and external monotonic reconciliation before promotion. | Backup predating revocation, missing watermark, wrong key epoch, rollback of anchor generation. |
| Backup/WAL theft | Encryption and key separation; no credentials or Node keys in evidence. | Wrong decryption identity, stolen media, incomplete WAL, tampered restore point. |
| Dependency compromise | Minimal direct set, exact lock/SBOM, provenance review, input/output constraints, rapid disable path. | Malformed discovery/JWK/SQL, dependency error/timeout, compromised-version denylist and rollback drill. |
| Sensitive evidence leakage | Explicit evidence schema and denylist with redaction before persistence/export. | Tokens, subjects, customer labels, DSNs, SQL parameters, paths, prompts, and response-body canaries. |

OIDC discovery and JWK retrieval are controlled outbound requests, not generic HTTP fetches. The
future adapter must derive destinations only from the separately configured exact HTTPS issuer,
reject redirects or resolved destinations outside the provider contract, enforce response size and
time limits, and never accept discovery metadata as a new authority root. ID-token verification
must use a fixed asymmetric algorithm allowlist; select a known key by `kid`; reject missing,
duplicate, incompatible, or ambiguous keys; validate `iss`, `sub`, `aud`, `azp` when multiple
audiences exist, `exp`, `iat`, `nbf` when present, and the session-bound nonce; and handle JWK
rollover through a bounded refresh without accepting an unknown key indefinitely. Callback URL and
secure-cookie decisions use explicitly trusted deployment configuration, never an unvalidated
`Host`, `Forwarded`, or `X-Forwarded-*` value.

## Threat Evidence, Recovery, And Residual Ownership

Safe evidence is deliberately narrower than debug output. Every implementation ticket must name
its event schema and prove that denial/recovery evidence contains only random local references,
coarse reason codes, generations, digests, and timestamps allowed by the data-class policy.

| Threat family | Minimum safe evidence | Recovery or fencing action | Residual risk owner |
| --- | --- | --- | --- |
| OIDC issuer, discovery, JWK, callback, or subject confusion | provider-configuration reference, safe denial code, key ID digest, authentication generation | disable provider configuration, revoke affected sessions, rotate client credentials if exposed, re-establish exact metadata/key trust | Ithildin identity maintainer; deployment operator for provider configuration |
| Session fixation, theft, replay, CSRF, or membership drift | random session audit reference, safe denial code, identity/membership/digest-key generations | revoke session family, rotate digest key when implicated, increment identity/membership generation, require fresh authentication | Ithildin identity maintainer; organization admin for membership correction |
| Cross-organization/workspace or caller-authority spoofing | random request reference, resolved organization/workspace references, safe denial code, policy generation | deny and quarantine affected request, revoke compromised principal, repair server-owned mapping, inspect adjacent scope predicates | Ithildin authorization maintainer; organization admin for principal disposition |
| Node key clone, stale configuration, or replay | Node/deployment references, certificate and application-key IDs, configuration generation, nonce outcome | revoke affected generation, fence Node, perform replace-not-restore enrollment, reissue configuration | Ithildin Node maintainer; deployment operator for endpoint recovery |
| Split brain, stale restore, or watermark rollback | deployment epoch, external watermark generation/digest, safe fence reason, isolated-restore reference | fence all ambiguous writers and Node authority, reconcile external anchor, promote exactly one epoch through attributed recovery | Ithildin storage maintainer; deployment recovery operator |
| Ambiguous transaction, audit-head race, or outbox failure | request/idempotency reference, deployment epoch, transaction outcome label, audit/outbox sequence references | keep result pending or recovery-required, reconcile durable records, never replay as fresh work, repair only through an attributed runbook | Ithildin storage/audit maintainer |
| Partial migration, backup/WAL failure, or database role misuse | migration/restore reference, schema version, inventory/digest mismatch, role class, safe failure code | discard isolated target or keep restore fenced, rotate credentials if implicated, repeat from verified source after root-cause closure | Ithildin storage maintainer; deployment database/backup operator |
| Dependency compromise or sensitive-evidence leakage | dependency/version/hash reference or canary class, affected feature, safe incident reference | disable feature or revert to last reviewed lock, revoke exposed material, quarantine exports, run scoped incident review | Ithildin maintainer; deployment security owner for external incident handling |

## Required Fail-Closed Behavior

| Unavailable or uncertain dependency | Required behavior |
| --- | --- |
| IdP/discovery/JWK endpoint | Deny new sign-in; do not accept stale issuer metadata beyond an explicitly reviewed bounded cache policy. |
| Session-digest key | Deny creation and validation for that key generation; retirement invalidates bound sessions. |
| Trustworthy time | Deny freshness-dependent authentication, recent-auth checks, key rotation, and authority transitions. |
| PostgreSQL or transaction outcome | Deny new governed mutation; expose only safe unavailable or reconciliation-required status. |
| KMS/CA/signing service | Deny dependent certificate, configuration, manifest, checkpoint, and export-signing operations. |
| External watermark/fence | Keep restore isolated or transition pending; deny write and Node authority. |
| Audit head or outbox | Roll back domain mutation or retain terminal recovery-required state; never report success. |
| Backup/WAL completeness | Refuse restore promotion and preserve incident evidence. |
| Dependency integrity/provenance | Refuse startup or the affected disabled feature; do not fall back to an unreviewed implementation. |

## Current Dependency Inventory

The runtime currently has direct dependencies on `cryptography`, FastAPI/Starlette through FastAPI,
MCP, OpenTelemetry, Pydantic, PyYAML, and Uvicorn. HTTPX and PyJWT are currently present through
development or transitive dependency paths; they are not an Ithildin-owned production OIDC
contract. SQLite, `secrets`, `hmac`, `hashlib`, and `ssl` are Python standard-library facilities.

Current code is intentionally SQLite-specific: repositories open `sqlite3` connections directly,
several transitions use `BEGIN IMMEDIATE`, audit correlation can depend on `rowid`, and schema
creation lives beside runtime stores. A future PostgreSQL lane therefore cannot be a driver string
swap.

### Existing components retained

- **`cryptography`** — accepted existing dependency for current Ed25519 and serialization behavior.
  It processes keys and signatures. Any future X.509 or CA use needs a separate design and negative
  parser tests; PIS-001 does not extend its role.
- **FastAPI/Starlette request primitives** — accepted existing HTTP framework surface. Starlette's
  signed-cookie `SessionMiddleware` is explicitly rejected as the production authentication
  session or pre-authentication transaction store because Phase 1 requires opaque handles with only
  keyed server-side lookup digests.
- **Python `secrets`, `hmac`, and `hashlib`** — accepted for random session/CSRF values, keyed
  session-handle lookup digests, and constant-time comparisons. Password hashing is unnecessary
  because Phase 1 does not add passwords and session handles have high entropy.
- **Python `sqlite3`** — retained as the only supported runtime backend through PIS-002 unless a
  later decision says otherwise. Its current semantics are the compatibility baseline, not the
  production storage implementation.

## Candidate Dependency Decisions

### Authlib client integration — recommended, deferred to a PIS-004 dependency gate

- **Capability:** standards-aware OIDC Authorization Code with PKCE, discovery, state/nonce, token
  parsing, and FastAPI/Starlette/HTTPX client integration. The standard library and current direct
  dependency set do not provide a complete OIDC relying-party implementation.
- **Layer:** identity-provider adapter only; it must not own Ithildin sessions, principal mapping,
  memberships, roles, or authorization.
- **Sensitive processing:** authorization code, client authentication, ID token, JWKs, discovery
  metadata, and untrusted network input. Tokens must remain ephemeral.
- **Maintenance/license:** the official project showed active 2026 releases, a documented security
  reporting channel, Python 3.10+ support, and BSD-3-Clause licensing at the planning snapshot.
  Authlib also documents migration away from its older `authlib.jose` module; a later gate must
  review the exact client/Jose dependency split rather than assuming today’s import paths.
- **Footprint/interoperability:** adds one security-sensitive direct dependency and uses HTTPX;
  supports OAuth/OIDC and Starlette/FastAPI client integration. Dynamic client registration and
  provider-specific social-login helpers remain disabled/non-goals.
- **Unsafe configuration classes:** automatic issuer normalization, permissive algorithm selection,
  unchecked discovery/JWK redirects, unbounded metadata, persistent token dictionaries, trusting
  `userinfo` or group claims as authority, and using framework session middleware as the auth store.
- **Testability:** deterministic adapter around captured metadata/JWK fixtures, exact issuer
  comparisons outside the library, clock injection, replay fixtures, network timeout/size limits,
  and provider-conformance tests.
- **Operational burden:** security monitoring, version review, IdP interoperability matrix, JWK
  rotation handling, emergency provider disable, and incident rotation of client credentials.
- **Decision:** `recommended_deferred`; do not add before a separate PIS-004 entry/dependency
  decision and source review.

Authlib integration may use protocol/client primitives only. A future sign-in start must create an
Ithildin-owned, server-side pre-authentication transaction containing the state, nonce, PKCE
verifier, provider-configuration reference, exact redirect URI, issuance/expiry, requested
freshness, and one-use status. The browser receives only a random opaque `__Host-` transaction
handle marked `Secure`, `HttpOnly`, and `SameSite`; it never receives the transaction contents in a
signed client cookie. Callback consumption is atomic and replay-denying. Default Authlib/Starlette
`SessionMiddleware`, persistent ID/access/refresh tokens, and retaining an ID token merely for RP
logout are forbidden. Phase 1 logout is local Manager-session revocation unless a later reviewed
design proves non-persistent RP-initiated logout.

Recent authentication is a separate authority property, not the time a Manager session happened to
be created. A recent-auth-required transition must start a newly bound OIDC ceremony with an exact
`max_age` requirement and validate a trustworthy ID-token `auth_time` against injected time and the
requested bound. A provider that omits, contradicts, or cannot honor that freshness proof cannot
satisfy recent authentication; silent SSO success alone is insufficient.

### Hand-rolled OIDC using transitive PyJWT plus HTTPX — rejected

- **Capability/layer:** would manually implement discovery, authorization redirect/callback, PKCE,
  state/nonce, JWK retrieval, ID-token verification, issuer/audience/time checks, and errors.
- **Sensitive processing:** all OIDC credentials, tokens, keys, and attacker-controlled metadata.
- **Maintenance/license/footprint:** PyJWT is MIT-licensed and actively released at the snapshot,
  but is present transitively through MCP, not as an Ithildin direct contract. HTTPX is not an OIDC
  protocol implementation. A nominally smaller dependency list would create a larger Ithildin-owned
  security implementation and accidental coupling to another package's dependency graph.
- **Testability/operations:** every protocol edge and provider divergence would become Ithildin's
  maintenance and incident burden.
- **Decision:** `rejected`; PyJWT may be evaluated as an explicit JOSE component only if a later
  Authlib/Jose review requires it, never because it happens to be installed transitively.

### SQLAlchemy 2.0 Core — recommended, deferred to the PIS-002 entry decision

- **Capability:** backend-neutral SQL construction, explicit connection/transaction boundaries,
  typed result handling, SQLite/PostgreSQL dialect behavior, and schema metadata. The standard
  library has no PostgreSQL driver or cross-backend SQL abstraction.
- **Layer:** repository/transaction infrastructure using **Core only**; ORM identity maps, implicit
  unit-of-work behavior, lazy loading, and model-driven authority are out of scope.
- **Sensitive processing:** SQL, bound parameters, identifiers, transaction state, and database
  results; it must never log credentials or sensitive values.
- **Maintenance/license:** the official project identified the 2.0 line as current and MIT-licensed
  at the snapshot; 2.1 was beta and is not a candidate line for a first implementation gate.
- **Footprint/interoperability:** adds SQLAlchemy and its declared transitive requirements; supports
  SQLite and PostgreSQL dialects. It does not eliminate the need for explicit PostgreSQL locks,
  isolation, constraints, or migration review.
- **Unsafe configuration classes:** implicit autocommit assumptions, unscoped pooled connections,
  string-built SQL, ORM autoflush/lazy behavior, dialect-conditional authority gaps, and logging
  bound secrets.
- **Testability:** run identical repository contracts against SQLite and an isolated PostgreSQL test
  service later; assert emitted constraints, transaction boundaries, concurrency, cancellation,
  and failure behavior.
- **Operational burden:** new abstraction and upgrade surface, pool lifecycle, SQL logging/redaction,
  dialect review, and pinned current-series upgrades.
- **Decision:** `recommended_deferred`. The PIS-002 entry decision must choose between first adding
  interfaces over existing `sqlite3` or introducing SQLAlchemy Core behind a disabled adapter. No
  dependency change is approved here.

### Psycopg 3 — recommended, deferred to a PIS-003 dependency gate

- **Capability:** PostgreSQL DB-API/async access, parameter binding, COPY support, typed interfaces,
  and optional connection pooling. Neither `sqlite3` nor the current dependency set can connect to
  PostgreSQL.
- **Layer:** SQLAlchemy PostgreSQL dialect driver and narrowly owned migration/import utilities;
  application repositories should not depend directly on driver-specific objects.
- **Sensitive processing:** DSNs, database credentials, TLS settings, SQL, parameters, and result
  rows.
- **Maintenance/license:** the official project identifies Psycopg 3 as the current generation,
  supports modern Python/PostgreSQL releases, and uses LGPL-3.0-only licensing. Legal/redistribution
  review is required before adoption.
- **Footprint/interoperability:** the pure Python package uses system `libpq`; the local C build also
  links system `libpq`/`libssl`; and the binary extra bundles native components. Each choice changes
  performance, build, patch, redistribution, and SBOM ownership. Package flavor is deliberately
  unselected until PIS-003 evaluates the actual deployment and performance requirements; the binary
  extra remains disallowed until that packaging review.
- **Unsafe configuration classes:** default TLS posture, DSNs containing credentials, shared pools
  across deployments, runtime use of migration credentials, driver-level transparent retries, and
  unbounded prepared-statement/pool behavior.
- **Testability:** real PostgreSQL integration tests for `verify-full`, role denial, pool isolation,
  serialization, cancellation, ambiguous commit, connection loss, and credential rotation.
- **Operational burden:** PostgreSQL and `libpq` support matrix, native package patching, connection
  pool sizing, credential rotation, server certificate roots, incident revocation, and license/SBOM
  tracking.
- **Decision:** `recommended_deferred`; version, package flavor, extras, native build, and system
  library ownership remain unselected until PIS-003.

### Alembic — recommended, deferred to a PIS-003 dependency gate

- **Capability:** versioned, reviewable upgrade/downgrade scripts, offline SQL generation,
  transactional PostgreSQL DDL, and explicit SQLite batch behavior. Hand-written ad hoc schema
  initialization cannot safely carry the future compatibility and rollback contract alone.
- **Layer:** offline/operator migration package using the migration database role. It is never
  imported by ordinary request handling to perform startup migration.
- **Sensitive processing:** schema metadata, DDL, optional data migration SQL, database URL, and
  migration-role credentials.
- **Maintenance/license:** Alembic is part of the SQLAlchemy project, actively maintained, and
  MIT-licensed at the snapshot.
- **Footprint/interoperability:** adds Alembic plus SQLAlchemy and template dependencies. It supports
  offline SQL and PostgreSQL transactional DDL but does not supply a deployment-wide advisory lock
  or safe data-migration semantics automatically.
- **Unsafe configuration classes:** unreviewed autogenerate output, automatic startup upgrade,
  branch/merge heads, destructive downgrade, credentials in configuration, concurrent migrators,
  and assuming every DDL/data operation is transactionally reversible.
- **Testability:** single linear head, checked-in generated SQL, empty/previous/current schema
  upgrade, downgrade boundary, interrupted migration, advisory lock, older-writer denial, and
  backup/restore preflight.
- **Operational burden:** migration review ceremony, compatibility matrix, signed artifact binding,
  DBA/offline execution support, irreversible-boundary declaration, and recovery rehearsal.
- **Decision:** `recommended_deferred`; autogenerate may create a draft only and never constitutes an
  approved migration.

### Psycopg pool, asyncpg, ORM usage, and retry frameworks

- `psycopg_pool`: `deferred`; pool semantics and process model require load/concurrency evidence.
- `asyncpg`: `rejected_for_phase_1`; it duplicates the selected driver role and increases parity
  burden without a demonstrated requirement.
- SQLAlchemy ORM: `rejected_for_authority_state`; Core and explicit repositories keep transaction,
  scope, and locking behavior visible.
- General retry libraries around database/effects: `rejected`; retries must be explicit,
  idempotency-bound, and prohibited around ambiguous external effects.
- Each candidate processes SQL or transaction state except the retry library, whose danger is
  control-flow opacity. Their licenses and exact dependency trees must still be rechecked if a
  later decision reopens them.

### Provider SDKs and infrastructure products — deferred and unselected

OIDC providers, PostgreSQL distributions/managed services, KMS/HSM/CA providers, backup systems,
external watermark stores, immutable evidence stores, and legal-hold systems remain unselected.
Provider SDKs would process credentials, keys, network responses, and custody operations; choosing
one now would improperly decide deployment topology and external authority. A future decision must
cover maintenance, license, provenance, tenant isolation, outage/partition semantics, conditional
writes, key exportability, auditability, rollback, and incident exit strategy.

PostgreSQL itself remains the sole production database candidate, not an approved deployment. Its
official versioning policy provides five years of major-version support, and official libpq
documentation recommends `verify-full` for security-sensitive environments. The future deployment
decision must choose an exact supported major/minor line and patch policy; PIS-001 does not.

## Exact Identity And Storage Contract Freeze

PIS-001 accepts the seventeen security invariants above without weakening the reviewed architecture.
The only clarification is dependency placement:

```text
IdP protocol adapter (future)       Authlib client surface, separately gated
Ithildin session/authorization      Ithildin-owned server state and rules
Repository/transaction boundary     explicit Ithildin interfaces
SQL construction/dialects (future)  SQLAlchemy 2.0 Core candidate
PostgreSQL driver (future)           Psycopg 3 candidate
Migration runner (future)            Alembic offline/operator surface candidate
Custody/watermark providers          unselected external adapters
```

Libraries may implement protocol or storage mechanics; they may not decide exact issuer equality,
principal mapping, organization/workspace authority, role generation, approval separation,
evidence redaction, restore promotion, or deployment fencing.

## Negative, Interruption, Restart, And Partition Plan

A later implementation may advance only if its ticket maps every changed boundary to deterministic
tests and, where needed, real service evidence:

1. **Identity fixtures:** issuer-confusion matrix, state/nonce/PKCE replay, algorithm/key confusion,
   JWK rotation, callback duplication, disabled/remapped subject, attribute collision, unavailable
   IdP, and untrustworthy clock.
2. **Session fixtures:** fixation, copied cookie, CSRF origin/token failures, expiry boundaries,
   membership and digest-key rotation, restart, concurrent revocation, and audit-reference misuse.
3. **Authorization fixtures:** caller-supplied identity/role/scope/generation, cross-workspace object
   IDs, service-role-as-human approval, self-approval policy, and stale policy/configuration.
4. **Repository parity:** every aggregate against SQLite before a second backend; no changed public
   behavior, transaction outcome, audit lifecycle, ordering contract, or failure label.
5. **PostgreSQL integration:** TLS downgrade and hostname mismatch, runtime/migration role denial,
   pool isolation, constraints, row locks, serialization failure, deadlock, connection loss before
   and after commit, and process restart.
6. **Migration:** empty target, duplicate/conflicting IDs, interrupted export/import, unknown schema,
   row/digest mismatch, audit-head mismatch, old writer after activation, downgrade boundary, and
   absence of synthesized production authority.
7. **Audit/outbox:** concurrent writers, head race, audit failure, outbox failure, response loss,
   duplicate delivery, backlog, signed checkpoint, and redaction canaries.
8. **Node identity:** certificate/application-key mismatch, cloned key, rotation overlap, retired key
   replay, Manager restart, partition, stale configuration, and replace-not-restore recovery.
9. **Backup/restore:** stolen/tampered/incomplete backup, wrong decryption authority, WAL gap, stale
   revocation, missing watermark, wrong key epoch, competing primary, crash before/after anchor, and
   explicit fence/promotion evidence.
10. **Dependency failure:** malformed/unbounded network input, timeout/cancellation, unavailable
    library/native component, compromised-version denylist, rollback to last reviewed lock, and
    secret-free error handling.

## Rollback And Recovery Rules

- A planning or dependency-gate failure changes no runtime state; revert the candidate commit and
  retain this no-runtime baseline.
- PIS-002 must preserve SQLite behavior and provide a per-aggregate rollback path before any
  PostgreSQL package or schema is introduced.
- A failed isolated PostgreSQL import is discarded, never repaired into authority.
- Application rollback without database restore is allowed only while the earlier writer is
  explicitly compatible with the active schema.
- After authority-bearing schema activation, incompatible rollback is restore-only through isolated
  reconciliation and external fencing.
- Ambiguous external effects and anchor writes are reconciled by their existing reservation and
  idempotency records, never retried as fresh work.
- Dependency rollback uses an exact previously reviewed lock and artifact; emergency removal must
  disable the affected future feature rather than fall back to hand-rolled protocol behavior.

## Unresolved External Decisions And Accepted-Risk Impact

No new accepted risk is created by this planning artifact because it changes no runtime behavior.
The current local-preview identity, SQLite, exportable Node-key, and local evidence limitations
remain accurately bounded and must not be described as production controls.

PIS-001 revisits but does not close the following registered risks:

| Risk | PIS-001 effect | Required later closure evidence | Owner |
| --- | --- | --- | --- |
| `AR-001` local host trusted computing base | unchanged `accepted_deferred`; no sandbox, EDR/MDM, host-compromise, or production-security claim | separately approved deployment/action-path boundary and evidence showing what a compromised host can and cannot bypass | Ithildin maintainer |
| `AR-002` local principal labels | unchanged `accepted_deferred`; the exact OIDC mapping and server-owned authorization contract define a future closure path only | implemented and independently reviewed identity/session/authorization slice with provider and negative-test evidence | Ithildin maintainer |
| `AR-003` local tamper-evident audit | unchanged `accepted_deferred`; atomic audit/outbox and external watermark are future requirements, not current custody | implemented external anchoring/custody, recovery, retention, and independent verification evidence | Ithildin maintainer |
| `AR-009` SQLite-only runtime storage | unchanged `accepted_deferred`; repository parity and PostgreSQL are future gated work | real PostgreSQL parity, migration, interruption, restart, backup/restore, and rollback evidence | Ithildin maintainer |
| `AR-010` best-effort redaction | unchanged `accepted_deferred`; evidence minimization is mandatory and redaction remains secondary | schema-level data minimization, canary tests, packet/export scanning, incident path, and independent leak review | Ithildin maintainer |

No accepted-deferred risk may be relabeled closed merely because its design requirement or test plan
appears here. Each closure requires the implemented boundary, exact-candidate evidence, and its own
review/authority record.

The following remain external or later decisions:

- supported IdP/provider matrix, client authentication method, and client-credential custody;
- PostgreSQL distribution/managed service, supported major version, topology, and patch SLA;
- runtime and migration credential provider, KMS/HSM/CA, certificate profile, and key ceremonies;
- external watermark/conditional-write implementation and deployment-fencing operator;
- RPO, RTO, backup frequency, region/geography, retention periods, legal hold, privacy deletion,
  crypto-shredding, and immutable storage;
- deployment ingress/TLS termination and service-manager topology; and
- enterprise-preview pilot data, operator ownership, support, and incident-response commitments.

If one of those choices becomes necessary to write PIS-002, stop and record the separate decision;
do not use a convenient local default as production architecture.

## PIS-002 Entry Decision

`PIS-002` remains `no_go_pending_separate_entry_decision`.

The next allowed artifact is a **PIS-002 entry decision record**, not implementation. It may decide
whether to introduce backend-neutral repository/transaction interfaces over existing `sqlite3`
with behavior unchanged and which aggregate is first. It may also decide whether SQLAlchemy Core is
introduced in PIS-002 or deferred to PIS-003. It must not authorize PostgreSQL startup, a PostgreSQL
schema, migration execution, production OIDC, remote admin, or a new governed power.

Before a PIS-002 go decision, the entry record must:

1. name one first aggregate and its current SQLite transaction/audit behavior;
2. define exact parity and rollback evidence;
3. decide the SQLAlchemy Core timing and repeat exact dependency/license/provenance review if it is
   proposed for installation;
4. show that `pyproject.toml`, `uv.lock`, public APIs, schemas, migrations, policies, and the 24-tool
   surface remain unchanged unless the entry decision explicitly gates one necessary change;
5. preserve every PIS-001 invariant and stop on critical/high findings; and
6. obtain a separate committed authorization before implementation begins.

## Explicit Non-Goals And Claims

This artifact does not approve or claim production IAM, enterprise RBAC, tenant/team authorization,
remote administration, runtime PostgreSQL, database migrations, backup/restore runtime behavior,
retention enforcement, Node private-key backup, multi-tenant hosting, hosted telemetry, remote MCP,
sandbox orchestration, SIEM delivery, compliance automation, custody-grade evidence, regulatory
compliance, EDR/MDM behavior, public security-product positioning, production readiness, release,
enterprise-preview acceptance, or UAT acceptance.

## Primary Sources Checked

- [Authlib project and security/licensing information](https://github.com/authlib/authlib)
- [Authlib Starlette/OIDC client documentation](https://docs.authlib.org/en/latest/client/starlette.html)
- [Psycopg 3 project documentation](https://www.psycopg.org/psycopg3/docs/)
- [SQLAlchemy release and license status](https://www.sqlalchemy.org/download.html)
- [Alembic project documentation](https://alembic.sqlalchemy.org/en/latest/)
- [PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/)
- [PostgreSQL libpq TLS verification guidance](https://www.postgresql.org/docs/current/libpq-ssl.html)

## Validation And Next Gate

Run the focused PIS-001 gate:

```sh
make production-identity-storage-pis-001-decision-check
make production-identity-storage-pis-001-planning-gate-check
make production-identity-storage-architecture-decision-record-check
make production-identity-storage-architecture-check
make no-new-powers-guardrail
make tool-surface-invariant-gate
```

PIS-001 is evidence-complete only after focused checks, independent read-only security review, the
applicable clean exact-candidate release checkpoint, and packet redaction scan pass. Passing those
checks permits preparation of the separate PIS-002 entry decision only; it does not authorize
PIS-002 implementation or any runtime/dependency change.
