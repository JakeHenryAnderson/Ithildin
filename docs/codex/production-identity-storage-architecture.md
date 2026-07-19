# Production Identity And Storage Architecture

Status: design-only architecture packet for `ERG-006` and `ERG-007`.

This document defines the future architecture questions Ithildin must answer before it can support
production identity, organization authorization, remote admin use, runtime Postgres, multi-user
concurrency, retention policy, backup/restore, or production custody claims. It does not add runtime
behavior, tool manifests, executors, policy rules, API endpoints, MCP transports, production IAM,
runtime Postgres, hosted telemetry, remote MCP, SIEM adapters, compliance automation, public
security-product positioning, or any new governed tool power.

Current governed tool count: `24`.

Current selected capability: `not selected`.

## Scope

This packet covers two enterprise-readiness gap rows:

- `ERG-006`: production identity and multi-user authorization.
- `ERG-007`: durable runtime storage and retention.

It is intentionally paired because production identity and durable storage depend on each other:
principal attribution, tenant/workspace membership, approval history, audit retention, backup,
restore, and incident reconstruction all need one coherent trust model.

## Current Boundary

The current v1.0 local-preview boundary remains:

- local principal labels, not enterprise authentication;
- local admin token and loopback admin surface, not production session management;
- SQLite runtime storage, not runtime Postgres;
- local tamper-evident audit evidence, not custody-grade retention;
- stdio/local MCP posture, not remote MCP hosting;
- single-operator local-preview workflow, not organization/team authorization.

## Phase 1 Self-Hosted Candidate

The smallest defensible enterprise candidate is a **single-organization, self-hosted Manager with
multiple human operators, multiple workspaces, and remotely connected Ithildin Nodes**. It is not a
multi-tenant hosted service. Every authoritative row still carries a deployment-scoped
`organization_id` so that a later multi-organization design cannot infer or retrofit a trust
boundary from display labels.

This is a review candidate, not an implementation decision. It makes the current architecture
questions concrete enough for threat-model and external architecture review while all runtime flags
remain false.

### Truth And Authority Split

```text
enterprise IdP -> authenticates a human subject
Ithildin Manager -> maps (organization_id, normalized issuer, subject) to a local principal and server-owned memberships
workspace membership -> grants bounded Ithildin roles; token claims do not directly grant roles
Ithildin Node CA -> authenticates the Node transport identity
Node Ed25519 key -> signs the existing application request contract
PostgreSQL -> canonical Manager state and serialized audit chain
signed export -> derived evidence artifact; never the live authorization source
external recovery watermark -> prevents a restored database from claiming stale authority
```

Gateway truth, Node connectivity, runner-reported state, and model-provider state remain separate.
Production identity must not turn runner or provider reports into Gateway decisions.

### Human Identity And Authorization

- Human sign-in uses OIDC Authorization Code with PKCE through an Ithildin backend-for-frontend.
  SAML, SCIM, password authentication, and direct browser custody of long-lived bearer tokens remain
  later decisions.
- The immutable external identity key is `(organization_id, normalized issuer, subject)`. Email,
  display name, username, groups, and arbitrary token claims are attributes only and must never be
  principal keys or account-linking keys.
- The Manager creates a random Ithildin principal ID and stores the external subject mapping.
  Disabled, unknown, remapped, or issuer-drifted subjects fail closed.
- Phase 1 requires pre-provisioned subject mappings. Just-in-time administrator or role creation is
  forbidden.
- Roles and workspace memberships are server-owned records. IdP groups may feed a separately
  reviewed reconciliation process, but a request-time group or role claim cannot directly create
  authority.
- Phase 1 reuses the current closed role vocabulary. Human and Node/service memberships are stored
  separately so an agent role cannot be presented as a human approval role.
- Every authorization decision binds principal ID, identity generation, organization, workspace,
  role-membership generation, authentication method, session ID, and policy generation. Caller
  fields cannot supply or override any of them.
- A production policy must decide whether self-approval is forbidden for each approval class. The
  default candidate is separation of requester and approver for trusted-host placement and other
  high-risk actions.

### Session, CSRF, Revocation, And Break Glass

- The browser receives only a random opaque session identifier in a `Secure`, `HttpOnly`,
  `SameSite=Lax`, `__Host-` cookie. PostgreSQL stores only a keyed digest of that handle. OIDC
  tokens are consumed during callback validation and are not persisted. Phase 1 retains only safe
  issuer, subject, authentication-time, authentication-method, and session metadata; it does not
  keep a long-lived refresh token to extend a browser session indefinitely.
- Sessions have absolute and idle expiry ceilings, rotate after authentication or authority change,
  and are revoked on principal disable, membership-generation change, IdP subject remap, or explicit
  administrator action.
- Every state-changing browser request requires an origin check and a session-bound CSRF token.
  CORS is an API exposure control, not a CSRF defense.
- Role changes, Node enrollment, key rotation, recovery promotion, break glass, and destructive or
  high-risk approvals require recent human authentication in addition to current authorization.
- Remote admin use requires TLS and production identity. The current local bearer token is never a
  remote production credential.
- Break glass is disabled by default, loopback-only, separately attributed, time-bounded, and cannot
  approve or execute governed work. It may only fence or isolate a deployment and orchestrate
  recovery. Any authoritative principal, membership, key-epoch, database, or recovery-state
  mutation must still use reserve-anchor-finalize and the canonical domain/audit/outbox transaction.
  An external receipt may anchor a recovery discontinuity; it cannot substitute for missing
  authoritative audit evidence. If that evidence cannot be preserved, governed mutations remain
  denied.

### Node Workload Identity And Transport

- Remote Node traffic uses a distinct ingress namespace and requires a reviewed TLS 1.3 profile
  with a Manager certificate and a Node client certificate issued by a dedicated Ithildin Node CA.
  Plain HTTP and trust-on-first-use remain local-preview only.
- mTLS is additive to, not a replacement for, the current Ed25519 application signatures. The
  certificate identity, Node ID, application signing key, configuration generation, and deployment
  organization must all resolve to the same active server record.
- Enrollment remains one-time and digest-only. The Node generates both private keys locally; the
  Manager binds the enrollment proof to the certificate request and application public key. A
  certificate or Ed25519 key is never copied from Manager backup data.
- Certificate and application-key rotation have distinct generations and overlap windows. Loss,
  revocation, or cross-generation mismatch denies new authority and routes the Node to explicit
  replacement or recovery.
- A production Node stores private keys in a non-exportable OS keystore or equivalent reviewed
  custody provider where the host supports it. An exportable mode-0600 file remains technical
  preview posture and cannot support a production workload-identity claim.
- Phase 1 makes no TPM, HSM-on-endpoint, device-attestation, non-bypass, EDR, or MDM claim.

### Canonical Storage And Transaction Model

- PostgreSQL is the only candidate production runtime backend. SQLite remains the supported
  local-preview backend; setting `postgres_dsn` does not enable production storage.
- A backend-neutral repository/transaction contract must replace direct `sqlite3` access one
  bounded aggregate at a time. This is not a mechanical driver substitution: existing
  `BEGIN IMMEDIATE`, `rowid`, placeholder, migration, and filesystem-mirror assumptions require
  explicit PostgreSQL equivalents.
- Authoritative mutation paths use database transactions with closed uniqueness constraints and
  row locks. Security-sensitive compare-and-set transitions use `SERIALIZABLE` isolation or an
  equivalently proven lock protocol.
- Domain mutation, the authoritative audit event, and an export-outbox record commit in the same
  PostgreSQL transaction. An audit insert failure rolls back the domain mutation. Export delivery
  happens after commit and may be retried without rewriting canonical history.
- Serialization failures may be retried only when the request has a durable idempotency key and no
  external side effect has occurred. Placement and other effects keep their reservation, evidence,
  and terminal-recovery protocols; the database adapter must not add transparent retries around
  effects.
- Phase 1 permits multiple Manager API processes within one active deployment epoch, all using one
  PostgreSQL primary and the same deployment-epoch lease/fence. A second active deployment epoch,
  active/active primaries, sharding, and cross-region multi-primary operation are later decisions.

### Audit And Evidence In A Multi-Process Runtime

- PostgreSQL is the canonical production audit store. Each deployment has an explicit monotonic
  audit sequence and hash-chain head updated in the same serialized transaction that reserves the
  event. No implementation may depend on PostgreSQL physical row order.
- One segment-head row per deployment epoch holds the next sequence and current hash. Every
  audit-producing transaction locks it `FOR UPDATE`, inserts the next event, and advances the head
  atomically. Phase 1 accepts this deliberate serialization in favor of ambiguous multiwriter
  ordering.
- The current exact SQLite/JSONL mirror remains a local-preview contract. In production, JSONL is a
  derived, signed, checkpoint-bound export generated from committed rows; it is not a second live
  database and is never consulted for authorization.
- A state transition is externally successful only after its audit binding is durable. If an
  external effect can precede audit completion, the transition remains terminal recovery-required
  with effect-possible evidence, matching the existing trusted-host and mission protocols.
- Periodic signed checkpoints bind deployment ID, organization ID, sequence range, head hash,
  schema version, export policy, and signing-key epoch. External notarization and custody-grade
  evidence remain separate decisions.
- A transaction outbox derives JSONL and other evidence bundles from committed rows. An export
  backlog may trigger bounded backpressure and operator attention, but it must not drop events or
  turn the derived export into an authorization source.

### SQLite-To-PostgreSQL Cutover

The candidate migration is an **offline, verify-before-activate cutover**. Dual write is forbidden.

1. Freeze local-preview writes and record the exact application commit, schema/minimum-writer
   version, audit head, manifest lock, policy/configuration generations, and export digest.
2. Export only through a versioned, duplicate-key-rejecting canonical transfer schema. Never copy a
   live SQLite file into a running PostgreSQL service.
3. Import into an empty, isolated PostgreSQL deployment epoch and verify row counts, referential
   constraints, canonical record digests, audit sequence/head, and every security-sensitive state
   inventory.
   Local principal labels, approvals, and sessions import only as `legacy_local_preview` evidence;
   the importer must not synthesize OIDC subjects, memberships, production sessions, Node
   certificates, or production approval authority.
4. Run negative migration, replay, stale-authority, and downgrade tests before activation.
5. Fence the SQLite writer, create the external recovery watermark, and explicitly activate the new
   deployment epoch. A failed pre-activation import is discarded; it is not repaired in place.
6. After activation, rollback means restore a verified PostgreSQL backup into isolation and follow
   the recovery protocol. The old SQLite process must refuse write authority and cannot be silently
   promoted again.

### Backup, Restore, Fencing, And Key Custody

- Database backup uses the selected PostgreSQL provider's encrypted base backup and point-in-time
  recovery mechanism. Ithildin records safe backup generations and verification receipts but does
  not invent a second database-copy format.
- Restore always starts isolated and read-only. It must pass schema, record-digest, audit-chain,
  tenant/workspace, key-epoch, and external-watermark reconciliation before promotion.
- The external recovery watermark binds deployment epoch, backup generation, identity/revocation
  high-water mark, audit sequence/head, configuration-signing epoch, Node-CA epoch, and creation
  time. The runtime database cannot update or validate that watermark by itself.
- The watermark lives in an operator-selected external conditional-write and signing boundary. A
  critical authority transition follows reserve-anchor-finalize ordering: reserve a pending
  transition in PostgreSQL, compare-and-set a signed watermark against the prior generation, then
  finalize the database transition. A timeout or ambiguous anchor result leaves authority pending
  and fail-closed until reconciliation; it is never retried as a fresh transition.
- Only one Manager deployment epoch may hold write authority. Lease loss, ambiguous fencing,
  unreachable prior primary, or competing primary evidence disables writes, Node authentication,
  mission admission, configuration issuance, and approvals until an attributed recovery decision.
- Production Node CA, configuration-signing, manifest-signing, audit-export-signing, and backup
  encryption keys require an external KMS/HSM or equivalent custody decision. The keyed-digest
  secret for browser-session handles is part of the same external custody and rotation contract;
  rotation invalidates every session bound to the retired key generation. Key identifiers and
  epochs may be stored in PostgreSQL; private key material may not.

### Retention And Deletion Candidate

- Every stored and exported record receives a server-derived data-class label and retention-policy
  label. Prompts, model chain-of-thought, raw IdP claims, session material, and secrets remain
  excluded.
- Audit and approval history are append-only within the active retention window. Expiration is a
  separately audited lifecycle transition with hold/conflict checks; a background job must never
  silently delete evidence after a failure.
- Audit deletion operates only on a sealed, exported, signed, independently verified segment that
  is outside retention and not under legal hold. It never removes an event from the middle of an
  active chain. A retained tombstone binds the segment range, root hash, export digest, policy
  version, and deletion authority.
- Legal hold, privacy deletion, crypto-shredding, immutable storage, and framework-specific
  retention durations require external legal and architecture decisions. Phase 1 cannot claim
  compliance merely because labels and evidence exist.

### Upgrade And Rollback Candidate

- Manager releases use an immutable signed artifact and exact candidate inventory. The external
  service manager performs installation, start, stop, and rollback; Ithildin does not control its
  own process or orchestration layer.
- Database migrations declare current schema, minimum writer, compatible reader, and irreversible
  boundary. Prefer expand/contract migrations and make older writers fail closed as soon as a new
  authority-bearing schema is activated.
- One schema-migration advisory lock excludes concurrent migration, recovery promotion, and
  signing-key epoch transition. A Node/API compatibility contract supports the current and one
  explicitly named previous protocol version; older versions remain below minimum.
- Preflight verifies artifact signature, dependency lock, database backup receipt, migration plan,
  key epochs, external watermark availability, and Node/API compatibility range.
- Application rollback is allowed without database restore only while the prior writer remains
  compatible with the active schema. Otherwise rollback is restore-only through isolated recovery.
- Node software remains an operator-managed signed-artifact replacement. Manager policy may mark a
  Node below minimum and deny authority; it still does not self-update or control the Node process.

### Required Failure Posture

| Failure | Required candidate posture |
| --- | --- |
| IdP unavailable | Deny new sign-in; existing server sessions live only to their bounded expiry and local revocation state. |
| Session-digest key unavailable or retired | Deny session creation/validation for that generation; rotation invalidates affected sessions. |
| Unknown issuer/subject or membership drift | Deny and revoke the affected session generation. |
| PostgreSQL unavailable or transaction outcome ambiguous | Deny governed mutation and expose safe unavailable/recovery status. |
| Audit serialization/checkpoint failure | Preserve prior authority state or terminal recovery-required state; never report success. |
| KMS/CA/signing authority unavailable | Deny certificate, configuration, manifest, and export signing that depends on it. |
| Lease loss or split-brain ambiguity | Fence all write and Node-authority paths. |
| Stale restore or watermark/key-epoch mismatch | Keep the restored Manager isolated and require explicit reconciliation or Node replacement. |
| Partial migration | Roll back the isolated transaction/import; never serve mixed schemas. |
| Retention worker failure or legal-hold conflict | Retain data, alert, and record a safe failure; never delete silently. |
| Clock/freshness uncertainty | Deny freshness-dependent authentication and authority changes. |

## Candidate Work-Package Order

No item below is authorized for runtime implementation by this packet. After external architecture
review and a committed go/no-go record, the smallest safe sequence is:

1. `PIS-001` — freeze the Phase 1 threat model, non-goals, dependency decision, and exact
   identity/storage contract;
2. `PIS-002` — introduce repository and transaction interfaces with SQLite behavior unchanged and
   exhaustive parity tests;
3. `PIS-003` — add PostgreSQL schema/migration tooling and isolated import verification, still with
   production startup disabled;
4. `PIS-004` — add OIDC subject mapping, server-owned memberships, opaque sessions, CSRF, and
   revocation behind a disabled production-auth mode;
5. `PIS-005` — add mTLS Node identity and application-key cross-binding behind a disabled remote
   transport mode;
6. `PIS-006` — implement PostgreSQL audit serialization, signed derived exports, and interruption
   evidence;
7. `PIS-007` — implement external watermark, backup/restore reconciliation, fencing, retention
   labels, and upgrade/rollback evidence;
8. `PIS-008` — run exact-candidate migration, restart, replay, partition, IdP/storage/KMS failure,
   stale-restore, split-brain, redaction, accessibility, and independent source-review gates before
   any enterprise-preview pilot.

Stop before a ticket if it needs an unapproved dependency, public API, schema/migration,
identity-provider contract, key-custody provider, retention/legal choice, deployment topology, or
external authority decision. Passing a prior ticket does not authorize the next one.

## Future Identity Architecture Questions

Before implementation, a future decision record must define:

- identity provider posture: local-only, OIDC/SAML, enterprise IdP, or another explicit model;
- local principal mapping from external subject to Ithildin principal ID;
- tenant, team, workspace, and role boundaries;
- admin session model, token lifetime, revocation, and local break-glass behavior;
- machine/service principal handling;
- approval attribution requirements;
- audit attribution requirements;
- disabled/unknown principal behavior;
- role-spoofing and caller-supplied role denial behavior;
- migration path from local principal labels to production identity.

## Future Storage Architecture Questions

Before implementation, a future decision record must define:

- runtime storage backend and whether Postgres becomes supported;
- migration plan from SQLite local-preview data;
- concurrency and transaction requirements for approvals, patch attempts, audit events, and Agent
  Run evidence;
- backup, restore, and disaster-recovery model;
- retention and deletion policy;
- export and signing policy;
- schema compatibility and migration rollback requirements;
- storage encryption expectations and key-management boundary;
- failure-mode behavior for unavailable storage;
- custody and notarization non-goals unless a separate trust-root decision exists.

## Disaster-Recovery Candidate Contract

The preferred candidate for external review is **replace a lost Node; do not restore its private
identity key**. This is an architecture candidate, not a selected capability or implementation
approval.

Node identity is an online authorization credential, not durable business data. Copying an old Node
private key out of a backup would permit credential cloning, make stale-backup replay difficult to
distinguish from legitimate recovery, and allow a restore to bypass a later revocation. The future
production design should therefore treat a Node host as replaceable:

1. Quarantine and revoke the lost Node record before replacement authority is issued.
2. Require a fresh, non-replayable authenticated enrollment proof for the replacement.
3. Generate the replacement private key at the replacement Node; never return it from the Manager
   or copy it from a backup.
4. Create a new server-issued Node identity binding and pull current signed configuration.
5. Prove that requests signed by the lost credential are denied after replacement.
6. Preserve an explicit lineage link from the retired Node ID to the replacement Node ID without
   reusing the retired identity.

The current local-preview mode-0600 Node state file does not satisfy this production contract. It is
exportable local state, not HSM/TPM-backed workload identity, and this packet does not authorize an
encrypted private-key backup utility around it.

Manager recovery is a separate problem. A future durable-storage design must partition recovery
assets so that one backup cannot silently recreate all authority:

| Recovery asset | Candidate custody | Restore rule |
| --- | --- | --- |
| Runtime database | Encrypted, versioned storage backup | Restore in isolation and validate schema, integrity, tenant scope, and transaction high-water marks before serving |
| Node private identity | Not backed up | Revoke and replace through fresh enrollment |
| Enrollment authority | External production identity/key-custody boundary | Restore only with explicit break-glass attribution and dual control |
| Configuration signing authority | External KMS/HSM or equivalent custody decision | Reconcile signing-key epoch with restored data before any bundle is issued |
| Audit/export signing authority | Separate custody from runtime database | Preserve verification continuity or record an explicit, externally anchored discontinuity |
| Policy/configuration source | Versioned authoritative source plus database bindings | Reject rollback to an unapproved policy/configuration generation |

### Stale-Restore And Split-Brain Rule

A database snapshot can predate a Node revocation, key rotation, approval decision, or policy
generation. Database integrity alone therefore cannot prove that a restore is current. Before a
restored Manager may authenticate a Node or issue configuration, it must reconcile against a
monotonic recovery watermark held outside the restored database. That watermark must bind at least
the tenant or deployment, database backup generation, identity/revocation high-water mark,
configuration-signing-key epoch, policy/configuration generation, and creation time.

If the external watermark, later revocation/rotation history, or matching key-custody state is
unavailable, the safe candidate posture is fail closed: keep remote administration and Node
authentication disabled, rotate recoverable Manager authorities, and require affected Nodes to
re-enroll. A stale snapshot must never silently resurrect a revoked Node or an older policy.

Only one recovered Manager authority may become active for a deployment epoch. Competing primaries,
ambiguous lease ownership, or an unreachable prior primary keep write authority disabled until an
operator completes a separately attributed fencing decision.

### Recovery Classes

- `node_host_loss`: revoke and replace the Node; do not restore its private key.
- `manager_database_loss`: restore an isolated snapshot, validate it, reconcile the external
  watermark and authority epochs, then explicitly promote it.
- `manager_signing_key_loss`: do not infer keys from database state; follow the selected external
  custody and rotation ceremony or remain unavailable.
- `site_loss`: restore Manager data and custody services first, fence the old site, establish a new
  deployment epoch, then re-enroll Nodes whose freshness cannot be proven.
- `operator_error_or_policy_rollback`: restore data only after preserving incident evidence and
  proving that the selected policy/configuration generation is authorized.

RPO, RTO, backup frequency, retention duration, geographic redundancy, custody provider, enrollment
protocol, and recovery-watermark implementation remain unselected. They require the external
architecture disposition and a later committed decision record.

### Required Recovery Proof

Any later implementation plan must include negative and interruption evidence for stolen backup,
wrong decryption authority, tampered backup, stale snapshot, retired Node credential replay,
revoked Node replacement, lost signing key, database/key epoch mismatch, partial restore,
concurrent primary, network partition, crash before promotion, and crash after promotion. Evidence
must distinguish `restored_isolated`, `reconciliation_failed`, `ready_for_promotion`, `promoted`,
and `fenced`; a successful file copy or database startup is not proof of authoritative recovery.

## Evidence Contract

Any future implementation plan must specify secret-free evidence fields for:

- authenticated subject label and Ithildin principal ID;
- tenant/team/workspace labels;
- session ID and authentication method label;
- decision ID and policy hash;
- storage backend label and schema version;
- migration state;
- backup/restore status labels;
- retention-policy label;
- audit/export verification status;
- safe error labels for identity or storage failures.

The evidence must not expose secrets, bearer tokens, session material, private keys, raw IdP claims,
raw user directory payloads, connection strings, database credentials, prompts, file contents, diffs,
response bodies, or raw sensitive paths.

## Required Before Implementation

A future implementation sprint must have:

- a post-RC decision record for `ERG-006` and/or `ERG-007`;
- explicit go/no-go outcome;
- identity and storage threat model update;
- schema and migration plan;
- source-review handoff;
- failure-mode test plan;
- rollback and backup/restore test plan;
- operator warning language;
- accepted-risk impact review;
- release/readiness gate updates;
- external architecture review before any production identity, runtime Postgres, or remote admin
  claim.

## Explicit Non-Goals

This packet does not approve:

- production IAM;
- enterprise RBAC;
- tenant/team authorization;
- remote admin use;
- runtime Postgres;
- database migrations;
- backup/restore runtime behavior;
- Node private-key export or credential-clone recovery;
- retention enforcement;
- hosted telemetry;
- remote MCP;
- hosted control plane;
- custody-grade audit;
- compliance automation;
- public/security-product positioning.

## Current Decision

The current decision is `planning_only`.

Architecture discussion and review packets may continue. Runtime implementation remains blocked
until a separate post-RC decision record approves a specific identity or storage implementation plan.

The Phase 1 candidate above selects a reviewable architecture shape only. It does not change the
decision-register status, select a capability for runtime work, or authorize `PIS-001` through
`PIS-008`.

### Planning Status Axes

- `planning_only` is the enterprise-gap capability state;
- `approved_for_planning` is permission to produce architecture and review artifacts;
- `not selected` means no runtime capability is active for implementation; and
- `ready_for_architecture_decision_record` is a possible future review disposition.

These labels are different axes, not an approval ladder. None authorizes a dependency, public API,
schema/migration, production credential, deployment, release, or runtime behavior.

Reviewer responses to the architecture disposition packet should be captured through
[production-identity-storage-external-response-intake.md](production-identity-storage-external-response-intake.md),
which validates the `EXT-PROD-IAM-STORAGE-###` finding namespace while keeping `ERG-006` and
`ERG-007` planning-only until a later committed triage update changes the decision register.
Normalized responses must also pass the fail-closed
[production-identity-storage-disposition-closure-gate.md](production-identity-storage-disposition-closure-gate.md)
before that later triage update may consider an architecture decision record.

## Validation

Run:

```sh
make production-identity-storage-architecture-check
make enterprise-readiness-gap-matrix-check
make post-rc-decision-register-check
```

<!-- production-identity-storage-contract:start -->
{"document_type":"phase_1_candidate_architecture","schema_version":"1","tool_count":24,"decision_status":"planning_only","deployment_scope":"single_organization_self_hosted","organization_id_required":true,"multi_tenant_hosted_authorized":false,"human_identity_protocol":"oidc_authorization_code_pkce_bff","human_subject_key":["organization_id","issuer","subject"],"human_provisioning":"preprovisioned_no_jit_admin","caller_identity_or_roles_authorized":false,"server_owned_memberships_required":true,"session_model":"opaque_server_side_cookie","session_handle_storage":"keyed_digest_only","session_digest_key_custody":"external_kms_hsm_or_equivalent","session_digest_key_rotation":"invalidates_bound_sessions","oidc_token_persistence_authorized":false,"csrf_protection_required":true,"recent_authentication_for_sensitive_operations_required":true,"remote_admin_tls_required":true,"remote_admin_bearer_token_authorized":false,"break_glass_scope":"loopback_fencing_isolation_recovery_orchestration_only","node_transport":"tls13_mtls_plus_ed25519_request_signatures","node_private_key_backup_authorized":false,"node_private_key_production_custody":"non_exportable_os_keystore_or_equivalent","production_storage_candidate":"postgresql","sqlite_production_authorized":false,"dual_write_authorized":false,"migration_mode":"offline_verify_before_activate","legacy_local_authority_import_authorized":false,"manager_writer_topology":"single_active_deployment_multi_process_fenced","domain_audit_outbox_atomic":true,"production_audit_canonical_store":"postgresql_append_only_hash_chain","audit_head_serialization":"segment_head_for_update","jsonl_production_role":"derived_signed_export_only","external_recovery_watermark_required":true,"external_watermark_protocol":"reserve_anchor_finalize","external_watermark_provider_selected":false,"external_key_custody_decision_required":true,"key_custody_provider_selected":false,"retention_deletion_unit":"sealed_audit_segment_only","ordered_work_packages":["PIS-001","PIS-002","PIS-003","PIS-004","PIS-005","PIS-006","PIS-007","PIS-008"],"runtime_implementation_authorized":false,"production_identity_authorized":false,"runtime_postgres_authorized":false,"remote_node_transport_authorized":false,"release_authorized":false,"uat_required_now":false}
<!-- production-identity-storage-contract:end -->
