# XH-GITMETA-001 Git Metadata Packet Hash Traceability

- Finding ID: XH-GITMETA-001
- Severity: medium
- Area: git commit metadata
- Affected files/functions: scripts/git_commit_metadata_source_review_bundle.py `build_bundle`; tests/test_release_readiness.py `test_git_commit_metadata_source_review_bundle_is_wired`
- Claim being tested: The git metadata source-review packet should bind prompt/index/intake hash references to the exact bytes written for the implementation packet.
- Observed behavior: Internal xhigh review found the packet index, prompt, and intake commands cited a pre-normalization implementation-packet hash that did not match the generated artifact hash.
- Risk: Reviewers could not reliably bind the packet text to the exact implementation packet artifact.
- Recommended fix: Fixed by normalizing packet text before computing the implementation-packet hash and adding a release-readiness assertion that displayed hashes match the artifact hash manifest.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `test_git_commit_metadata_source_review_bundle_is_wired` verifies the implementation packet hash in the index, prompt, and intake command matches `git-commit-metadata-source-review-artifact-hashes.json`.
