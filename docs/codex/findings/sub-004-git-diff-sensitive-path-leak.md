# SUB-004 Git Diff Sensitive Path Leak

- Finding ID: SUB-004
- Severity: high
- Area: git read tools sensitive-path enforcement
- Affected files/functions: apps/api/src/ithildin_api/read_tools.py; GitReadTools.diff
- Claim being tested: read tools do not expose hidden or sensitive workspace paths such as `.env` or `secrets`.
- Observed behavior: `git.diff` returned raw git diff output for the repository. If a tracked hidden or sensitive path such as `.env` changed, the diff could include that path and content even though filesystem reads deny it.
- Risk: A governed read-only git tool could bypass the filesystem sensitive-path policy and leak local secret material from tracked files.
- Recommended fix: Parse diff path metadata and fail closed when any diff path is hidden, sensitive, absolute, or traversal-like.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `GitReadTools.diff` now scans diff path headers before returning output and rejects hidden/sensitive or unsafe paths. Tests cover a tracked `.env` diff denial. External/source review remains pending.
