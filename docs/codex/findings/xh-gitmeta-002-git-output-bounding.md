# XH-GITMETA-002 Git Metadata Output Bounding

- Finding ID: XH-GITMETA-002
- Severity: medium
- Area: git commit metadata
- Affected files/functions: apps/api/src/ithildin_api/read_tools.py `GitReadTools._run_git`; apps/api/src/ithildin_api/read_tools.py `GitReadTools._commit_identity_metadata`; tests/test_read_tools.py `test_git_output_is_bounded`; tests/test_read_tools.py `test_git_commit_metadata_sanitizes_identity_separator_and_hides_email`
- Claim being tested: Git metadata subprocess output and returned identity metadata should remain bounded without materializing unbounded output.
- Observed behavior: Internal xhigh review found `_run_git` used `capture_output=True` and truncated after process completion, while identity names were sanitized but not separately capped.
- Risk: Large repository metadata could be materialized before Ithildin applies output limits, and unusually long identity strings could exceed review-friendly bounds.
- Recommended fix: Fixed by reading Git stdout incrementally up to `max_output_bytes + 1`, killing/truncating safely when the bound is exceeded, discarding stderr, and capping sanitized identity names.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `test_git_output_is_bounded` exercises bounded Git output, and `test_git_commit_metadata_sanitizes_identity_separator_and_hides_email` verifies sanitized identity names remain capped.
