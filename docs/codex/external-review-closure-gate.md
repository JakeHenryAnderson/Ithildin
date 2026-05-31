# External-Review Closure Gate v2

Task 156 adds `make external-review-closure-gate`. The gate keeps source-review closure honest while
Ithildin remains in the v0.5 review-closure track.

## Command

```sh
make external-review-closure-gate
uv run python scripts/external_review_closure_gate.py --json
```

Use `--require-closed` only for a future release decision that intentionally requires every external
source-review row to be closed:

```sh
uv run python scripts/external_review_closure_gate.py --require-closed
```

## Expected Current Result

The current healthy result is:

- the gate is `valid`;
- `external_closure_complete` is `false`;
- blockers list the still-pending external review rows;
- no docs claim source review is complete, capability expansion is allowed, or new tool powers are
  ready.

This is deliberately different from `make capability-expansion-gate --require-allowed`. The closure
gate checks honesty and matrix consistency. It does not approve capability expansion.

## Closure Rule

External rows may move out of `external_pending` only after GPT 5.5 Pro / Very High or a human
expert reviews the relevant source/evidence, any actionable findings are recorded with `EXT-###`
finding IDs, and verification commands/fixed commits or accepted-risk links are recorded.
