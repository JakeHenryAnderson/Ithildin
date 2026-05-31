# SUB-012 Audit Non-Object Payload Handling

- Finding ID: SUB-012
- Severity: medium
- Area: audit/signed evidence
- Affected files/functions: packages/audit-core/src/ithildin_audit_core/writer.py; AuditWriter.verify_chain; packages/audit-core/src/ithildin_audit_core/signing.py; verify_exported_events_jsonl
- Claim being tested: audit verification should fail safely and deterministically on malformed persisted payloads.
- Observed behavior: Non-object JSON payloads such as arrays could reach `.get(...)` calls and raise an unstructured `AttributeError`.
- Risk: Corrupt local evidence could cause diagnostics/export verification paths to crash instead of reporting structured invalid evidence.
- Recommended fix: Require decoded audit payloads to be JSON objects before schema validation.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: SQLite chain verification and exported JSONL verification now reject non-object JSON payloads with `invalid audit event schema`. Tests cover both paths. External/source review remains pending.
