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

For a shorter recommendation-only view that never runs commands and never claims release proof, run:

```sh
make validation-recommendation
```

or pass a hypothetical file set through Make:

```sh
make validation-decision ARGS=apps/api/src/ithildin_api/tools/example.py
```

To run the recommended command set directly:

```sh
make dev-check
```

`dev-check` wraps `smart-check`, which prints the same file/category plan, runs the recommended
commands, and records
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

When Python test files under `tests/` are dirty, `smart-check` also runs those changed test files
directly with `slow_packet` tests excluded as focused evidence. That keeps test-writing loops
honest without jumping straight to the full Python suite or generated-packet tests. Use
`make test-fast`, `make test`, or `make release-check` when a change needs broader confidence or
checkpoint evidence.

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
uv run python scripts/validation_timing.py --profile enterprise-status
uv run python scripts/validation_timing.py --profile handoff-dry-run
uv run python scripts/validation_timing.py --profile readiness --budget-seconds 300
uv run python scripts/validation_timing.py --command "make enterprise-response-paste-preflight" --budget-seconds 10 --fail-on-budget
```

Handoff-oriented timing profiles are measurement aids, not proof gates:

- `enterprise-status`: times the no-refresh `make enterprise-status-quick` operator-status lane.
- `enterprise-send-refresh`: times regeneration of the current ERG-003/ERG-002 send artifacts.
- `handoff-dry-run`: times the cheap current-artifact readiness path without rebuilding the full
  review candidate.
- `handoff`: times `make review-candidate`, the full release/handoff proof path.

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

For the common, no-refresh enterprise status/send-guidance loop, run:

```sh
make enterprise-status-quick
```

This quick slice runs the compact status view and operator next-action guidance. It does not refresh
generated ERG-003/ERG-002 send artifacts, does not validate the current-checkpoint packet, and does
not validate the status export or Mission Control display-import contract.

When the send artifacts themselves may be stale and need to be rebuilt before the same status checks,
run:

```sh
make enterprise-status-slice
```

This refresh-inclusive slice runs `make enterprise-review-send-refresh`, then `make
enterprise-status-quick`, then the current checkpoint, status export check, and Mission Control
display-import contract check. Both status slices are focused development evidence only; use `make
enterprise-send-now` on a clean tree for the final send summary, `make artifact-freshness-check`
when you need full generated artifact freshness, `make review-candidate` before handoff, and `make
release-check` before broad checkpoint claims.

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

### Artifact Freshness

Run:

```sh
make artifact-freshness-check
```

Use this before starting a long gate when the likely failure is stale generated evidence rather than
implementation breakage. The command checks the current enterprise send artifacts, compact v1.0 RC
packet, and captured release-check transcript against the current commit. It prints refresh commands
such as `make enterprise-review-send-refresh` or `make review-candidate` when those artifacts are
stale.

This command does not start services, does not call governed tools, does not record external review,
and does not replace `make release-check` or `make review-candidate`.

### Status Now

Run:

```sh
make status-now
```

Use this when you want the smallest current-state answer: commit, dirty state, tool count, selected
capability, technical MVP status, enterprise next action, validation mode, artifact freshness, and
the next command to run. It is a status command only. It is not release proof and is not handoff
proof.

### Packet Recursion Guard

Run:

```sh
make packet-check-recursion-guard
```

Use this when editing generated packet checks, status exports, review bundles, or response kits.
Do not nest high-level packet/status/export report builders inside another high-level packet check
when the referenced builder can reach back into the caller through current-checkpoint, send
readiness, or external-review bundle paths. Packet checks may bundle related docs and list the
dedicated validation commands as external evidence, but recursive report imports should fail fast in
this guard instead of becoming a long-running check.

`quick-check` and `release-check` both run this guard so known packet-check recursion hazards are
caught before broad validation spends time rebuilding packet graphs.

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

### Dev Check

Run:

```sh
make dev-check
```

Use this as the normal default after a focused change. It delegates to the dirty-file-aware
validation planner instead of blindly running the full release gate. If the planner sees runtime,
manifest, policy, UI, or review-packet surfaces, it reports the slower release/handoff gate as
deferred evidence so the developer can finish the inner loop first and then run the right checkpoint
gate intentionally.

### Quick Check

Run:

```sh
make quick-check
```

Use this for small docs, bookkeeping, script wiring, and manager-owned cleanup where no runtime,
manifest, policy, API/MCP, approval/audit, or UI behavior changed.

This runs core boundary checks, lint, and typecheck. It does not generate review packets.

### Capability Check

Run:

```sh
make capability-check
```

Use this for bounded read-only capability implementation work before the full release gate. It checks
the manifest lock, tool-surface invariant, no-new-powers guardrail, read-only capability inventory,
project-intelligence readiness, next-capability readiness, policy parity, focused runtime tests, and
the broad Python suite without generated-packet `slow_packet` tests.

This is stronger than `dev-check` for tool work but still narrower than `release-check`. It is not a
source-review handoff gate by itself.

### Evidence Check

Run:

```sh
make evidence-check
```

Use this for review/evidence/checkpoint wiring changes where the risk is stale handoff state rather
than runtime behavior. It checks release evidence, reviewer findings, finding summaries,
review-run manifests, packet recursion, and docs-site wiring without running the full Python suite or
UI production build.

This is useful after docs, packet, response-kit, or external-review intake work. It is not a
replacement for `release-check` before a major checkpoint or external handoff.

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
  tests with `make dev-check`, `make runtime-check`, `make capability-check`, or `make test-fast`, then
  `make smart-handoff-check` or `make release-check` before handoff, review, or a meaningful
  checkpoint commit.
- UI runtime changes: run UI tests/build plus relevant API/readiness tests.
- Docs/process/review wiring changes: run `make readiness-check` or `make evidence-check`, plus the
  focused test for the specific script/doc you touched.
- Pure docs edits: run `make docs-check`.
- Tiny mechanical docs plus code-adjacent edits: run `make dev-check`, `make quick-check`, or `make readiness-check`
  according to `make validation-decision`.
- Stale packet suspicion before a long gate: run `make artifact-freshness-check`.
- Quick operator orientation: run `make status-now`.
- External-review handoff: run `make review-candidate`.

Do not use fast gates to claim release readiness. Fast gates are a development accelerator, not a
replacement for the full review/release gates.
