# Task 009 - Filesystem and Git Read Tools

## Goal

Implement safe read-only local tools.

## Tools

- `fs.list`
- `fs.stat`
- `fs.read`
- `fs.search`
- `git.status`
- `git.diff`
- `git.log`

## Acceptance Criteria

- All paths are canonicalized and scoped to allowed workspaces.
- Symlink escapes are denied.
- File size limits are enforced.
- Hidden/sensitive paths are denied by default policy.
- Git commands are read-only and cannot accept arbitrary flags.
- Tests cover traversal, symlink escape, large files, and denied paths.

