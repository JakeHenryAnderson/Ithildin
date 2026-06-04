# XH-GITMETA-004 Git Metadata Stable Hash Privacy Caveat

- Finding ID: XH-GITMETA-004
- Severity: low
- Area: git commit metadata
- Affected files/functions: apps/api/src/ithildin_api/read_tools.py `GitReadTools.commit_metadata`; docs/codex/v0.9-git-commit-metadata-implementation.md `Privacy Caveat`
- Claim being tested: Stable hashes for redacted emails and sensitive paths should not be mistaken for anonymity or external trust evidence.
- Observed behavior: Internal xhigh review noted that unsalted stable SHA-256 hashes of common emails or path names remain dictionary-guessable.
- Risk: Operators could overread local evidence hashes as privacy guarantees.
- Recommended fix: Fixed for local preview by documenting the privacy caveat and preserving redaction of raw email values and sensitive path names. Keyed or salted evidence hashes remain a future evidence-contract decision.
- Blocking status: later
- Disposition: fixed
- Verification notes: `docs/codex/v0.9-git-commit-metadata-implementation.md` now states stable email/path hashes are local evidence aids rather than anonymity guarantees.
