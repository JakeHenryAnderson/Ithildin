# SUB-079 Patch Diagnostics Detail Visibility

- Finding ID: SUB-079
- Severity: medium
- Area: review console/admin boundary
- Affected files/functions: apps/ui/src/App.tsx `PatchDiagnosticsSummary`; apps/api/src/ithildin_api/patches.py `patch_apply_diagnostics`
- Claim being tested: When patch-apply diagnostics report recovery-required or ambiguous state, the review console should expose enough safe metadata for an admin to identify the affected attempt or approval.
- Observed behavior: The API returned safe attempt and stuck-approval metadata, but the review console only rendered counts and recommendation text.
- Risk: An admin could know that diagnostics required attention without knowing which approval/proposal/path/status required manual review.
- Recommended fix: Render compact diagnostic tables with safe IDs, workspace/path, diagnostic status, reason, and hash-match booleans without exposing file contents or diffs.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `PatchDiagnosticsSummary` now displays incomplete attempts and stuck executing approvals with safe identifiers, workspace/path, status, and hash-match state. The endpoint remains read-only and content-free. UI typecheck/build and API diagnostics tests remain part of the gate. External/source review remains pending.
