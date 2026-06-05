# No-New-Powers Guardrail v2

Task 170 adds `make no-new-powers-guardrail`, an executable check that v0.5 review-closure work has not
expanded Ithildin's governed tool powers.

## Command

```bash
make no-new-powers-guardrail
uv run python scripts/no_new_powers_guardrail.py --json
```

## What It Checks

- The governed tool list remains the approved local-preview tool set, including the bounded v0.9
  read-only `git.show.commit_metadata` and `git.show.ref_summary` additions.
- The runtime boundary remains `v0.1 local-preview`.
- The deferred-power list is unchanged.
- No manifest introduces shell, Docker, Kubernetes, browser, secrets, broad-write, broad-network, or
  arbitrary-command semantics.
- `http.fetch` remains GET-only by manifest shape: a URL-only input schema with no caller headers, body,
  method, cookies, or proxy controls.
- `git.show.commit_metadata` remains read-only by manifest shape: structured ref selectors only, no
  caller-controlled Git argv, format strings, pathspecs, raw diffs, or file contents.
- `git.show.ref_summary` remains read-only by manifest shape: selector/limit inputs only, no caller
  supplied ref names, format strings, remotes, refspecs, raw diffs, or file contents.
- `fs.patch.apply` and `fs.patch.propose` remain the only write/write-proposal tools.

## Current Expected Result

The guardrail should pass and report `new_power_classes_allowed: false`. Passing means the current review
track preserved the boundary; it does not approve new powers.
