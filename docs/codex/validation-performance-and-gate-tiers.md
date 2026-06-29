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

For an operator-friendly decision summary with the current mode, deferred handoff commands, and
release-check slice suggestions, run:

```sh
make validation-decision
```

or pass a hypothetical file set through Make:

```sh
make validation-decision ARGS=apps/api/src/ithildin_api/tools/example.py
```

To run the recommended command set directly:

```sh
make smart-check
```

`smart-check` prints the same file/category plan, runs the recommended commands, and records
per-command elapsed time plus a short failure tail when a command fails. It is the default
development-loop command when you are not preparing a release or review handoff. It avoids
recommending duplicate sub-gates: for example, mixed docs/process changes run `readiness-check`, not
`quick-check` followed by `readiness-check`, because `readiness-check` already includes the quick
gate. Pure docs/README/AGENTS edits run the narrower `docs-check` gate.

By default, `smart-check` reports slow release/review gates as deferred handoff commands instead of
running them. That keeps routine development from paying the full generated-packet and release-gate
cost after every small change. When you want the same dirty-file-aware plan plus slow handoff gates,
run:

```sh
make smart-handoff-check
```

or:

```sh
uv run python scripts/validation_plan.py --include-release --run
```

### Validation Timing

Run:

```sh
make validation-timing
```

Use this when the fast development loop starts to feel slow. It times the fast profile and prints
per-command elapsed seconds plus a profile budget status. The default fast profile measures
`make smart-check`, because that is the normal dirty-file-aware development gate. Budget overruns
are informational by default so performance drift is visible without breaking ordinary development.
To turn a timing budget into a failing gate for a local investigation, use `--fail-on-budget`.

Examples:

```sh
uv run python scripts/validation_timing.py --dry-run
uv run python scripts/validation_timing.py --profile docs
uv run python scripts/validation_timing.py --profile readiness --budget-seconds 300
uv run python scripts/validation_timing.py --command "make enterprise-response-paste-preflight" --budget-seconds 10 --fail-on-budget
```

### Release Check Profile

Run:

```sh
make release-check-profile
```

Use this before assuming `make release-check` is hung or unexpectedly slow. It parses the Makefile
and reports the static `release-check` prerequisite graph, largest target categories, duplicate
targets, and whether the full Python test, UI build, and docs-site targets are present. It does not
run the release gate and is not release proof; it is a fast explanation tool for planning which
focused command or packet lane deserves attention next.

To inspect one category from that graph, run:

```sh
make release-check-slice ARGS="--category enterprise"
```

To infer relevant slices from the current dirty file set, run:

```sh
make release-check-impact
```

You can also pass explicit paths:

```sh
make release-check-impact ARGS="docs/codex/enterprise-response-status-board.md scripts/enterprise_response_status_board.py"
```

This is plan-only by default. To intentionally execute only that category, run:

```sh
make release-check-slice ARGS="--category enterprise --run"
```

Slice runs are focused development evidence, not full release proof. Use them to debug a slow or
failing lane before returning to `make release-check` for a release, handoff, or major checkpoint.

### Docs Check

Run:

```sh
make docs-check
```

Use this for pure docs, README, or AGENTS edits where no scripts, tests, config, runtime source,
manifests, policy, UI, review-packet outputs, or generated artifacts changed.

This runs release wording guardrails, the curated review-doc/docs-site smoke tests, and docs-site
generation. It intentionally skips lint and typecheck because there is no code surface in a pure
docs edit. Mixed docs plus scripts/config/tests still route to `readiness-check`.

### Quick Check

Run:

```sh
make quick-check
```

Use this for small docs, bookkeeping, script wiring, and manager-owned cleanup where no runtime,
manifest, policy, API/MCP, approval/audit, or UI behavior changed.

This runs core boundary checks, lint, and typecheck. It does not generate review packets.

### Fast Python Tests

Run:

```sh
make test-fast
```

Use this for runtime iteration when generated packet tests are not the thing under review. It runs
the Python suite with `slow_packet` tests excluded, so executor/API regressions still get broad
coverage without walking every review-packet generator. `make test` remains the full Python test
suite and is still part of release proof.

### Runtime Check

Run:

```sh
make runtime-check
```

Use this for backend/runtime iteration before broader Python or release gates. It runs the focused
core API, governed-tool, read-tool, security-regression, tool-registry, and policy-parity tests that
catch the highest-risk runtime regressions without traversing review-packet machinery.

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
  tests with `make smart-check`, `make runtime-check`, or `make test-fast`, then
  `make smart-handoff-check` or `make release-check` before handoff, review, or a meaningful
  checkpoint commit.
- UI runtime changes: run UI tests/build plus relevant API/readiness tests.
- Docs/process/review wiring changes: run `make readiness-check`, plus the focused test for the
  specific script/doc you touched.
- Pure docs edits: run `make docs-check`.
- Tiny mechanical docs plus code-adjacent edits: run `make quick-check` or `make readiness-check`
  according to `make validation-decision`.
- External-review handoff: run `make review-candidate`.

Do not use fast gates to claim release readiness. Fast gates are a development accelerator, not a
replacement for the full review/release gates.
