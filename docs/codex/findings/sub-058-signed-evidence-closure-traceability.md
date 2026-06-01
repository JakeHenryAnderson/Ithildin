# SUB-058 Signed Evidence Closure Traceability

- Finding ID: SUB-058
- Severity: medium
- Area: source review closure matrix
- Affected files/functions: docs/codex/source-review-closure-matrix.md; docs/codex/v0.6-internal-review-execution-wave-2.md
- Claim being tested: Signed-evidence closure rows should reference the full internal finding trail before external handoff.
- Observed behavior: Internal proxy review found signed-evidence closure rows were stale relative to `SUB-010` through `SUB-014` and did not yet mention the latest signed-evidence recheck findings.
- Risk: Reviewers could miss which signed-evidence issues were fixed internally and which rows still require external review.
- Recommended fix: Update closure matrix and lane notes to include both historical and current signed-evidence finding ranges with fixed-commit/test evidence.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: Signed-evidence closure rows and lane notes now reference the expanded finding trail and remain external-pending. External/source review remains pending.
