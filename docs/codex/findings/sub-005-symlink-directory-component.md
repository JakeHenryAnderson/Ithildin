# SUB-005 Symlink Directory Component Accepted

- Finding ID: SUB-005
- Severity: medium
- Area: filesystem path resolution
- Affected files/functions: apps/api/src/ithildin_api/read_tools.py; FilesystemReadTools.resolve_existing_path
- Claim being tested: filesystem tools deny symlink paths rather than relying on resolved destination safety.
- Observed behavior: The prior resolver checked whether the final target path was a symlink, but a symlinked directory component that resolved back inside the workspace could be accepted.
- Risk: This weakened the documented symlink-denial contract and made path reasoning less reviewable across reads and patch proposal/apply preparation.
- Recommended fix: Reject symlinks in every requested path component before resolving the target.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `resolve_existing_path` now checks every requested component for symlinks before strict resolution. Tests cover a symlinked directory component that points inside the workspace. External/source review remains pending.
