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

## Phase 1 Offline Handoff Candidate

The smallest defensible `ERG-008` candidate is an **operator-retrieved, offline, signed evidence
handoff bundle**. Ithildin derives a closed, vendor-neutral security-event stream from a verified
canonical audit export and returns the bundle through an existing authenticated export boundary.
Ithildin does not open a network connection to a SIEM, retain destination credentials, watch an
arbitrary directory, acknowledge downstream ingestion, or become the downstream custody system.

An operator or separately managed forwarder may move a verified bundle into an organization-owned
ingestion path. That transfer is outside Ithildin's authority and must not be represented as an
Ithildin delivery success. This profile is a review candidate only; the current `no_go` decision and
all runtime flags remain unchanged.

### Authority And Data Flow

```text
canonical audit store
  -> verified canonical audit export
  -> deterministic allowlist mapper
  -> security events NDJSON
  -> manifest binds source and transformed-event digests
  -> detached Ed25519 signature binds the canonical manifest
  -> operator retrieves bundle
  -> external forwarder or SIEM verifies and ingests outside Ithildin
```

The canonical audit store remains the authority for what occurred. The handoff event stream is a
derived projection and is never consulted for policy, approval, mission, Node, runner, provider, or
recovery decisions. A downstream acknowledgement is operational metadata only; it cannot rewrite
source events or prove custody, completeness beyond the exported range, or compliance.

### Current Source Gap

The current local-preview signed audit export does **not** satisfy this candidate. It preserves
ordered hash-chained events, but each exported event does not carry an explicit deployment epoch or
canonical source sequence, and the existing signature does not bind a security-event mapper or
redaction-policy version. Row position or download order must not be silently promoted into a
production sequence contract. A later, separately approved source-schema change must make those
bindings explicit before an output can claim `ithildin.security_event.v1` compatibility.

### Closed Bundle Layout

The candidate bundle has exactly three logical artifacts. A later implementation may serialize
them as one closed JSON object or as three detached files, but it must not require archive
extraction or infer files from names.

| Artifact | Candidate schema | Required binding |
| --- | --- | --- |
| Manifest | `ithildin.security_export_manifest.v1` | Profile, source range/head, source-export digest, event and omission counts, closed omission receipts/category counts, events digest, mapper version, redaction-policy version, creation time, signing key ID/epoch |
| Events | `ithildin.security_event.v1` NDJSON | One canonical JSON object per LF-terminated line; digest covers the exact UTF-8 bytes |
| Signature | `ithildin.security_export_signature.v1` | Ed25519 signature over canonical manifest bytes; trusted public key is supplied out of band |

The manifest must bind both the verified source export and the transformed event bytes. Signing only
the transformed stream would lose provenance; signing only the source audit export would leave the
mapping output unauthenticated. Embedded public keys are descriptive and never establish trust.

Compression, encryption-at-rest packaging, object-storage upload, syslog, webhook, OTLP, CEF, LEEF,
ECS, OCSF, and vendor-specific field mappings remain later profiles. Phase 1 does not create an
archive or accept a destination credential.

### Security Event Envelope

Every line uses the exact schema identifier `ithildin.security_event.v1` and a closed top-level
field set. Required fields are:

| Field | Rule |
| --- | --- |
| `schema` | Exact schema identifier; unknown major versions fail closed |
| `event_id` | Existing canonical audit event ID; never regenerated during export |
| `category` | Closed category from the event-category registry |
| `action` | Stable Ithildin action label derived by the mapper |
| `outcome` | Closed value: `success`, `denied`, `failed`, `pending`, `recovery_required`, or `informational` |
| `severity` | Deterministic mapping: `info`, `low`, `medium`, `high`, or `critical`; never caller supplied |
| `occurred_at` | Source audit timestamp in UTC RFC 3339 form |
| `recorded_at` | Canonical-store commit timestamp when distinct; otherwise equal to `occurred_at` |
| `deployment_epoch` | Opaque server-derived deployment-epoch reference |
| `source_sequence` | Monotonic audit sequence within the deployment epoch |
| `source_event_hash` | Hash of the canonical source audit event |
| `correlation` | Closed object of optional opaque Ithildin principal, request, run, mission, workspace, Node, tool, policy, approval, and artifact references |
| `redaction` | Mapper and redaction-policy versions plus omitted-field count and category labels |

The event may carry a closed `attributes` object whose keys are registered per category. It may not
carry arbitrary source fields, a generic metadata bag, raw labels supplied by callers, or an
extensions object. An optional principal reference is an opaque server-owned Ithildin principal ID;
it is never an IdP subject, email address, username, display name, group, or caller-supplied label.
All opaque references are correlation handles, not human display values.

### Category Registry And Mapping Rules

Phase 1 uses the existing evidence categories: run lifecycle, tool lifecycle, policy decision,
approval lifecycle, executor result, audit verification, signed export, redaction summary,
diagnostics, and sandbox/workspace posture.

For each `(source_event_type, source_schema_version)` pair, the mapper registry must declare:

- exactly one output category and action, or an explicit `not_exportable` result;
- required source fields and their types;
- the closed output attribute allowlist;
- deterministic outcome and severity mapping;
- correlation fields that may be emitted as opaque references;
- the redaction reason recorded for every intentionally omitted source field; and
- fixture vectors for accepted, rejected, unknown-version, and sensitive-field cases.

Mapper and redaction-policy activation is bound to an explicit first source sequence within a
deployment epoch. That historical binding is immutable: re-exporting an older range uses the
versions active for each source event and cannot reinterpret it under a newer mapper while retaining
the same canonical event ID. A semantic correction is a new canonical audit event with its own ID,
not a retroactive remap.

Unknown event types, unknown source major versions, missing required fields, duplicate JSON keys,
non-finite numbers, invalid Unicode, or an unregistered output attribute fail the export range. They
must never be silently dropped or emitted as a partially shaped event. An explicit `not_exportable`
mapping produces a closed redaction/omission receipt in the manifest without copying the source
payload. Each receipt contains only the source sequence, canonical source-event hash, and closed
`not_exportable` omission category. The per-category counts and receipt count must agree, and
exported events plus omission receipts must cover the requested source range exactly once.

### Redaction And Data Minimization

Mapping is allowlist-only and operates on already committed safe audit fields. A second final
serialization inspection rejects forbidden keys and value classes after mapping. Hashing a secret,
prompt, path, or user-directory attribute does not make that value exportable.

The profile never exports prompts, chain-of-thought, model input or output, tool arguments or
results, file contents, diffs, response bodies, raw paths, dependency names, package scripts,
environment values, tokens, cookies, connection strings, private or session keys, raw IdP claims,
email addresses, usernames, display names, database rows, or raw sandbox internals. Error material
uses a closed safe code and category; exception messages and downstream response bodies are not
events.

The manifest records only safe redaction categories, counts, source sequences, and canonical
source-event hashes for omissions. It must not preserve the rejected key name, value, or source
payload when that would reveal sensitive structure.

### Ordering, Idempotency, And Replay

- Event identity is the canonical `event_id`. Consumers deduplicate on `(deployment_epoch,
  event_id)`; bundle ID or download time is not event identity.
- Ordering is defined only by `source_sequence` within one deployment epoch. No cross-deployment,
  cross-organization, Node-clock, runner-clock, or model-provider total order is claimed.
- Each bundle covers one contiguous, closed source-sequence range and binds the prior source hash,
  range head, event count, omission count, closed omission receipts/category counts, and exact
  source-export digest. Exported event records and omission receipts cover every sequence exactly
  once; the final record's canonical source-event hash equals the range head.
- Re-exporting the same range with the same mapper and redaction-policy versions must produce the
  same event bytes. Creation time and signature metadata may differ without changing event IDs.
- A consumer may safely replay a fully verified bundle. Ithildin never interprets a replay or
  downstream acknowledgement as new policy, approval, or execution evidence.
- Phase 1 is stateless. The operator requests one explicit contiguous source-sequence range; there
  is no persistent incremental cursor and no implicit “since last export” mode. A crash, lost
  response, or partial bundle records no progress and the same range can be requested again.
- One bundle may cover only one mapper/redaction-policy activation segment. A requested range that
  crosses either activation boundary fails closed and reports only the safe split boundaries; the
  operator must request separate bundles. Phase 1 does not encode a multi-version schedule in one
  manifest.
- Retrieval status does not alter source state. Re-requesting a range may change creation-time and
  signature metadata, but the canonical event bytes remain identical for the same source range,
  mapper version, redaction-policy version, and event schema.

### Failure, Retry, And Backpressure

The offline candidate has no automatic delivery retry and no event-copy dead-letter queue. Failed
generation or retrieval produces a bounded, secret-free attempt receipt; the canonical source
events remain available for a fresh export attempt.

Export backlog or mapper failure must not block, downgrade, or change the outcome of a canonical
governed action. It raises operator attention and may block only a stronger claim that a requested
export range is current. Resource limits are fail-closed and must bound source range, event count,
per-event bytes, total bytes, and generation time before a later implementation is authorized.

The following outcomes remain distinct: `not_started`, `generating`, `verified`, `retrieved`,
`generation_failed`, and `verification_failed`. There is no `delivered`, `accepted_by_siem`, or
`in_custody` state in this profile.

### Trust, Key Custody, And Verification

- The signing key is distinct from Node, configuration, manifest-release, session, and TLS keys.
- A verifier requires an out-of-band trusted public key and expected key epoch. An embedded key is
  insufficient.
- Local-preview file-backed Ed25519 keys support local integrity evidence only. A production claim
  requires a separately selected external key-custody, rotation, revocation, and recovery design.
- Missing, retired, mismatched, or unavailable signing authority fails export generation or
  verification; unsigned fallback is forbidden.
- Signature verification proves byte integrity and possession of the signing key. It does not prove
  external notarization, immutable retention, downstream ingestion, complete historical coverage,
  security monitoring, or regulatory compliance.

### Compatibility Contract

The event, manifest, and signature record each carry an independent exact schema identifier with a
major version. Consumers reject an unknown major version. A change to their field sets, required
fields, canonicalization, field semantics, or signature payload requires a new schema major. A
deterministic source-to-event mapping change that preserves all schema semantics requires a new
mapper version. A redaction-rule change requires a new redaction-policy version. Mapper or
redaction-policy version changes cannot stand in for a required schema-major change.

A future implementation must test canonical-byte stability, duplicate-key rejection, unknown-field
rejection, every allowed and rejected old-reader/new-writer and new-reader/old-writer direction,
mapper determinism, sensitive-field injection, partial ranges, replay, crash/lost-response
re-request behavior, signing-key mismatch, and tampered manifest/event/signature combinations.

### SEA-001 Offline Compatibility Corpus

The static [SIEM export adapter compatibility fixtures](siem-export-adapter-compatibility-fixtures.md)
freeze three accepted version-1 shapes and eighteen rejected compatibility cases. Run:

```sh
make siem-export-adapter-compatibility-check
```

The corpus covers duplicate members and identities, unknown fields and major versions, forbidden
event material including nested compound sensitive keys, closed category-attribute value types,
activation-segment crossings, partial bundles, signature-reference mismatch, exact event-byte and
range-head binding, coherent omission receipts, source-sequence drift, calendar-valid timestamps,
finite numbers, architecture-optional attributes, and unregistered category attributes. Negative
variants are materialized in memory from one committed canonical bundle and produce safe reason
labels only.

This is `SEA-001` static design evidence, not an export generator, mapper implementation, signature
verifier, destination adapter, runtime API, delivery receipt, custody claim, or authorization for
`SEA-002`. `PRD-SIEM-EXPORT-001` remains `no_go`, `ERG-008` remains `planning_only`, and every
runtime, delivery, credential, signing-key, queue, custody, compliance, and new-power flag remains
false.

### Candidate Work-Package Order

No item below is authorized for runtime implementation by this packet:

1. `SEA-001` — freeze the event envelope, category registry, redaction rules, canonical JSON, and
   golden accepted/rejected fixtures;
2. `SEA-002` — specify the source-audit-to-event mapper and prove deterministic offline fixture
   transformation with no runtime/API integration;
3. `SEA-003` — specify manifest/signature verification and stateless range/re-request crash
   semantics against detached fixtures;
4. `SEA-004` — after a separate favorable decision, implement an operator-retrieved offline bundle
   behind disabled configuration with no destination credentials or remote transport; and
5. `SEA-005` — run exact-candidate redaction, replay, corruption, resource-bound, accessibility,
   operator-warning, and independent source-review gates before any pilot.

Passing one package does not authorize the next. Stop before a dependency, public API, runtime
schema, filesystem destination, credential, remote transport, signing-custody choice, retention
decision, or downstream acknowledgement contract is added or changed.

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

The candidate above selects a planning shape only. It does not change `PRD-SIEM-EXPORT-001` from
`no_go`, authorize `SEA-001` through `SEA-005`, or imply that the current signed audit export is a
SIEM adapter.

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

<!-- siem-export-adapter-contract:start -->
{"document_type":"offline_signed_evidence_handoff_candidate","schema_version":"1","tool_count":24,"decision_status":"planning_only","adapter_profile":"operator_retrieved_offline_signed_bundle","source_authority":"verified_canonical_audit_export","current_signed_export_satisfies_candidate":false,"explicit_deployment_epoch_required":true,"explicit_source_sequence_required":true,"event_schema":"ithildin.security_event.v1","manifest_schema":"ithildin.security_export_manifest.v1","signature_schema":"ithildin.security_export_signature.v1","bundle_layout":"manifest_events_signature_detached","event_identity":"deployment_epoch_plus_canonical_event_id","ordering_scope":"deployment_epoch_audit_sequence","range_selection_model":"stateless_explicit_contiguous_range","range_version_scope":"single_mapper_and_redaction_activation","cross_activation_range_authorized":false,"persistent_cursor_authorized":false,"mapping_mode":"deterministic_allowlist_only","mapping_version_binding":"immutable_source_sequence_activation","retroactive_remap_authorized":false,"unknown_source_event_behavior":"fail_export_range","not_exportable_behavior":"counted_omission_receipt_only","manifest_binds_source_export_digest":true,"manifest_binds_event_bytes_digest":true,"signature_scope":"canonical_manifest_bytes","embedded_signing_key_trusted":false,"remote_delivery_authorized":false,"destination_credentials_authorized":false,"arbitrary_directory_watch_authorized":false,"archive_extraction_required":false,"downstream_ack_authoritative":false,"automatic_retry_authorized":false,"dead_letter_mode":"attempt_receipts_only_no_event_copy","canonical_action_backpressure_authorized":false,"partial_bundle_import_authorized":false,"signature_algorithm":"ed25519","trusted_key_source":"out_of_band_only","signing_key_custody_selected":false,"compatibility_policy":"separate_event_manifest_signature_major_mapper_and_redaction_versions","ordered_work_packages":["SEA-001","SEA-002","SEA-003","SEA-004","SEA-005"],"runtime_implementation_authorized":false,"siem_adapter_authorized":false,"hosted_telemetry_authorized":false,"remote_delivery_claim_authorized":false,"custody_claim_authorized":false,"compliance_claim_authorized":false,"uat_required_now":false}
<!-- siem-export-adapter-contract:end -->
