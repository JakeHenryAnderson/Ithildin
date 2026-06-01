# SUB-045 HTTP Closure Traceability

- Finding ID: SUB-045
- Severity: medium
- Area: source review closure matrix
- Affected files/functions: docs/codex/source-review-closure-matrix.md; docs/codex/v0.6-milestone-manifest.md; docs/codex/v0.6-milestone-manifest.json; scripts/closure_matrix_evidence_sync.py
- Claim being tested: A remediated internal proxy lane should identify remediation commits and concrete verification commands without implying external closure.
- Observed behavior: Internal proxy review found that the HTTP v3 closure row said findings were fixed but still listed `Fixed commit` as `pending` and used generic verification text.
- Risk: Traceability was weaker than the patch and filesystem rows, making it harder to bind HTTP remediation to exact commits and tests.
- Recommended fix: Record HTTP remediation commits or current remediation commit placeholders, strengthen verification text, and make the sync gate flag fixed rows whose fixed-commit field remains `pending`.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: The HTTP closure row now names prior and current HTTP remediation commits, uses focused HTTP verification commands, and `closure_matrix_evidence_sync` rejects rows that say findings are fixed while `Fixed commit` remains `pending`. External/source review remains pending.
