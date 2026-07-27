# Enterprise E1 Candidate Gate Procedure

Status: pre-freeze procedure. A passing run must be recorded separately against one exact clean
candidate. This procedure is not itself candidate qualification, independent review, human UAT,
release acceptance, or production promotion.

## Freeze boundary

The candidate must be a clean commit on `codex/enterprise-single-site-operations`, descended from
`0ef2fae9a06da7455a25017e5773caa52e7c8db6`. E1-O1 through E1-O5 and E1-M1 through
E1-M5 must be complete. E1-O6/E1-M6 must remain `in_progress`, and candidate gate, independent
review, UAT packet, human UAT, and PIS collection authority must remain false.

Record the exact commit, then run:

```sh
E1_CANDIDATE_COMMIT="$(git rev-parse HEAD)"
make enterprise-e1-candidate-check E1_CANDIDATE_COMMIT="$E1_CANDIDATE_COMMIT"
```

The gate checks exact HEAD and tree identity plus cleanliness before and after the inventory. It
runs every E1 milestone gate, the E1 tests, the descendant-safe Local v1 candidate inventory, the
descendant-safe PIS wait, the 24-tool/no-new-powers guards, the full non-slow Python suite used by
Local v1, strict shipped-source and E1 typing, all Command Center tests and production build, docs
generation, the agent-workflow check, and a current npm high-advisory audit.

The descendant-safe Local v1 inventory reruns the current Local v1 candidate inventory with one
intentional evidence substitution. It does not rerun the historical
`local-v1-o2-evidence-check`, because that check requires the exact O2 qualification-only
descendant and its private evidence base. Instead,
`enterprise-e1-inherited-local-v1-check` verifies that the frozen Local v1 candidate and tree are
ancestors of E1, its hash-bound candidate and independent-review evidence remain complete, human
UAT and release acceptance remain false, and all protected Local v1 qualification and UAT records
are byte-for-byte unchanged from the required E1 source commit. All other Local v1 candidate
inventory targets run in their original order. This preserves the historical O2 result as lineage;
it does not relabel or reproduce that result against the E1 descendant.

The transcript must be retained outside the repository and reduced to a non-sensitive durable gate
record with transcript SHA-256. Generated packet paths, tokens, local state, and private identifiers
must not be committed.

## Result interpretation

A pass qualifies the exact commit for proportional independent review. It does not authorize
human UAT until that review is closed and the exact-candidate UAT packet is prepared. It does not
complete human UAT, release acceptance, enterprise production readiness, Local v1 acceptance, or
any external-system action.
