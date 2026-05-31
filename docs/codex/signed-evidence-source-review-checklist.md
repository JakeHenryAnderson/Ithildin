# Signed Evidence Source Review Checklist

Task 162 creates the source-review checklist for locally signed evidence: audit export bundles and
manifest-lock signatures. Use it with [source-review-runbook-v2.md](source-review-runbook-v2.md),
[source-file-inspection-packet.md](source-file-inspection-packet.md), and
[evidence-contracts.md](evidence-contracts.md).

## Files And Functions

Inspect:

- `packages/audit-core/src/ithildin_audit_core/signing.py`
  - `generate_audit_signing_keypair`
  - `signed_audit_export_bundle`
  - `verify_signed_audit_export_bundle`
  - `audit_signing_status`
  - `verify_exported_events_jsonl`
  - `_signature_payload`
  - `_metadata_matches_verification`
  - `_event_hash_from_event`
  - `_load_private_key`
  - `_load_public_key`
- `packages/audit-core/src/ithildin_audit_core/writer.py`
  - audit verification and JSONL export helpers
- `apps/api/src/ithildin_api/manifest_lock.py`
  - `write_manifest_lock_signature`
  - `verify_manifest_lock_signature`
  - `manifest_lock_signature_status`
  - `require_manifest_lock_signature`
  - `manifest_lock_payload`
- `scripts/signed_evidence_demo.py`
- `scripts/signed_evidence_demo_verify.py`

## Claims To Test

- Signed audit export verifies the Ed25519 signature, event JSONL digest, and embedded audit
  hash-chain metadata.
- Verification fails on tampered metadata, event order, event JSONL, event digest, signature, key ID,
  embedded public key, or trusted public key mismatch.
- Manifest-lock signatures bind the current lock payload/digest, lock path, key ID, public key,
  algorithm, timestamp, and signature.
- Runtime audit signing and signed-manifest-lock enforcement are explicit local configuration, not
  silently generated trust roots.
- The signed-evidence demo uses ignored non-production fixture keys and does not change runtime
  signing configuration.
- Release evidence distinguishes runtime signing status from demo signing status.
- Docs and UI labels describe this as locally signed evidence only, not external notarization,
  hosted custody, official supply-chain signing, production key management, tamper-proof storage, or
  immutable evidence.

## Evidence Commands

```sh
make signed-evidence-demo
make signed-evidence-demo-verify
uv run pytest tests/test_audit_writer.py tests/test_signed_evidence_demo.py tests/test_tool_registry.py
make evidence-confusion-gate
make release-check
```

## Finding Prompts

For every issue, record:

- whether the issue affects audit export signatures, manifest-lock signatures, demo evidence, or
  release evidence;
- whether verification can be replayed, substituted, downgraded, or confused across bundle types;
- whether public key or key ID handling allows a wrong trust root;
- whether the issue creates an overclaim about custody, notarization, immutability, or production
  signing.

## Non-Goals

This checklist does not add external timestamping, notarization, immutable storage, hosted custody,
official release signing, key rotation policy, production key management, or per-event signatures.
