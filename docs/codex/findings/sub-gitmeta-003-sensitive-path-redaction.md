# SUB-GITMETA-003 Git Commit Metadata Sensitive Path Redaction

- Finding ID: SUB-GITMETA-003
- Severity: medium
- Area: git commit metadata
- Affected files/functions: apps/api/src/ithildin_api/read_tools.py `_ensure_relative_parts_not_sensitive`; apps/api/src/ithildin_api/read_tools.py `_safe_commit_path`; tests/test_read_tools.py `test_git_commit_metadata_redacts_private_key_and_credential_paths`
- Claim being tested: `git.show.commit_metadata` changed-file summaries should redact sensitive credential and private-key path names, not only hidden paths and obvious `secret` names.
- Observed behavior: Internal xhigh source review found that private-key and credential filenames such as `id_rsa`, `credentials.json`, and `private-key.pem` were not part of the sensitive-path classifier.
- Risk: Commit metadata could reveal sensitive file names even though file contents and raw diffs remain excluded.
- Recommended fix: Fixed by expanding the sensitive path classifier to include common credential/private-key names and markers, and adding a regression for private-key and credential changed paths.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `test_git_commit_metadata_redacts_private_key_and_credential_paths` verifies these paths are redacted and absent from serialized metadata. Existing `.env` and hidden-path redaction coverage remains green.
