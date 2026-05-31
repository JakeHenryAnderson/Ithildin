# SUB-003 Patch Apply Ancestor Symlink Race

- Finding ID: SUB-003
- Severity: high
- Area: patch apply filesystem race handling
- Affected files/functions: apps/api/src/ithildin_api/patches.py; PatchProposalService.apply_approved; _atomic_write_text
- Claim being tested: patch apply cannot be redirected outside the workspace after proposal validation and before final file replacement.
- Observed behavior: The prior final replacement helper accepted a resolved target path and checked only the immediate parent path before using path-string temp-file and replace operations. An ancestor directory swapped to a symlink after apply preparation could redirect the final write.
- Risk: A local race could turn the only approved write path into an out-of-workspace write despite earlier workspace validation.
- Recommended fix: Perform the final replace through verified directory file descriptors using no-follow directory walking from the workspace root, and add a regression for ancestor-directory symlink replacement before final write.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `_atomic_write_text` now walks workspace-relative path components with directory file descriptors and no-follow opens, verifies the target as a regular non-hardlinked file, writes a same-directory temporary file via `dir_fd`, and performs `os.replace` with source/destination directory fds. Regression tests cover immediate parent and ancestor symlink swaps before replace. External/source review remains pending.
