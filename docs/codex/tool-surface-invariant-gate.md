# Tool-Surface Invariant Gate v2

Task 154 adds `make tool-surface-invariant-gate` to verify that Ithildin has not accidentally
expanded its governed tool surface.

## Command

```sh
make tool-surface-invariant-gate
uv run python scripts/tool_surface_invariant_gate.py --json
```

## Current Invariant

The local-preview tool surface remains the approved twelve tools:

- `fs.list`
- `fs.patch.apply`
- `fs.patch.propose`
- `fs.read`
- `fs.search`
- `fs.stat`
- `git.diff`
- `git.log`
- `git.show.commit_metadata`
- `git.show.ref_summary`
- `git.status`
- `http.fetch`

The gate fails if the lockfile tool names drift, the manifest count changes, or manifest text
references obvious deferred/broad powers such as shell, Docker, Kubernetes, browser, delete, chmod,
or archive behavior. It also parses the YAML manifests, checks the expected risk class for each
tool, verifies lockfile paths against the manifest directory, keeps `http.fetch` limited to the
single caller-controlled `url` field, keeps `git.show.commit_metadata` limited to structured ref
selectors with no caller-controlled Git argv, format strings, pathspecs, raw diffs, or file content,
and keeps `git.show.ref_summary` limited to selector/limit inputs with no caller-controlled names,
formats, remotes, refspecs, diffs, or stable ref-name hashes.

This gate is intentionally conservative. A future capability expansion must update the boundary
decision, manifest review, threat model, source-review closure matrix, and external review packet
before this invariant is relaxed.
