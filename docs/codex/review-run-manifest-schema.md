# Review Run Manifest Schema

Review-run manifests record executed internal AI, external AI, human, or Codex source-review runs.
They live under ignored `var/review-runs/` and are validated with:

```sh
make review-run-manifest-check
```

The directory may be empty; an empty directory means no review runs have been executed yet.

## Required Fields

Each manifest file is named `review-run-*.json` and contains a JSON object with:

- `review_id`: stable run ID.
- `prompt_file`: repo-relative prompt or review packet path.
- `reviewer_type`: `codex_internal`, `internal_ai`, `external_ai`, or `human`.
- `reviewer_name`: model, person, or review role.
- `date`: ISO-like date or timestamp.
- `commit`: current source commit or prefix.
- `dirty`: current working-tree dirty state.
- `files_inspected`: non-empty list of repo-relative files/functions inspected.
- `tests_run`: non-empty list of commands or focused checks run.
- `output_file`: repo-relative review output file.
- `finding_count`: number of findings in this manifest.
- `severity_counts`: counts for `critical`, `high`, `medium`, `low`, and `informational`.
- `closure_matrix_rows_touched`: source-review closure matrix rows affected by the run.
- `findings`: optional list of finding summaries.

Finding IDs in review-run manifests use the v0.3/v0.4 execution namespace:
`V03-INT-PATCH-001`, `V03-EXT-HTTP-001`, or `V03-DOCS-001` style. Implementation findings must list
`files_functions`. Fixed or closed findings must include verification notes.

## Boundary

Review-run manifests are execution evidence, not external closure by themselves. Internal AI or
subagent manifests may create findings and update internal status, but they cannot close external
review rows.
