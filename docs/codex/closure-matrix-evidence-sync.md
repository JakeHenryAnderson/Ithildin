# Closure Matrix Evidence Sync

Task 167 adds `make closure-matrix-evidence-sync` to keep the v0.5 milestone manifest and source
review closure matrix aligned.

## Command

```sh
make closure-matrix-evidence-sync
uv run python scripts/closure_matrix_evidence_sync.py --json
```

The gate verifies:

- every completed v0.5 task has a `Task ###` reference in
  [source-review-closure-matrix.md](source-review-closure-matrix.md);
- v3 closure rows have verification commands;
- closure states use the documented state vocabulary;
- rows do not claim external closure while external review remains pending.

The gate is included in `make release-check`. It does not close external rows and does not approve
capability expansion; it only prevents evidence/status drift.
