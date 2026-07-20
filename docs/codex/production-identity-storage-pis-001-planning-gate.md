# Production Identity And Storage PIS-001 Planning Gate

Status: ready for bounded `PIS-001` planning execution.

Work package: `PIS-001`.

Parent decision: `PRD-PROD-IAM-STORAGE-ARCH-001`.

Parent decision status: `approved_for_pis_001_planning_only`.

Current governed tool count: `24`.

Current selected runtime capability: `not selected`.

Current `ERG-006` status: `planning_only`.

Current `ERG-007` status: `planning_only`.

This gate turns the accepted architecture direction into one bounded planning deliverable. It does
not approve dependencies, schemas, migrations, identity-provider integration, production
credentials, runtime PostgreSQL, remote administration, production identity, or any runtime code.

## Required Output

Create the committed planning artifact:

```text
docs/codex/production-identity-storage-pis-001-threat-model-and-dependency-decision.md
```

The artifact must freeze the Phase 1 threat model, non-goals, dependency recommendations and
rejections, and exact identity/storage contract. It may recommend a later PIS-002 entry decision;
it may not grant that decision.

The resulting artifact is
[production-identity-storage-pis-001-threat-model-and-dependency-decision.md](production-identity-storage-pis-001-threat-model-and-dependency-decision.md)
and is validated with `make production-identity-storage-pis-001-decision-check`. Its presence does
not by itself satisfy the done criteria or authorize PIS-002.

## Allowed Work

- inspect current source, dependency manifests, lock files, database boundaries, authentication
  boundaries, session handling, cryptographic helpers, deployment files, tests, and evidence gates;
- identify assets, actors, trust boundaries, entry points, authority transitions, data classes,
  recovery boundaries, and abuse cases;
- record current dependencies and evaluate candidate libraries or platform components without
  modifying manifests or locks;
- compare maintenance posture, license, supply-chain exposure, standards support, failure modes,
  operational burden, key-custody implications, and testability;
- freeze non-goals, safe defaults, exact authority checks, evidence fields, and fail-closed rules;
- define negative, interruption, restart, replay, migration, restore, and partition test plans;
- identify decisions that require later operator, legal/retention, provider, or infrastructure
  authority; and
- prepare a later source-review handoff and PIS-002 entry decision.

## Forbidden Work

- adding, removing, upgrading, importing, or executing a new dependency;
- modifying `pyproject.toml`, `uv.lock`, package manifests, lock files, or container images;
- changing public APIs, MCP tools, schemas, migrations, repositories, transaction behavior, or
  storage backends;
- implementing OIDC/SAML/SCIM, sessions, enterprise RBAC, tenant/team authorization, remote admin,
  PostgreSQL, backup/restore, retention, KMS/HSM/CA integration, or remote Node transport;
- taking custody of credentials, signing keys, production identities, provider accounts, or real
  customer data;
- changing the 24-tool manifest, policy semantics, approval behavior, audit behavior, or governed
  power classes;
- shell, Docker socket, Kubernetes, browser automation, arbitrary HTTP, broad filesystem writes,
  sandbox orchestration, SIEM runtime delivery, or hosted telemetry;
- production, compliance, custody-grade, sandbox, SIEM, EDR/MDM, or public security-product claims;
  or
- release, production promotion, enterprise-preview pilot acceptance, or UAT acceptance.

## Threat-Model Minimums

The required output must cover at least:

- assets: identities, memberships, sessions, approvals, policy/configuration generations, Node
  credentials, database state, audit chains, outbox state, backups, WAL, signing keys, recovery
  watermarks, and evidence exports;
- actors: human operator, organization admin, ordinary principal, disabled principal, Node/service
  principal, database role, migration role, backup operator, IdP, external custody service, local
  attacker, network attacker, compromised dependency, and stale/restored Manager;
- boundaries: browser-to-Manager, IdP callback, Manager session store, API authorization, Manager to
  PostgreSQL, Manager to Node, database to backup/WAL storage, Manager to KMS/CA, and export to
  external verifier;
- abuse cases: exact-issuer confusion, subject remap, caller-role spoofing, membership drift,
  session fixation/theft/replay, CSRF, cross-workspace access, disabled-principal reuse, Node key
  cloning, stale configuration, split brain, ambiguous transactions, partial migration, audit-head
  races, outbox loss, stale restore, watermark rollback, backup theft, key-epoch mismatch,
  dependency compromise, and sensitive evidence leakage; and
- fail-closed behavior for unavailable IdP, session-digest key, database, KMS/CA, watermark,
  signing authority, or trustworthy time.

## Dependency-Decision Minimums

For each candidate dependency or platform component, record:

- capability needed and why the standard library or current dependency set is insufficient;
- candidate name and the exact layer it would occupy;
- whether it processes credentials, tokens, keys, SQL, migrations, or untrusted network input;
- maintenance and release posture;
- license and redistribution posture;
- dependency and supply-chain footprint;
- standards/interoperability behavior;
- security defaults and known unsafe configuration classes;
- deterministic and failure-mode testability;
- operational, upgrade, rollback, and incident-response burden;
- accepted/rejected/deferred recommendation with reasons; and
- the later gate required before any manifest or lock-file change.

Provider accounts, infrastructure products, retention durations, RPO/RTO values, KMS/HSM vendors,
CA vendors, and external watermark services must remain unselected unless separately authorized.

## Exact Contract Freeze

The planning artifact must preserve or strengthen:

- exact configured/discovery/token issuer equality;
- immutable organization/provider/exact-issuer/subject identity mapping;
- server-owned authorization and denial of caller-supplied identity or roles;
- opaque session handles, keyed lookup digests, and separate non-authenticating audit references;
- no persisted OIDC tokens;
- SQLite as the only supported runtime backend today;
- PostgreSQL only as a production candidate with TLS server verification and separate least-
  privilege runtime/migration roles;
- offline verify-before-activate migration, no dual write, and no import of legacy local authority;
- atomic domain, audit, and export-outbox mutation;
- one active deployment epoch, restore isolation, external watermark reconciliation, and
  split-brain fencing;
- replace-not-restore Node private identity; and
- secret-free, privacy-safe evidence.

## Done Criteria

`PIS-001` planning is complete only when:

1. the required output exists and its validator passes;
2. every minimum threat-model and dependency-decision field is addressed;
3. recommendations and unresolved external decisions are distinct;
4. no dependency, API, schema, migration, runtime, manifest, policy, or tool change occurred;
5. PIS-002 remains blocked behind a separate entry decision;
6. focused tests, lint, typing, docs, no-new-powers, and tool-surface gates pass;
7. a clean exact-candidate release checkpoint and packet redaction scan pass; and
8. any critical/high finding stops progression rather than being accepted implicitly.

## Stop Conditions

Stop immediately if the work requires a dependency change, public API, schema/migration,
production credentials, identity-provider contract, retention/legal choice, deployment topology,
external authority, new governed power, weaker fail-closed rule, critical/high finding, or three
failures of the same applicable gate.

## Validation

Run:

```sh
make production-identity-storage-pis-001-decision-check
make production-identity-storage-pis-001-planning-gate-check
make production-identity-storage-architecture-decision-record-check
make production-identity-storage-architecture-check
make no-new-powers-guardrail
make tool-surface-invariant-gate
```

Passing this gate authorizes preparation of the PIS-001 planning artifact only. It does not prove
that PIS-001 is complete and does not authorize PIS-002 or runtime work.
