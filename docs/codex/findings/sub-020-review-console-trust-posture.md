# SUB-020 Review Console Trust Posture

- Finding ID: SUB-020
- Severity: medium
- Area: review console/admin status
- Affected files/functions: apps/ui/src/App.tsx; System Trust panel
- Claim being tested: the local review console should present system trust posture without implying audit-only verification is full-system verification.
- Observed behavior: The System Trust panel omitted principal/workspace/storage/telemetry posture and labeled audit-chain validity as `Verified`.
- Risk: Operators could overread a valid audit hash chain as full system verification and miss important local-preview posture fields.
- Recommended fix: Render principal, workspace, storage, and telemetry status, and rename the audit-only label.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: The System Trust panel now displays principal counts, workspace counts/default workspace, storage backend, and telemetry state. Audit labels now say `Audit chain OK` rather than standalone `Verified`. UI typecheck covers the status shape. External/source review remains pending.
