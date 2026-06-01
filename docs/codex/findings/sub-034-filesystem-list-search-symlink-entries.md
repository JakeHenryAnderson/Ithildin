# SUB-034 Filesystem List Search Symlink Entries

- Finding ID: SUB-034
- Severity: medium
- Area: filesystem
- Affected files/functions: apps/api/src/ithildin_api/read_tools.py; FilesystemReadTools.list_path; FilesystemReadTools.search; tests/test_read_tools.py
- Claim being tested: Symlink entries are denied or skipped consistently across filesystem list, stat, read, and search tools.
- Observed behavior: Internal proxy review found that list_path and search canonicalized traversal children before checking symlink status, so a symlink pointing to an allowed in-workspace file could appear as a duplicate real file.
- Risk: Symlink handling was inconsistent with the executor contract and could confuse review evidence.
- Recommended fix: Skip symlink entries before canonicalizing list/search traversal children.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: list_path and search now skip candidate symlinks before resolving relative paths or checking file status. Regression coverage is tests/test_read_tools.py::test_filesystem_list_and_search_skip_symlink_entries_inside_workspace.
