# SUB-048 Signed Export Failure Evidence

- Finding ID: SUB-048
- Severity: medium
- Area: audit/signed evidence
- Affected files/functions: apps/api/src/ithildin_api/app.py; export_signed_audit_events; _write_audit_export_event
- Claim being tested: Signed audit export attempts must not record successful export evidence when signing fails before a bundle is produced.
- Observed behavior: Internal proxy review found that `/audit-events/export/signed` wrote `audit.exported` before key loading and lifecycle checks completed, so missing keys or unclean lifecycle could leave a successful-looking export event.
- Risk: Reviewers could see a durable `audit.exported` event for an export that never actually succeeded.
- Recommended fix: Preflight clean lifecycle and signing key availability before writing export success evidence; write the success event only after export construction can succeed.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: The signed-export route now preflights clean lifecycle and signing before writing the export event. Tests assert missing keys and unclean lifecycle do not write `audit.exported`. External/source review remains pending.
