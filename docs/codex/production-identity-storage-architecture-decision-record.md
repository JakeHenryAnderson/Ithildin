# Production Identity And Storage Architecture Decision Record

Status: committed planning-only architecture decision for `ERG-006` and `ERG-007`.

Decision ID: `PRD-PROD-IAM-STORAGE-ARCH-001`.

Decision record status: `approved_for_pis_001_planning_only`.

Current governed tool count: `24`.

Current selected runtime capability: `not selected`.

Previous `ERG-006` status: `planning_only`.

Previous `ERG-007` status: `planning_only`.

Recorded `ERG-006` status: `planning_only`.

Recorded `ERG-007` status: `planning_only`.

This record accepts the reviewed Phase 1 architecture as the basis for one bounded planning work
package: `PIS-001`. It does not approve implementation planning for `PIS-002` through `PIS-008`,
runtime implementation, a dependency change, a public API, a database schema or migration,
production credentials, production identity, enterprise RBAC, remote administration, runtime
PostgreSQL, backup/restore behavior, retention enforcement, hosted trust, or a product claim.

## Decision Inputs

- Architecture packet: `docs/codex/production-identity-storage-architecture.md`.
- Disposition packet: `var/review-packets/v3/production-identity-storage-external-review`.
- Source-review record: `docs/codex/production-identity-storage-source-review.md`.
- Reviewed remediation commit: `88f8e53cc54e599df25da6b14d465a5fb06848d7`.
- Reviewed packet-manifest digest:
  `sha256:bdcac6f8cbb1c5a3cec40730eccdf2cb6a3a2d1f9c0ab2a588e3f1afaf378c57`.
- Reviewer disposition: `continue_architecture_planning`.
- Review result: all five `EXT-PROD-IAM-STORAGE-001` through
  `EXT-PROD-IAM-STORAGE-005` findings fixed; no new critical, high, or medium finding.
- Closure result at the reviewed candidate: `ready_for_architecture_decision_record` for both
  enterprise gaps with every implementation and runtime authority flag false.

The later disposition-record commit is documentation and routing evidence. It does not replace the
reviewed remediation candidate or imply that generated evidence authorizes runtime behavior.

## Trigger And Requested Change

- Trigger: exact-candidate packet-and-source review found the remediated Phase 1 architecture
  coherent enough for continued architecture planning.
- Requested change: move from review preparation to a bounded `PIS-001` planning gate.
- Current boundary being changed: planning workflow only. No product or governed-power boundary is
  changed.
- Why this cannot remain an untracked note: the next work package needs a durable, testable stop
  line separating architecture acceptance from dependency, schema, identity, and storage runtime
  decisions.

## Accepted Architecture Direction

The following direction is accepted only as input to `PIS-001`:

- a single-organization, self-hosted Manager deployment candidate;
- human identity through an OIDC Authorization Code with PKCE backend-for-frontend candidate;
- exact configured/discovery/token issuer matching and immutable subject mapping;
- server-owned memberships and permissions with caller-supplied identity or roles denied;
- opaque server-side sessions with a separate non-authenticating `session_audit_id`;
- PostgreSQL as the only candidate production runtime database while SQLite remains the only
  supported runtime backend today;
- offline verify-before-activate migration with no dual write and no import of legacy local
  authority;
- atomic domain, audit, and export-outbox mutation;
- external recovery watermarking, single active deployment-epoch write authority, and fail-closed
  stale-restore or split-brain handling;
- replace-not-restore Node private identity recovery; and
- explicit database transport, least-privilege role, credential-custody, encryption, WAL, restore,
  and failure-mode requirements before `PIS-002` or any database dependency decision.

These are architecture constraints, not implemented features or deployment claims.

## Allowed `PIS-001` Scope

`PIS-001` may produce documentation, static contracts, inventories, decision matrices, threat-model
artifacts, negative-test plans, and source-review handoff material that:

The executable planning boundary is defined in
`production-identity-storage-pis-001-planning-gate.md`.

- freezes the Phase 1 assets, actors, trust boundaries, abuse cases, and failure assumptions;
- freezes explicit non-goals and claim boundaries;
- inventories current identity, session, cryptography, database, migration, and test dependencies;
- evaluates candidate dependencies using maintenance, license, supply-chain, interoperability,
  cryptographic-boundary, and operational criteria;
- records recommended and rejected dependency choices without changing project manifests or lock
  files;
- freezes the exact identity/storage contract that later work packages would have to satisfy;
- defines the `PIS-002` entry gate, rollback expectations, and source-review requirements; and
- preserves the current 24-tool surface and local-preview runtime behavior.

## Explicitly Forbidden Scope

This decision does not authorize:

- dependency additions, removals, upgrades, manifest edits, or lock-file changes;
- runtime implementation or implementation planning for `PIS-002` through `PIS-008`;
- production IAM, OIDC/SAML/SCIM runtime behavior, enterprise RBAC, just-in-time provisioning, or
  tenant/team authorization runtime behavior;
- remote administration, remote MCP, hosted MCP, hosted control plane, or production credentials;
- runtime PostgreSQL, schema creation, migrations, repositories, transaction adapters, data import,
  dual write, backup/restore runtime behavior, or retention enforcement;
- key-custody provider selection, production CA/KMS/HSM custody, or signing-key possession;
- Node transport expansion, shell, Docker, Kubernetes, browser automation, arbitrary HTTP, broad filesystem writes, or sandbox orchestration;
- SIEM adapter runtime behavior, hosted telemetry, compliance automation, custody-grade audit
  claims, or public/security-product positioning;
- release, production promotion, enterprise-preview pilot acceptance, or UAT acceptance; or
- any new governed tool or power class.

## Required `PIS-001` Evidence

The work package is complete only when a committed planning artifact provides:

1. a structured threat model covering human, service, Node, database, backup, recovery, and operator
   trust boundaries;
2. explicit abuse cases for issuer confusion, role spoofing, session theft/replay, cross-workspace
   access, stale restore, split brain, migration ambiguity, audit truncation, credential loss, and
   dependency compromise;
3. an inventory of current dependencies and candidate dependency decisions with rejection reasons;
4. an exact contract delta, if any, that does not weaken the reviewed architecture;
5. a negative and interruption test plan;
6. rollback and stop conditions;
7. accepted-risk impact and operator warning language;
8. a `PIS-002` entry decision that remains no-go unless separately committed; and
9. focused gates plus the applicable release and exact-candidate review evidence.

## Stop Conditions

Stop `PIS-001` and require a separate decision if it would:

- add or change a dependency rather than record a recommendation;
- change a public API, schema, migration, identity-provider contract, retention/legal rule,
  deployment topology, or external authority;
- weaken exact issuer matching, server-owned authorization, evidence redaction, transaction
  atomicity, restore fencing, or fail-closed behavior;
- introduce production credentials, provider accounts, signing keys, or real customer data;
- change the 24-tool surface or add a governed power class;
- claim production, regulatory, custody, sandbox, SIEM, or security-product readiness;
- reveal a critical/high trust-boundary issue; or
- fail the same applicable gate three times.

## Decision Outcome

The approved outcome is:

```text
approved_for_pis_001_planning_only
```

The allowed workflow transition is:

```text
ERG-006/ERG-007 architecture review recorded -> PIS-001 planning gate
```

The enterprise gaps remain `planning_only`. The selected runtime capability remains `not selected`.
Passing `PIS-001` will not itself authorize `PIS-002`, dependency changes, schema/migration work, or
runtime behavior.

## Validation

Run:

```sh
make production-identity-storage-architecture-decision-record-check
make production-identity-storage-architecture-check
make production-identity-storage-disposition-closure-check
make post-rc-decision-register-check
make no-new-powers-guardrail
make tool-surface-invariant-gate
```

Release gates must continue to pass with no live normalized response present.
