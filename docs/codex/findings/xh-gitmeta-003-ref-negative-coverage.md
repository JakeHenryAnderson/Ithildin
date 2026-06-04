# XH-GITMETA-003 Git Metadata Ref Negative Coverage

- Finding ID: XH-GITMETA-003
- Severity: low
- Area: git commit metadata
- Affected files/functions: apps/api/src/ithildin_api/read_tools.py `_validate_commit_ref_selector`; tests/test_read_tools.py `test_git_commit_metadata_denies_unsupported_ref_syntax`; tests/test_read_tools.py `test_git_commit_metadata_denies_non_commit_object_id`
- Claim being tested: `git.show.commit_metadata` should reject revision operators, pathspec-like refs, remote refs, control characters, non-normalized refs, and non-commit object IDs.
- Observed behavior: Internal xhigh review found the source validator was strong, but focused tests covered only a smaller subset of the review prompt's denial cases.
- Risk: Future ref-validation drift could accidentally permit syntax that behaves like revision ranges, pathspecs, reflog lookups, or remote refs.
- Recommended fix: Fixed by adding explicit negative tests for revision/range/pathspec/search/remote/control/non-NFC refs and non-commit object IDs.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `test_git_commit_metadata_denies_unsupported_ref_syntax` and `test_git_commit_metadata_denies_non_commit_object_id` cover the added denial cases.
