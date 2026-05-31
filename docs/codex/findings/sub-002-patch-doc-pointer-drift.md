# SUB-002 Patch Apply Dispatch Pointer Drift

- Finding ID: SUB-002
- Severity: informational
- Area: patch apply review packet/documentation pointers
- Affected files/functions: scripts/external_review_dispatch_packets.py; docs/codex/patch-apply-source-review-checklist.md
- Claim being tested: v0.6 dispatch packets and checklists point reviewers to implemented source files and functions.
- Observed behavior: The patch dispatch packet referenced `apps/api/src/ithildin_api/governed_tools.py`, which is not present, and the checklist referenced `ApprovalService.fail_execution` rather than the implemented `ApprovalService.complete_execution(..., success=False)` path.
- Risk: Reviewers could waste time chasing stale pointers or miss the actual governed call and failure-completion implementation.
- Recommended fix: Replace stale pointers with `apps/api/src/ithildin_api/tool_calls.py` and the implemented approval failure-completion method.
- Blocking status: later
- Disposition: fixed
- Verification notes: Updated the dispatch source pointer and patch apply checklist. Regenerating v0.6 dispatch packets will carry the corrected file/function references.
