# Audit Integrity Adversarial Suite

Task 107 expands v0.3-prep coverage for local audit integrity and locally signed export evidence.
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
- diagnostics categories for corruption;
- fail-closed write behavior when JSONL cannot be written.

## Exported JSONL Coverage

The suite also verifies exported-event JSONL independently from SQLite:

- duplicate event lines are rejected by previous-hash validation;
- missing middle events are rejected by previous-hash validation;
- malformed event payloads and schema failures return deterministic verification failures.

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
