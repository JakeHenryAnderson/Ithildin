# SUB-037 Patch Output Binary Content

- Finding ID: SUB-037
- Severity: medium
- Area: filesystem
- Affected files/functions: apps/api/src/ithildin_api/patches.py; validate_unified_diff; PatchProposalService._prepare_apply; _atomic_write_text; tests/test_patch_proposals.py
- Claim being tested: Patch proposal/apply only supports UTF-8 text targets and cannot turn a text target into binary/NUL-containing content.
- Observed behavior: Internal proxy review found that a patch could add NUL bytes and still be proposed and applied because the existing target was checked as UTF-8 text, but patched output was not checked.
- Risk: Approval-gated patch apply could create binary-ish content despite the text-only local-preview contract.
- Recommended fix: Validate patched output before storage and immediately before writing, rejecting NUL bytes and invalid UTF-8.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: patched output is now validated through _ensure_safe_text_content during proposal validation, apply preparation, and atomic write. Regression coverage is included in tests/test_patch_proposals.py::test_invalid_diff_shapes_are_denied.
