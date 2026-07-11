# Review Run Manifest Schema

Review-run manifests record executed internal AI, external AI, human, or Codex source-review runs.
They live under ignored `var/review-runs/` and are validated with:

```sh
make review-run-manifest-check
```

Review-run manifests have two provenance bindings:

- `historical` preserves the commit and dirty state that the reviewer actually inspected. The
  validator requires the recorded commit to exist in repository history but never rewrites or
  compares it to current `HEAD`.
- `current_candidate` binds a review to exact current `HEAD`, current dirty state, and a
  deterministic `tree_fingerprint` covering `HEAD`, domain-separated index and worktree diffs,
  untracked paths and bytes, symlink targets, and file modes. Staging the same content changes the
  fingerprint because index and unstaged state are bound independently.

Manifests created before this distinction and lacking `binding` are interpreted as `historical` so
their provenance remains immutable. New manifests must state their binding explicitly.

When a current-candidate commit or working tree changes, detect the stale binding with:

```sh
make review-run-manifest-refresh
```

The compatibility target never rewrites an executed review, even with its retained `--write` flag.
A stale current-candidate record requires a fresh review and a new manifest; it cannot be repaired
by retargeting the reviewer, date, findings, or output to new bytes. The command does not modify
historical manifests and does not grant approval, closure, or release authority.

The directory may be empty; an empty directory means no review runs have been executed yet.

## Required Fields

Each manifest file is named `review-run-*.json` and contains a JSON object with:

- `review_id`: stable run ID.
- `prompt_file`: repo-relative prompt or review packet path.
- `reviewer_type`: `codex_internal`, `internal_ai`, `external_ai`, or `human`.
- `reviewer_name`: model, person, or review role.
- `date`: ISO-like date or timestamp.
- `binding`: `historical` or `current_candidate`; omitted legacy values mean `historical`.
- `commit`: the commit actually reviewed. Historical bindings allow an existing 7-to-40-character
  commit identifier; current-candidate bindings require exact full current `HEAD`.
- `dirty`: working-tree state observed by the review. It is immutable history for `historical` and
  must match the current tree for `current_candidate`.
- `tree_fingerprint`: required only for `current_candidate`; a `sha256:` digest over the exact
  current commit plus staged, unstaged, and untracked tree state.
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

Changing any executed manifest's commit, dirty state, or tree fingerprint would misattribute an
older review to new source and is prohibited. A changed candidate requires a fresh
`current_candidate` review manifest. The compatibility refresh command reports staleness and fails
closed; it does not update binding metadata or imply that review occurred.
