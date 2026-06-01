# SUB-028 External Response Area Binding

- Finding ID: SUB-028
- Severity: medium
- Area: release automation
- Affected files/functions: scripts/external_response_normalize.py; normalize_response; _extract_findings; _validate_finding_row; tests/test_release_readiness.py
- Claim being tested: A focused external review response for one lane cannot be normalized as closure-ready for a different lane.
- Observed behavior: Internal proxy review found that a --area patch-apply normalization run could accept an EXT-HTTP-### / http-fetch finding row and still report source rows as closeable. The normalizer validated the finding ID shape but did not bind the lane-specific namespace or row area to the requested area.
- Risk: An external response could be filed under the wrong review lane, making closure evidence ambiguous or misleading.
- Recommended fix: Add an area-to-namespace map, reject lane-specific finding IDs whose namespace does not match the requested area, and reject row areas that do not match the requested area.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: scripts/external_response_normalize.py now validates the requested area against known v0.6 lanes, checks lane-specific EXT namespaces, normalizes row areas, and rejects mismatches. Regression coverage is tests/test_release_readiness.py::test_external_response_normalization_binds_area_and_namespace.
