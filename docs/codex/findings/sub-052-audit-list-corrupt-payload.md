# SUB-052 Audit List Corrupt Payload

- Finding ID: SUB-052
- Severity: low
- Area: audit API diagnostics
- Affected files/functions: packages/audit-core/src/ithildin_audit_core/writer.py; AuditWriter.list_events; apps/api/src/ithildin_api/app.py; list_audit_events
- Claim being tested: Audit read APIs should fail safely when stored audit payload JSON is corrupt.
- Observed behavior: Internal proxy review found that corrupt `payload_json` rows could bubble up as generic server errors.
- Risk: Operators reviewing audit health could get an opaque 500 instead of actionable, safe diagnostics.
- Recommended fix: Convert corrupt or non-object stored payloads into structured audit read errors and return a safe admin API conflict.
- Blocking status: later
- Disposition: fixed
- Verification notes: `AuditWriter.list_events` now raises `AuditWriteError` for corrupt/non-object payload JSON, and `/audit-events` returns a safe 409. Tests cover corrupt payload handling without leaking event contents. External/source review remains pending.
