# Command Center Node Run-Origin Evidence Parity Implementation Handoff

Status: implemented and focused checks passed; exact-candidate validation remains required.

Current governed tool count: `24`.

## Implemented Behavior

- The selected Node run authority panel compares the existing run-detail metadata with the existing
  redacted evidence-export `run.origin` across all nine bounded origin fields.
- While evidence loads, the panel says `Preparing comparison`. A failed evidence request says
  `Unavailable` rather than implying consistency.
- Exact equality says `Matches selected run` and explicitly limits that statement to same-record
  serialization consistency, not independent attestation.
- A missing or different origin says `Mismatch - do not rely on export origin` and directs the
  operator to reload and review evidence before handoff.
- Generic MCP and guided-demo runs retain their existing presentation.

## Focused Validation

```sh
(cd apps/ui && npm test -- --run App.test.tsx)
(cd apps/ui && npm run build)
uv run python scripts/review_docs.py
git diff --check
```

Observed result: 39 UI tests passed, including explicit matching, unavailable, and mismatched
Node-origin cases; the production UI build and documentation routing checks passed.

## Remaining Closeout

Commit this bounded slice, refresh ignored exact-candidate status evidence if required, then run:

```sh
make agent-workflow-check
make release-check
make review-candidate
```

Passing checks and generated evidence do not authorize release, approval, UAT acceptance, or any
claim that runner enforcement, model activity, filesystem isolation, custody, or all endpoint
activity has been proven.
