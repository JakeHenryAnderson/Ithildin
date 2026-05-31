# SUB-010 Signed Export Lifecycle Drift

- Finding ID: SUB-010
- Severity: high
- Area: audit/signed evidence
- Affected files/functions: packages/audit-core/src/ithildin_audit_core/writer.py; AuditWriter.export_jsonl_bundle; apps/api/src/ithildin_api/app.py; export_signed_audit_events
- Claim being tested: signed audit exports must not present locally inconsistent SQLite/JSONL evidence as clean signed evidence.
- Observed behavior: Signed exports could be produced from SQLite-derived export content even when audit diagnostics reported SQLite/JSONL lifecycle drift.
- Risk: A reviewer could verify a signed export and miss that the local audit lifecycle needed recovery review.
- Recommended fix: Include audit lifecycle diagnostics in export metadata and require a clean lifecycle before runtime signed export.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `AuditWriter.export_jsonl_bundle` now embeds lifecycle diagnostics and supports `require_clean_lifecycle`. `/audit-events/export/signed` uses the clean-lifecycle requirement and returns a safe conflict when diagnostics report drift. Tests cover recovery-required metadata and signed-export rejection for unclean lifecycle. External/source review remains pending.
