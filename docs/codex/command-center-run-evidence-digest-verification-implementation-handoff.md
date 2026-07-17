# Command Center Run-Evidence Digest Verification Implementation Handoff

Status: implemented and focused checks passed; exact-candidate closeout remains required.

Current governed tool count: `24`.

## Implemented Behavior

- Command Center recomputes all four existing run-evidence section digests with browser-native Web
  Crypto after each evidence response loads.
- Canonical JSON ordering matches Ithildin's Python hashing contract for JSON-compatible evidence.
- Missing or different values produce `Mismatch - do not rely on snapshot` and name the affected
  sections instead of treating supplied hashes as verified.
- Missing Web Crypto produces `Unavailable`; it does not silently downgrade to a match.
- `Export Run Evidence` parses and verifies the exact fetched response before download; malformed,
  wrong-run, mismatched, or locally unverifiable responses are blocked.
- Existing run-revision comparison, Node-origin parity, signed-evidence non-claims, raw technical
  details, and export behavior remain separate and unchanged.

## Focused Validation

```sh
(cd apps/ui && npm test -- --run App.test.tsx)
(cd apps/ui && npm run build)
uv run python scripts/review_docs.py
git diff --check
```

The suite includes exact Python-generated SHA-256 fixtures for one nested run object and the empty
array sections, plus an explicit mismatched timeline digest. These values avoid proving the browser
implementation only against a duplicate test helper.

Observed result: 42 UI tests passed, including verified, mismatched, unavailable, and blocked-download states;
the production UI build, documentation review, workflow check, Ruff, and diff check passed.

## Required Closeout

After focused checks pass, commit the bounded slice and run `make agent-workflow-check`,
`make release-check`, and `make review-candidate` on the exact clean commit. Passing checks do not
authorize release, UAT acceptance, external-review closure, custody claims, or capability expansion.
