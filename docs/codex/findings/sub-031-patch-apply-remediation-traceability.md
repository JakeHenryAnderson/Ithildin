# SUB-031 Patch Apply Remediation Traceability

- Finding ID: SUB-031
- Severity: low
- Area: release automation
- Affected files/functions: docs/codex/v0.6-milestone-manifest.md; docs/codex/v0.6-milestone-manifest.json; docs/codex/source-review-closure-matrix.md
- Claim being tested: Controlling review documents identify the exact patch-apply remediation baseline before being used as closure or handoff evidence.
- Observed behavior: Internal proxy review found that the generated patch-apply packet was correctly bound to commit 15e1fb5dff7dc9e2a365154d90604810f7368ac4, but controlling docs still used placeholder wording such as remediation commit TBD or plus follow-up remediation commit.
- Risk: Reviewers could see stale baseline wording and misinterpret which code state contains the patch apply remediation.
- Recommended fix: Update the milestone manifest and closure matrix to identify the exact remediation baseline and proxy-review follow-up commit bf23a15952b940d6dd1987c5f36219fba586d322.
- Blocking status: later
- Disposition: fixed
- Verification notes: The v0.6 manifest and closure matrix now point to the patch-apply remediation baseline 15e1fb5dff7dc9e2a365154d90604810f7368ac4 and proxy-review follow-up bf23a15952b940d6dd1987c5f36219fba586d322 rather than leaving placeholders.
