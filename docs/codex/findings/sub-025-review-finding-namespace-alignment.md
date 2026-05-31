# SUB-025 Review Finding Namespace Alignment

- Finding ID: SUB-025
- Severity: medium
- Area: release automation
- Affected files/functions: scripts/reviewer_findings.py; FINDING_ID_PATTERN; review-run documentation
- Claim being tested: reviewer finding namespaces should be accepted consistently by docs, validators, and review-run tooling.
- Observed behavior: v0.6 review-run namespace examples could use IDs that the reviewer finding validator rejected.
- Risk: Valid internal review findings could fail ingestion or be silently re-labeled outside the documented review process.
- Recommended fix: Align the reviewer finding validator with the documented namespace convention.
- Blocking status: later
- Disposition: fixed
- Verification notes: The reviewer finding ID validator now accepts the existing ISR/EXT/SUB/AI forms plus `V03-INT-*`, `V03-EXT-*`, and `V03-DOCS-*` namespaced findings. Existing reviewer-finding validation remains in the release-readiness suite. External/source review remains pending.
