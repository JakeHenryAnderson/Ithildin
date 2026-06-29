# Validation Performance And Gate Tiers

Status: development-speed guide for choosing the smallest honest validation gate.

Ithildin keeps `make release-check` and `make review-candidate` as full gates. Those commands are
allowed to be slow because they rebuild release evidence, generated packets, external-review
handoff artifacts, and broad readiness checks.

Normal development should not need to rebuild every generated review packet after every small docs,
test, or wiring change. Use the tiers below so validation cost matches change risk.

## Gate Tiers

### Validation Plan

Run:

```sh
make validation-plan
```

Use this before picking a gate when the dirty tree spans several areas. It classifies changed files
and recommends the smallest honest command set. You can also pass files directly:

```sh
uv run python scripts/validation_plan.py docs/codex/example.md scripts/example.py
```

To run the recommended command set directly:

```sh
make smart-check
```

`smart-check` prints the same file/category plan, runs the recommended commands, and records
per-command elapsed time plus a short failure tail when a command fails. It is the default
development-loop command when you are not preparing a release or review handoff. It avoids
recommending duplicate sub-gates: for example, docs/process changes run `readiness-check`, not
`quick-check` followed by `readiness-check`, because `readiness-check` already includes the quick
gate.

### Validation Timing

Run:

```sh
make validation-timing
```

Use this when the fast development loop starts to feel slow. It times the fast profile and prints
per-command elapsed seconds. For a no-execute preview, run:

```sh
uv run python scripts/validation_timing.py --dry-run
```

### Quick Check

Run:

```sh
make quick-check
```

Use this for small docs, bookkeeping, script wiring, and manager-owned cleanup where no runtime,
manifest, policy, API/MCP, approval/audit, or UI behavior changed.

This runs core boundary checks, lint, and typecheck. It does not generate review packets.

### Readiness Check

Run:

```sh
make readiness-check
```

Use this before committing release-readiness/docs/process changes that touch Make targets, review
docs, generated-artifact wiring, or release guardrails.

This runs `quick-check`, docs generation, and a curated release/docs smoke set. It does not walk the
entire release-readiness suite, because many of those tests intentionally regenerate review packets.

### Release Check

Run:

```sh
make release-check
```

Use this before meaningful capability/runtime commits, before source-review handoff, after changing
release gates, and before declaring the repo ready for the next review phase.

This remains the full local release gate.

### Review Candidate

Run:

```sh
make review-candidate
```

Use this when generating a reviewer/operator handoff packet.

This remains the full packet-generation gate.

## Slow Packet Tests

Release-readiness tests whose names indicate generated packets, bundles, handoffs, external-review
artifacts, response kits, Mission Control packets, sandbox/VM packets, observed demos, or review
candidates are automatically marked `slow_packet` by `tests/conftest.py`.

The marker does not remove tests from the full suite. It lets developers manually avoid recursive
packet generation when investigating release-readiness tests:

```sh
uv run pytest tests/test_release_readiness.py -m "not slow_packet" -q
```

## Rule Of Thumb

- Runtime, executor, manifest, policy, approval/audit, or API/MCP changes: run focused subsystem
  tests, then `make release-check`.
- UI runtime changes: run UI tests/build plus relevant API/readiness tests.
- Docs/process/review wiring changes: run `make readiness-check`, plus the focused test for the
  specific script/doc you touched.
- Tiny mechanical docs edits: run `make quick-check` plus any touched focused test.
- External-review handoff: run `make review-candidate`.

Do not use fast gates to claim release readiness. Fast gates are a development accelerator, not a
replacement for the full review/release gates.
