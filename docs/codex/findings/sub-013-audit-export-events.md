# SUB-013 Audit Export Events

- Finding ID: SUB-013
- Severity: medium
- Area: audit/signed evidence
- Affected files/functions: apps/api/src/ithildin_api/app.py; export_audit_events; export_signed_audit_events
- Claim being tested: admin audit export actions should leave an audit trail.
- Observed behavior: `/audit-events/export` and `/audit-events/export/signed` returned exports without writing `audit.exported` events.
- Risk: Evidence extraction could happen without a local audit record of the export action.
- Recommended fix: Write safe `audit.exported` events for plain and signed export attempts without exposing event contents or secrets.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: Both export endpoints now write an `audit.exported` event with safe metadata before creating the export response. API tests assert the event appears in JSONL and signed export bundles. External/source review remains pending.
