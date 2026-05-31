# EXT-PA-004 Unified Diff Hunk Counts

- Finding ID: EXT-PA-004
- Severity: low
- Area: patch-apply
- Affected files/functions: apps/api/src/ithildin_api/patches.py; apply_unified_diff; _HUNK_RE; tests/test_patch_proposals.py
- Claim being tested: accepted unified-diff hunks should match their declared old/new line counts or be explicitly documented as a custom grammar.
- Observed behavior: The external source review found strong context matching and single-file validation, but did not see hunk old/new count metadata enforced.
- Risk: Inconsistent hunk metadata could make reviewed diffs harder to reason about even when context matching prevents unsafe application.
- Recommended fix: Enforce old/new hunk counts or document the constrained custom unified-diff subset.
- Blocking status: later
- Disposition: fixed
- Verification notes: `apply_unified_diff()` now counts context, removal, and addition lines per hunk and rejects hunks whose actual old/new counts do not match the header. `test_invalid_diff_shapes_are_denied` includes inconsistent hunk-count fixtures.
