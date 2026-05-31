# Filesystem Source Review Checklist

Task 160 creates the source-review checklist for workspace-scoped filesystem behavior. Use it with
[source-review-runbook-v2.md](source-review-runbook-v2.md),
[source-file-inspection-packet.md](source-file-inspection-packet.md), and
[filesystem-executor-contract.md](filesystem-executor-contract.md).

## Files And Functions

Inspect:

- `apps/api/src/ithildin_api/read_tools.py`
  - `FilesystemReadTools.resolve_existing_path`
  - `FilesystemReadTools.list_path`
  - `FilesystemReadTools.stat_path`
  - `FilesystemReadTools.read_file`
  - `FilesystemReadTools.search`
  - `FilesystemReadTools.read_text_file`
  - `FilesystemReadTools.read_file_bytes`
  - `FilesystemReadTools._ensure_under_workspace`
  - `FilesystemReadTools._ensure_not_sensitive`
  - `FilesystemReadTools._ensure_not_hardlinked_file`
  - `_reject_ambiguous_path_input`
- `apps/api/src/ithildin_api/patches.py`
  - `PatchProposalService.create_proposal`
  - `PatchProposalService._prepare_apply`
  - `validate_unified_diff`
  - `_reject_unsupported_diff_features`
  - `_atomic_write_text`
- `apps/api/src/ithildin_api/filesystem_contract.py`
  - platform and capability evidence helpers

## Claims To Test

- Caller paths are relative only; absolute paths, traversal, encoded traversal, NUL/control
  ambiguity, and Unicode normalization ambiguity fail closed.
- Resolved targets remain under the configured workspace root.
- Hidden paths, sensitive names, `.git` internals, symlinks, hardlinks, directories-as-files, binary
  targets, invalid encodings, and oversized files are denied safely.
- Reads and searches enforce byte/result limits and do not leak blocked file contents in errors.
- Patch proposal/apply target validation inherits the same workspace path safety model.
- Race-like target replacement between validation and read/propose/apply preparation fails closed or
  is diagnosed according to the local-preview contract.
- macOS and Linux are the only security-supported local-preview profiles; Windows/WSL remain unsupported/untested for workspace/race security claims.

## Evidence Commands

```sh
make filesystem-contract-check
uv run pytest tests/test_read_tools.py tests/test_patch_proposals.py tests/test_security_regressions.py
make release-check
```

## Finding Prompts

For every issue, record:

- the path form or race condition being tested;
- whether a file outside the workspace could be read, proposed, or written;
- whether the failure leaks file contents, diff contents, secrets, or host paths beyond safe
  metadata;
- whether the issue is platform-specific and whether it changes the macOS/Linux support claim.

## Non-Goals

This checklist does not claim kernel sandboxing, host-compromise resistance, Windows/WSL security
support, broad filesystem writes, delete/move/chmod/archive support, or protection from every
possible OS-level race.
