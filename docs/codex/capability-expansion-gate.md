# Capability Expansion Gate v2

Task 153 adds `make capability-expansion-gate` as an explicit go/no-go check for new powerful tool
capabilities.

The gate is expected to report `decision: blocked` during the current v0.5 source-review phase. A
blocked result is healthy when the blockers are external-review closure or unfinished v0.5 tasks. The
command exits nonzero only when a hard invariant is violated, such as tool-surface drift or a changed
deferred-boundary list.

## Command

```sh
make capability-expansion-gate
uv run python scripts/capability_expansion_gate.py --json
```

Use `--require-allowed` only when intentionally checking whether a future capability expansion may
begin. Today, that form should fail.

## Hard Invariants

- tool count remains the approved local-preview set, including the bounded read-only
  `git.show.commit_metadata`, `git.show.ref_summary`, and `project.manifest.summary` additions;
- tool names remain the approved local-preview set;
- runtime boundary remains `v0.1 local-preview`;
- deferred-power list remains unchanged;
- structured reviewer findings validate with no open critical/high findings.

## Current Expected Result

Capability expansion remains blocked until external/source review rows are closed or accepted as
deferred and the remaining v0.5 planned tasks are complete. This gate does not approve new powers.
