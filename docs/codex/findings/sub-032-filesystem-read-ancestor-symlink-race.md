# SUB-032 Filesystem Read Ancestor Symlink Race

- Finding ID: SUB-032
- Severity: medium
- Area: filesystem
- Affected files/functions: apps/api/src/ithildin_api/read_tools.py; FilesystemReadTools.read_file_bytes; FilesystemReadTools._open_no_follow_file; tests/test_read_tools.py
- Claim being tested: Filesystem reads do not open out-of-workspace content when an ancestor directory is swapped to a symlink after path validation.
- Observed behavior: Internal proxy review found that resolve_existing_path returned an already-resolved absolute path, while read_file_bytes opened that path directly with O_NOFOLLOW protecting only the final component. An ancestor directory swap could cause the process to open/read outside content before a later relative_path check failed the response.
- Risk: Even without returning content to the caller, the process could read an out-of-workspace file, weakening the workspace confinement claim.
- Recommended fix: Open read targets by walking from the workspace root with directory file descriptors and no-follow semantics for every path component.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: FilesystemReadTools.read_file_bytes now opens targets through _open_no_follow_file, which walks workspace-relative components from the workspace root using no-follow directory/file opens. Regression coverage is tests/test_read_tools.py::test_filesystem_read_denies_ancestor_symlink_swap_between_resolution_and_open.
