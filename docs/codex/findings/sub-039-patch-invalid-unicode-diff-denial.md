# SUB-039 Patch Invalid Unicode Diff Denial

- Finding ID: SUB-039
- Severity: medium
- Area: filesystem
- Affected files/functions: apps/api/src/ithildin_api/patches.py; PatchProposalService.create_proposal; _safe_utf8_bytes; tests/test_patch_proposals.py
- Claim being tested: Invalid Unicode in patch inputs produces a safe patch denial rather than an unhandled exception.
- Observed behavior: Internal proxy review found that unified_diff.encode("utf-8") could raise UnicodeEncodeError before conversion to PatchProposalError.
- Risk: A malformed patch input could escape the governed denial path and produce a less controlled server/runtime error.
- Recommended fix: Convert invalid UTF-8 encoding failures into PatchProposalError with a safe message.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: create_proposal now uses _utf8_size/_safe_utf8_bytes to convert encoding failures into PatchProposalError. Regression coverage is tests/test_patch_proposals.py::test_patch_proposal_rejects_invalid_unicode_diff.
