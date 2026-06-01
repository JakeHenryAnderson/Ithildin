# SUB-075 Review Console Copy Evidence Parity

- Finding ID: SUB-075
- Severity: low
- Area: review console/admin boundary
- Affected files/functions: apps/ui/src/App.tsx; ApprovalEvidence; copyApprovalEvidence
- Claim being tested: review-console evidence exports should match the approval-binding verdict shown to the local admin.
- Observed behavior: the Binding Evidence copy action exported approval scope and metadata, but omitted the derived review validity, checks, reasons, and proposal review that drive the UI's approve/attention state.
- Risk: a reviewer comparing copied evidence with UI-visible approval state could miss why a stale or drifted approval was disabled.
- Recommended fix: Include a safe `review_summary` in copied approval evidence without adding file contents, diffs, secrets, or mutation controls.
- Blocking status: later
- Disposition: fixed
- Verification notes: `copyApprovalEvidence` now includes `review_summary.valid`, `checks`, `reasons`, and `proposal` when approval review data is available. The copy action remains client-side evidence export only and does not add new API calls or execution controls. UI typecheck/build and release gates remain required; external/source review remains pending.
