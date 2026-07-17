# Command Center Run-Evidence Revision Integrity Implementation Handoff

Status: implemented and focused checks passed; exact-candidate closeout remains required.

Current governed tool count: `24`.

## Implemented Behavior

- The selected-run evidence closeout compares ten existing authority/revision fields between run
  detail and the independently generated evidence snapshot.
- Exact equality says `Matches generated snapshot`; any difference says
  `Mismatch - reload before handoff` and blocks operator reliance in the copy.
- The technical closeout lists all existing evidence-section SHA-256 digests instead of showing
  only their count.
- Node-origin parity remains a separate comparison because it answers a different question: whether
  bounded Node provenance serialized consistently.
- Generic and Node-governed runs use the same revision-integrity rule.

## Focused Validation

```sh
(cd apps/ui && npm test -- --run App.test.tsx)
(cd apps/ui && npm run build)
uv run python scripts/review_docs.py
git diff --check
```

The focused test suite includes an explicit mismatched tool-call-count fixture and asserts that the
cockpit does not show a match. Passing tests and visible hashes do not prove signature, custody,
receipt, independent attestation, endpoint completeness, or UAT acceptance.

Observed result: 40 UI tests passed; the production UI build, documentation review, and diff check
also passed.

## Required Exact-Candidate Closeout

After committing this bounded slice, run `make agent-workflow-check`, `make release-check`, and
`make review-candidate` against the exact clean commit. Record the commit and generated packet path;
do not treat those artifacts as release, approval, or product-claim authorization.
