# Enterprise Response Waiting Room

Status: read-only raw-response waiting-room summary for `ERG-003` and `ERG-002`.

Current governed tool count: `24`.

Run:

```sh
make enterprise-response-waiting-room
```

This command inspects the ignored raw-response placeholder files under
`var/review-runs/enterprise-dual-response-inbox/` and reports whether each lane is still waiting,
looks populated, is missing, or is invalid. It is the small operator check between "I sent the review
packet" and "I pasted a response and should run `make enterprise-response-paste-preflight`."

Possible lane states:

- `placeholder`: the raw-response file still appears to be the generated placeholder.
- `candidate_response`: the raw-response file appears populated and should go through paste
  preflight before any normalizer runs.
- `missing`: the raw-response file is absent or empty.
- `invalid`: the raw-response path is not a regular UTF-8 file.
- `too_large`: the raw response exceeds the paste-preflight size bound.

If a lane reports `candidate_response`, run the lane-specific command printed by the waiting-room
output, or use:

```sh
make enterprise-response-paste-preflight
```

for deterministic docs/wiring validation before running the lane-specific preflight command with
`--lane` and `--raw-response`.

For a compact receive-side command summary, run:

```sh
make enterprise-response-now
```

It prints the current lane state plus the exact paste-preflight, normalizer, dry-run, and closure-gate
commands without running them.

## What This Proves

- The ignored raw-response path exists, is missing, or still appears to be a placeholder.
- A populated raw-response file is ready for the separate paste-preflight check.
- The response-handling boundary remains read-only at this step.

## What This Does Not Prove

This command does not normalize responses, does not write response files, does not record external review,
does not mutate findings, does not close either lane, and does not approve runtime behavior,
Mission Control runtime importer behavior, live VM/container inspection, local model invocation,
sandbox orchestration, trusted-host promotion, SIEM adapters, compliance automation,
public/security-product positioning, or new governed tool powers.
