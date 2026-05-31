# Test Determinism Gate

Task 128 adds `make determinism-check` as a local-preview reliability gate before deeper v0.4
hardening work. It is intentionally modest: it does not prove every test is deterministic, but it
catches common sources of accidental local-state coupling before a review candidate is generated.

## Command

```sh
make determinism-check
```

Direct JSON form:

```sh
uv run python scripts/test_determinism_gate.py --json
```

The gate runs pytest collection twice and compares the output, then scans committed test files for
obvious nondeterministic patterns such as `time.sleep`, unseeded `random.*` calls, and hard-coded
`/tmp` paths. `make release-check` includes this gate before running the full test suite.

## Boundary

This is a repeatability guardrail, not a formal proof. Tests that legitimately need clocks,
temporary files, or generated identifiers should keep those values scoped to `tmp_path`, explicit
fixtures, or deterministic helper APIs. Broader OS/platform nondeterminism remains part of external
source review and platform-support work.
