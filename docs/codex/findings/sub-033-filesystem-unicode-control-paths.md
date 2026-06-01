# SUB-033 Filesystem Unicode Control Paths

- Finding ID: SUB-033
- Severity: medium
- Area: filesystem
- Affected files/functions: apps/api/src/ithildin_api/read_tools.py; _reject_ambiguous_path_input; tests/test_read_tools.py
- Claim being tested: Ambiguous path inputs with control or formatting characters are denied before filesystem access.
- Observed behavior: Internal proxy review found that C1 Unicode controls such as U+0085 were accepted because the filter rejected only C0 controls and DEL.
- Risk: Ambiguous path strings could be accepted despite the documented control-character denial.
- Recommended fix: Reject Unicode Cc, Cf, and Cs path characters in addition to C0 and DEL.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: _reject_ambiguous_path_input now rejects Unicode control, format, and surrogate categories. Regression coverage includes U+0085 and U+202E in tests/test_read_tools.py::test_filesystem_denies_control_character_paths.
