# SUB-062 Release Dispatch Evidence Commands

- Finding ID: SUB-062
- Severity: low
- Area: release automation dispatch packet
- Affected files/functions: scripts/external_review_dispatch_packets.py; docs/codex/v0.6-external-review-assignment-matrix.md
- Claim being tested: Release-automation review packets should list the evidence commands reviewers need for validation.
- Observed behavior: Internal proxy review found that the release-automation packet omitted explicit `make release-evidence*` commands.
- Risk: Reviewers might not run the evidence schema and gate commands needed to validate packet claims.
- Recommended fix: Add `make release-evidence`, `make release-evidence-validate`, and `make release-evidence-gate` to release automation packet commands.
- Blocking status: later
- Disposition: fixed
- Verification notes: Release automation dispatch commands and assignment-matrix guidance now include the release-evidence command family. External/source review remains pending.
