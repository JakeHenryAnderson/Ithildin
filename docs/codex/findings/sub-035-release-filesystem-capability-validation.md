# SUB-035 Release Filesystem Capability Validation

- Finding ID: SUB-035
- Severity: medium
- Area: release automation
- Affected files/functions: scripts/release_evidence.py; validate_release_evidence_snapshot; tests/test_release_readiness.py
- Claim being tested: Release evidence validation requires the filesystem capability evidence that the generated snapshot and executor contract depend on.
- Observed behavior: Internal proxy review found that release evidence validation accepted filesystem evidence with support/probe fields but without platform, Python, or capability details.
- Risk: A release evidence JSON could claim filesystem support without carrying the O_NOFOLLOW, symlink, hardlink, and case-sensitivity facts needed by reviewers.
- Recommended fix: Require filesystem platform, Python version, and capability fields in release evidence validation.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: validate_release_evidence_snapshot now requires platform, python, and capability evidence. Regression coverage is tests/test_release_readiness.py::test_release_evidence_schema_validator_requires_filesystem_capabilities and tests/test_release_readiness.py::test_release_evidence_schema_validator_requires_o_no_follow_evidence.
