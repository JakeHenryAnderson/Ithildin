# XH-GITTAG-002 Git Tag Metadata Resource Parity

- Finding ID: XH-GITTAG-002
- Severity: low
- Area: git tag metadata
- Affected files/functions: apps/api/src/ithildin_api/policy_parity.py `PolicyParityCase.expect_resource_fields`; policies/tests/parity.yaml `git_tag_metadata_preview_matches_runtime`
- Claim being tested: Policy preview and runtime should agree on the normalized `git_tags` resource, including `selector_kind`.
- Observed behavior: Internal High review found the committed parity fixture asserted resource type and scope but did not assert `selector_kind`, so preview/runtime selector normalization drift would be easier to miss.
- Risk: Future resource-construction changes could weaken tag selector evidence while the parity fixture still passes on type and scope alone.
- Recommended fix: Fixed by extending the policy-parity harness with `expect_resource_fields` and asserting `selector_kind: all_local_tags` for `git.show.tag_metadata` against both preview and runtime execution-started resource evidence.
- Blocking status: later
- Disposition: fixed
- Verification notes: `make policy-parity` now validates the expected `selector_kind` field for the `git_tags` resource.
