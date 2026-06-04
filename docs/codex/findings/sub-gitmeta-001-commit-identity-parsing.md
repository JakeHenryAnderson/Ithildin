# SUB-GITMETA-001 Commit Identity Parsing And Privacy

- Finding ID: SUB-GITMETA-001
- Severity: high
- Area: git commit metadata
- Affected files/functions: apps/api/src/ithildin_api/read_tools.py `GitReadTools._commit_identity_metadata`; apps/api/src/ithildin_api/read_tools.py `GitReadTools._commit_format_field`; tests/test_read_tools.py `test_git_commit_metadata_sanitizes_identity_separator_and_hides_email`
- Claim being tested: `git.show.commit_metadata` should not parse untrusted Git identity metadata with in-band separators or leak raw email values when `include_emails=false`.
- Observed behavior: Internal xhigh source review found that the first implementation parsed all identity fields from one `git show` record separated with `%x1f`. A malicious author or committer name containing the same separator could confuse field boundaries, and email-like text embedded in names was not redacted.
- Risk: A crafted commit identity could weaken metadata parsing integrity or expose email-like values through the name field even when email output was disabled.
- Recommended fix: Fixed by reading fixed Git format fields separately, validating timestamp fields, sanitizing author/committer names, redacting email-like substrings in names, and adding a regression with a separator-bearing identity.
- Blocking status: blocking
- Disposition: fixed
- Verification notes: `test_git_commit_metadata_sanitizes_identity_separator_and_hides_email` verifies separator-bearing names are sanitized and raw author/committer emails are absent. Focused read-tool tests and git metadata integration tests pass.
