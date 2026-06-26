# SIEM Export Adapter Architecture

Status: design-only architecture packet for `ERG-008`.

This document defines the future architecture questions Ithildin must answer before it can implement
a SIEM-shaped export adapter. It does not add runtime behavior, export delivery code, API endpoints,
MCP tools, tool manifests, policy rules, executors, hosted telemetry, remote MCP, production
identity, runtime Postgres, custody-grade audit, compliance automation, public security-product
positioning, or any new governed tool power.

Current governed tool count: `24`.

Current selected capability: `not selected`.

## Scope

This packet covers `ERG-008`: SIEM-shaped export adapter.

The existing [siem-shaped-evidence-design.md](siem-shaped-evidence-design.md) defines event
categories and safe field boundaries. This architecture packet defines the additional delivery,
compatibility, retry, backpressure, signing, and review requirements that must exist before any
adapter implementation.

## Current Boundary

The current v1.0 local-preview boundary remains:

- local audit JSONL and SQLite evidence, not hosted telemetry;
- optional locally signed exports, not external custody;
- offline review packets, not SIEM delivery;
- Agent Run and workbench evidence, not security-operations ingestion;
- control mapping support, not compliance automation.

## Future Adapter Architecture Questions

Before implementation, a future decision record must define:

- target adapter type: file drop, local webhook, syslog, OTLP logs, object storage, or another
  explicit delivery profile;
- supported event schema version and compatibility policy;
- allowed event categories and required fields;
- field redaction and denylist rules;
- batch size, event size, and export window limits;
- retry, dead-letter, and backpressure behavior;
- delivery authentication model;
- signing and verification story;
- clock/timestamp and ordering expectations;
- idempotency and replay handling;
- operator-visible diagnostics;
- failure-mode behavior when export delivery fails.

## Event Schema Requirements

Future adapter events must be derived from stable, secret-free evidence categories:

- run lifecycle;
- tool lifecycle;
- policy decision;
- approval lifecycle;
- executor result;
- audit verification;
- signed export;
- redaction summary;
- diagnostics;
- sandbox/workspace posture.

Each exported event must include a schema version, event category, timestamp, safe correlation IDs,
principal/workspace labels when available, status/severity label, redaction summary when relevant,
and an evidence hash or audit event hash when available.

## Delivery Requirements

A future adapter plan must define:

- destination configuration shape without exposing secrets;
- connection timeout, read/write timeout, and retry limit;
- maximum batch bytes and event count;
- queue/dead-letter location if any;
- local-only versus remote delivery posture;
- safe operator errors and diagnostics;
- dry-run mode;
- compatibility tests against fixture events;
- explicit no-export handling for blocked sensitive fields.

## Export Non-Goals

The adapter must not export prompts, secrets, file contents, diffs, response bodies, package script
values, dependency names, raw sensitive paths, raw tool arguments, model output, private key
material, bearer tokens, cookies, environment variables, connection strings, local database
contents, raw sandbox internals, or unredacted IdP/user-directory claims unless a later reviewed
contract explicitly allows a narrower field.

## Required Before Implementation

A future implementation sprint must have:

- post-RC decision record for `ERG-008`;
- exact adapter profile and destination boundary;
- stable schema contract and compatibility tests;
- field-level redaction tests;
- delivery failure, retry, backpressure, and dead-letter tests;
- signing/verification evidence;
- operator warning language;
- accepted-risk impact review;
- source-review handoff;
- external/source review before any SIEM integration, delivery, or security-operations ingestion
  claim.

## Explicit Non-Goals

This packet does not approve:

- SIEM adapter runtime behavior;
- hosted telemetry by default;
- remote delivery;
- custody-grade audit claims;
- external notarization;
- immutable storage;
- production identity;
- runtime Postgres;
- compliance automation;
- security-operations control-plane claims;
- public/security-product positioning.

## Current Decision

The current decision is `planning_only`.

Architecture discussion, fixture schema design, compatibility-test planning, and review packets may
continue. Runtime adapter implementation remains blocked until a separate post-RC decision record
approves a specific adapter implementation plan.

The external response intake template for reviewer feedback is
[siem-export-adapter-external-response-intake.md](siem-export-adapter-external-response-intake.md).
It records allowed reviewer-response outcomes without mutating findings, closing `ERG-008`, or
approving runtime adapter behavior.
Normalized responses must also pass the fail-closed
[siem-export-adapter-disposition-closure-gate.md](siem-export-adapter-disposition-closure-gate.md)
before a later triage update may consider an architecture decision record.

## Validation

Run:

```sh
make siem-export-adapter-architecture-check
make siem-evidence-design-check
make enterprise-readiness-gap-matrix-check
make post-rc-decision-register-check
```
