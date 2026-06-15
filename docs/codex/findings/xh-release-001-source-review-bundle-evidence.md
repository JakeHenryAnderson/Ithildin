# XH-RELEASE-001 Release Summary Source-Review Bundle Evidence

- Finding ID: XH-RELEASE-001
- Severity: medium
- Area: project release summary
- Affected files/functions: scripts/project_release_summary_source_review_bundle.py `build_bundle`; tests/test_release_readiness.py `test_project_release_summary_source_review_bundle_builds_from_fixture`
- Claim being tested: The `project.release.summary` source-review bundle should provide enough implementation source, focused tests, manifest/policy evidence, and gate output for a source reviewer to assess the implemented lane.
- Observed behavior: Internal review found the bundle had proposal, plan, boundary, fixture, negative-transcript, handoff, and gate evidence artifacts, but did not include a source bundle or focused test bundle even though the handoff text asks reviewers to inspect implementation source and tests.
- Risk: Reviewers could receive a packet that is coherent as process evidence but insufficient for source-level assessment, causing false confidence or extra manual reconstruction work.
- Recommended fix: Fixed by adding source and focused test bundles to the generated source-review packet and updating packet tests to assert the implementation, manifest, policy parity fixture, and focused test files are included.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `make project-release-summary-source-review-bundle` generates source and test bundles, and `tests/test_release_readiness.py::test_project_release_summary_source_review_bundle_builds_from_fixture` validates the added artifacts.
