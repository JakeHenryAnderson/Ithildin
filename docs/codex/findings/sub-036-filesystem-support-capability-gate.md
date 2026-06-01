# SUB-036 Filesystem Support Capability Gate

- Finding ID: SUB-036
- Severity: medium
- Area: filesystem
- Affected files/functions: apps/api/src/ithildin_api/filesystem_contract.py; collect_filesystem_contract_status; tests/test_filesystem_contract_check.py
- Claim being tested: Supported filesystem status means the documented local-preview platform and required filesystem capability evidence are present.
- Observed behavior: Internal proxy review found that supported status required macOS/Linux and O_NOFOLLOW, but did not require successful symlink and hardlink probes even though the contract relies on normal symlink/hardlink behavior.
- Risk: A degraded host could be displayed as supported, reducing the usefulness of /system/status and release evidence warnings.
- Recommended fix: Treat missing symlink or hardlink capability evidence as degraded rather than supported.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: collect_filesystem_contract_status now requires O_NOFOLLOW, symlink support, and hardlink support for local-preview security-supported status. Regression coverage is tests/test_filesystem_contract_check.py::test_supported_platform_without_symlink_or_hardlink_probe_is_degraded.
