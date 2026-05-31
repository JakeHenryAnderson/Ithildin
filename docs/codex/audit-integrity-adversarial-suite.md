# Audit Integrity Adversarial Suite

Task 107 expanded v0.3-prep coverage for local audit integrity and locally signed export evidence.
Task 130 adds the v0.4 adversarial pass for SQLite index/payload consistency and exported
event-identity ambiguity.
The audit log remains local tamper-evident evidence, not immutable storage, external notarization,
or custody-grade audit.

## SQLite / JSONL Chain Coverage

`tests/test_audit_writer.py` now covers:

- valid empty and multi-event chains;
- tampered payload fields;
- broken previous-event hashes;
- invalid payload JSON rows;
- invalid audit event schema rows;
- missing middle rows;
- SQLite indexed-column drift from stored payload JSON;
- diagnostics categories for corruption;
- fail-closed write behavior when JSONL cannot be written.

## Exported JSONL Coverage

The suite also verifies exported-event JSONL independently from SQLite:

- duplicate event lines are rejected by previous-hash validation;
- duplicate event IDs are rejected even when an adversarial export recomputes the duplicated
  event hash;
- missing middle events are rejected by previous-hash validation;
- malformed event payloads and schema failures return deterministic verification failures.

## v0.4 Adversarial Additions

Task 130 treats `payload_json` as the canonical audit evidence while verifying that SQLite index
columns still match the payload. If an indexed field such as `event_hash`, `prev_event_hash`,
`event_type`, or `request_id` drifts from the stored payload, verification fails with
`indexed audit columns mismatch` and diagnostics classify the chain as `index_mismatch`.

Export verification now also rejects duplicate event IDs independently of hash-chain ordering. This
prevents a copied or rewritten JSONL event from creating ambiguous event identity in offline review.
These checks remain local tamper-evidence only; they are not external notarization or durable custody.

## Locally Signed Export Coverage

Signed audit export tests cover:

- valid empty and multi-event signed bundles;
- tampered metadata;
- tampered event JSONL;
- event digest mismatch;
- signature byte tampering;
- embedded public-key tampering;
- wrong trusted public key;
- missing trusted public key;
- malformed top-level bundle fields;
- malformed signature fields;
- reordered events with recomputed digest.

These tests improve confidence in the local signing and verification flow. They do not create an
external trust root or prove that a host attacker cannot rewrite local state before export.
