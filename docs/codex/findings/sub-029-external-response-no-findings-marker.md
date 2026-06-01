# SUB-029 External Response No-Findings Marker

- Finding ID: SUB-029
- Severity: medium
- Area: release automation
- Affected files/functions: scripts/external_response_normalize.py; _extract_findings; _has_explicit_no_findings_statement; tests/test_release_readiness.py
- Claim being tested: A malformed or non-finding review response cannot silently normalize to zero findings unless the reviewer explicitly states that there are no findings.
- Observed behavior: Internal proxy review found that responses without a valid finding table could normalize to finding_count: 0. The focused review prompt requires explicit no-findings language, but the normalizer did not enforce it.
- Risk: Malformed review output could be mistaken for a clean review result.
- Recommended fix: Require either at least one valid finding row or an explicit no-findings marker such as No findings.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: The normalizer now rejects responses with neither valid findings nor explicit no-findings language. Regression coverage is tests/test_release_readiness.py::test_external_response_normalization_requires_findings_or_explicit_none.
