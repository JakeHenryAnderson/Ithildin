# SIEM Export Adapter Compatibility Fixtures

Status: static planning-only compatibility corpus for `SEA-001` and `ERG-008`.

Current governed tool count: `24`.

`make siem-export-adapter-compatibility-check` validates one canonical accepted
`ithildin.security_export_manifest.v1` bundle fixture and twenty-three descriptor-driven compatibility
cases.
The checker is an offline design oracle only. It reads committed static fixtures, materializes
negative variants in memory, validates closed schemas and byte bindings, and emits safe reason
labels. It does not generate an export, sign data, load a signing key, read runtime audit storage,
open a destination, retain a cursor, send a network request, write a queue, or acknowledge
downstream custody.

## Fixture Layout

- `tests/fixtures/siem_export_adapter/valid-bundle-v1.json` is the canonical accepted bundle.
- `tests/fixtures/siem_export_adapter/compatibility-corpus.json` binds the exact case inventory,
  mutations, acceptance expectations, and safe reason labels.
- Negative payloads are materialized in memory from the accepted fixture. They are never written
  as generated exports or represented as runtime evidence.

The accepted fixture contains the three logical artifacts defined by the architecture:

1. a closed manifest that binds the verified source-export digest and exact NDJSON bytes;
2. one LF-terminated canonical `ithildin.security_event.v1` line; and
3. a detached `ithildin.security_export_signature.v1` reference.

The manifest carries a closed omission receipt list and omission-category count object. Exported
events plus omission receipts must cover every sequence in the closed source range exactly once,
and the final event or receipt hash must equal the range head. Omission receipts contain only the
source sequence, source-event hash, and closed `not_exportable` category; they never copy source
payloads.

The all-zero fixture signature is shape-only test data. The checker validates the algorithm,
key-reference binding, canonical-manifest digest, and 64-byte base64 shape; it does not claim that
the fixture carries a valid Ed25519 signature or trusted signing authority.

## Compatibility Cases

| ID | Case | Expected result | Safe reason |
| --- | --- | --- | --- |
| `SEA-COMP-001` | Canonical version-1 bundle | accept | none |
| `SEA-COMP-002` | Duplicate JSON member | reject | `duplicate_json_member` |
| `SEA-COMP-003` | Unknown bundle field | reject | `unknown_bundle_field` |
| `SEA-COMP-004` | Unknown manifest major version | reject | `unsupported_manifest_schema` |
| `SEA-COMP-005` | Forbidden sensitive event field | reject | `forbidden_event_field` |
| `SEA-COMP-006` | Source range crosses an activation segment | reject | `cross_activation_range` |
| `SEA-COMP-007` | Missing detached signature artifact | reject | `partial_bundle` |
| `SEA-COMP-008` | Signature references the wrong manifest digest | reject | `signature_manifest_digest_mismatch` |
| `SEA-COMP-009` | Unknown event major version | reject | `unsupported_event_schema` |
| `SEA-COMP-010` | Manifest does not bind the exact event bytes | reject | `events_digest_mismatch` |
| `SEA-COMP-011` | Event sequence does not match the closed source range | reject | `non_contiguous_source_sequence` |
| `SEA-COMP-012` | Event contains a non-finite JSON number | reject | `non_finite_number` |
| `SEA-COMP-013` | Event category carries an unregistered attribute | reject | `unknown_event_attribute` |
| `SEA-COMP-014` | Registered attribute contains a nested compound sensitive key | reject | `forbidden_event_field`, `invalid_event_attribute` |
| `SEA-COMP-015` | Omission count disagrees with receipts and source-range cardinality | reject | `omission_count_mismatch`, `source_range_count_mismatch` |
| `SEA-COMP-016` | Range-head hash disagrees with the final source record | reject | `range_head_hash_mismatch` |
| `SEA-COMP-017` | Two source sequences reuse one canonical event identity | reject | `duplicate_event_identity` |
| `SEA-COMP-018` | Timestamp has valid syntax but an impossible calendar date | reject | `invalid_calendar_timestamp` through `invalid_event_shape` |
| `SEA-COMP-019` | Architecture-optional event `attributes` is absent | accept | none |
| `SEA-COMP-020` | Valid JSON exponent overflows the finite-number parser | reject | `overflowing_json_number` through `non_finite_number` |
| `SEA-COMP-021` | One safe omission receipt fills a source-range gap | accept | `valid_omission_receipt`; no rejection reason |
| `SEA-COMP-022` | Every source event in the range is represented by a safe omission receipt | accept | `valid_all_omission_range`; empty NDJSON is valid |
| `SEA-COMP-023` | A JSON string decodes to an unpaired Unicode surrogate | reject | `invalid_unicode_scalar` through `invalid_unicode` |

The descriptor labels `nested_sensitive_attribute` and `optional_attributes_absent` make the
redaction and optional-field compatibility cases machine-identifiable without including payload
content. An empty event stream is valid only when the manifest and closed omission receipts cover
the entire requested range. Every decoded string and object key must contain valid Unicode scalar
values; invalid Unicode returns a fixed safe label before canonicalization or UTF-8 hashing.

The validator also fails closed on malformed shapes, unknown manifest/event/signature fields,
invalid timestamps and identifiers, invalid hash or signature encodings, event/omission-count drift,
duplicate canonical identities, range-head drift, deployment-epoch drift, mapper/redaction version
drift, unsafe attribute value types, and non-canonical NDJSON. Registered category attributes have
closed scalar type/value schemas; arbitrary nested dictionaries and lists are not accepted.

## Redaction Boundary

The validator recursively rejects forbidden event keys, including prompts, chain-of-thought, model
input/output, tool arguments/results, file contents, diffs, response bodies, raw paths, dependency
names, package scripts, environment values, tokens, cookies, connection strings, private keys, raw
identity-provider claims, email addresses, usernames, display names, database rows, and raw sandbox
internals. It reports only the safe reason label and never echoes the rejected key or value.

## Authority Boundary

Passing this corpus completes only the static `SEA-001` fixture vector. It does not change
`PRD-SIEM-EXPORT-001` from `no_go` and does not close `ERG-008`. It does not authorize `SEA-002`,
approve runtime mapper or adapter implementation, enable hosted telemetry or remote delivery,
select signing-key custody, create destination credentials, establish SIEM custody, prove external
notarization, provide immutable retention, automate compliance, or grant a new governed power.

The following remain false:

- runtime changes allowed;
- SIEM adapter allowed;
- hosted telemetry allowed;
- remote delivery allowed;
- signing-key access allowed;
- destination credentials allowed;
- persistent cursor allowed;
- queue or dead-letter storage allowed;
- custody-grade audit claims allowed;
- compliance claims allowed;
- security-operations control-plane authority allowed;
- closes `ERG-008`;
- new power classes allowed.
