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
