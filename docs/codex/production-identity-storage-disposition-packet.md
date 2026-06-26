# Production Identity And Storage Disposition Packet

Status: external architecture-disposition handoff packet for `ERG-006`, `ERG-007`, and
`PRD-PROD-IAM-STORAGE-001`.

Current governed tool count: `24`.

Current `ERG-006` status: `planning_only`.

Current `ERG-007` status: `planning_only`.

This packet defines the review question for Ithildin's future production identity and durable
storage lane. It asks whether the current design-only architecture evidence is coherent enough to
continue architecture planning, or whether the lane needs revision before any post-RC implementation
decision can be drafted.

This packet does not approve production IAM, enterprise RBAC, tenant/team authorization runtime
behavior, remote admin use, runtime Postgres, database migrations, backup/restore runtime behavior,
retention enforcement, hosted control plane, custody-grade audit claims, compliance automation,
public/security-product positioning, tool manifests, executors, policy rules, API endpoints, MCP
transports, hosted telemetry, remote MCP, SIEM adapters, sandbox orchestration, local model
invocation, trusted-host promotion, shell, Docker/Kubernetes/browser governed powers, arbitrary
HTTP, broad filesystem writes, plugin SDK behavior, or new governed tool powers.

Validate this packet with:

```sh
make production-identity-storage-disposition-packet-check
make production-identity-storage-disposition-closure-check
```

Generate the focused disposition handoff with:

```sh
make production-identity-storage-disposition-packet
```

## Required Reviewer Question

A reviewer should answer:

Is the current production identity and storage architecture evidence coherent enough for continued
planning, or must Ithildin revise the identity, tenant/workspace, session/admin, migration,
backup/restore, retention, audit-attribution, and failure-mode model before any implementation
decision is considered?

Allowed reviewer dispositions:

- `continue_architecture_planning`: the current evidence is coherent for more design, static
  schemas, threat-model updates, migration sketches, and review packets.
- `revise_before_more_planning`: the evidence has missing architecture questions, ambiguous
  authority, weak failure-mode coverage, or unsafe evidence expectations that should be fixed before
  more planning.
- `block_runtime_implementation`: a blocking identity/storage risk prevents implementation
  planning until a later decision record resolves it.

## Current Evidence Set

The reviewer should inspect:

| Evidence | Source |
| --- | --- |
| Architecture packet | `production-identity-storage-architecture.md` |
| External response intake | `production-identity-storage-external-response-intake.md` |
| Fail-closed closure gate | `production-identity-storage-disposition-closure-gate.md` |
| Post-RC decision register | `post-rc-decision-register.md` |
| Post-RC decision gate | `post-rc-decision-gate.md` |
| Enterprise gap matrix | `enterprise-readiness-gap-matrix.md` |
| Enterprise runway | `enterprise-readiness-runway.md` |
| Accepted-risk register | `accepted-risk-register.json` |
| No-new-powers evidence | `make no-new-powers-guardrail` and `make tool-surface-invariant-gate` |

## Required Architecture Focus

Before implementation planning, the lane needs clear answers for:

- identity provider posture and local principal mapping;
- tenant, team, workspace, and role boundaries;
- admin session lifetime, revocation, break-glass, and remote admin non-goals;
- machine/service principal handling;
- disabled/unknown principal behavior and role-spoofing denial;
- approval and audit attribution requirements;
- runtime storage backend decision;
- SQLite migration path, rollback, and compatibility policy;
- approval, patch-attempt, audit, and Agent Run transaction requirements;
- backup, restore, disaster recovery, retention, deletion, and export policy;
- storage encryption and key-management boundary;
- unavailable-storage and partial-migration failure modes;
- external architecture/source review requirements.

## Required Boundary Flags

Current output must continue to report:

- production identity allowed: `false`;
- enterprise RBAC allowed: `false`;
- tenant/team authorization runtime allowed: `false`;
- remote admin allowed: `false`;
- runtime Postgres allowed: `false`;
- database migrations allowed: `false`;
- backup/restore runtime allowed: `false`;
- retention enforcement allowed: `false`;
- hosted control plane allowed: `false`;
- custody-grade audit claims allowed: `false`;
- compliance claims allowed: `false`;
- new power classes allowed: `false`;
- closes `ERG-006`: `false`;
- closes `ERG-007`: `false`.

## Required Negative Review Focus

The disposition review should look for:

- wording that treats local principal labels as enterprise authentication;
- wording that treats SQLite local-preview state as production durable storage;
- session, tenant, or role language that implies runtime authorization already exists;
- migration, backup, restore, retention, or remote-admin expectations that imply implementation
  approval;
- evidence fields that could leak bearer tokens, session material, private keys, raw IdP claims,
  directory payloads, database credentials, connection strings, prompts, file contents, diffs,
  response bodies, or raw sensitive paths;
- unclear failure behavior for unavailable identity providers, unavailable storage, failed
  migrations, partial backups, stale restores, or retention conflicts;
- claims of custody-grade audit, production deployment readiness, compliance automation, or
  public/security-product positioning.

## Current Allowed State

This packet supports architecture docs, schema sketches, static examples, threat-model questions,
review packets, and operator warning design. It does not close `ERG-006` or `ERG-007`, and it does
not authorize production identity or durable storage runtime behavior. A later post-RC decision
record must record reviewer disposition before any implementation plan moves.

Reviewer responses should be recorded through
[production-identity-storage-external-response-intake.md](production-identity-storage-external-response-intake.md)
after this packet is reviewed. That intake captures `EXT-PROD-IAM-STORAGE-###` findings without
mutating findings, closing `ERG-006`/`ERG-007`, or approving runtime identity/storage behavior.
Normalized responses must also pass
[production-identity-storage-disposition-closure-gate.md](production-identity-storage-disposition-closure-gate.md)
before a later triage update may consider an architecture decision record.
