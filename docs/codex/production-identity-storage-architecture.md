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

## Validation

Run:

```sh
make production-identity-storage-architecture-check
make enterprise-readiness-gap-matrix-check
make post-rc-decision-register-check
```
