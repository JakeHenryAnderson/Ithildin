# PIS-004A Independent Implementation Review

Status: independent implementation review complete; no open findings.

Review disposition: `go_record_pis_004a_independent_review_only`.

Reviewed exact implementation commit:
`ff358753c50037c2bc936b761f249cf5c9115749`.

Reviewed exact tree: `0fff4fe145ca0b2b9db8fa874396486bba5eb6c7`.

Reviewed candidate parent: `68b96608fd3c0014f93d0c89d52c75e1e251b1f9`.

Rejected-candidate repair baseline: `0c40e553a75ca8c94640c2d34a110f3ce05bb792`.

Review method: independent read-only Codex review in a clean detached worktree.

Critical findings: `0`.

High findings: `0`.

Medium findings: `0`.

Low findings: `0`.

Open findings: `0`.

Current governed tool count: exactly `24`.

This is a post-review record, not the exact implementation commit that received the review. It
records the disposition without changing that candidate's runtime, schema, migration, policy,
authorization, session, identity, fixture, dependency, or test bytes.

## Candidate Identity And Validation

The reviewer independently fetched
`origin/codex/enterprise-e2-pis004a-review-repair`, checked out the exact commit above in a clean
detached worktree, and verified that fetched remote identity, detached `HEAD`, and the remote
repository identity matched. The reviewed cumulative repair inventory from the rejected candidate
contains exactly 20 paths.

The authoritative focused gate passed at the reviewed commit:

```sh
make production-identity-storage-pis-004a-check
```

Observed results were:

- contract report `valid: true`;
- schema version `6` with fingerprint
  `sha256:ca52764e2c4544446f0a1379abc60ec6d74a9320222509974d1cb35c1c955114`;
- exactly 24 governed tools;
- all six PIS-004A focused test files passed, totaling 141 tests;
- focused Ruff passed;
- strict MyPy passed for all nine checked source files; and
- `git diff --check` passed.

The reviewer observed only non-fatal pre-existing pytest temporary-directory cleanup warnings.
Those warnings are not represented as stronger test or release evidence.

## Findings And Closure

The first review of rejected candidate
`0c40e553a75ca8c94640c2d34a110f3ce05bb792` identified two selected High findings:

1. approval revalidated the current approver but not a queued requester's current authority; and
2. re-enabling an organization membership could revive enabled child workspace roles.

The repaired candidate binds queued requests to exact requester identity and membership
generations, revalidates current human requester authority before approval, disables all child
workspace memberships atomically with the parent, and requires explicit workspace-role
reassignment after re-enable.

The rereview also identified and then verified closure of two bounded Medium findings:

1. caller-selectable approval classification could choose `standard` and use the former
   standard-class self-approval path; and
2. an outstanding OIDC authentication grant did not bind or revalidate identity-provider
   configuration generation.

The final candidate removes the generic caller-selectable approval request seam, uses named
server-owned entry points that fix approval class, denies self-approval for every class, and marks
approval request and decision snapshots as `effect_authority: false`. It also binds each OIDC grant
to provider-configuration ID and generation and atomically rejects disabled, changed, remapped, or
re-enabled stale provider authority before grant consumption. The reviewer reproduced both prior
Medium cases and confirmed that neither could issue authority or a session.

The final rereview returned no Critical, High, Medium, or Low finding. Both selected High findings
remain closed.

## Authority And Stop Lines

This disposition clears the exact local-only/default-off PIS-004A implementation for durable
recording only. It does not authorize or prove:

- E2-ID-005 entry or implementation;
- human UAT completion or release acceptance;
- an approval effect consumer;
- a live identity-provider connection or external network access;
- production identity, credentials, signing-key custody, or remote administration;
- runtime PostgreSQL, a database connection, or migration execution;
- production promotion, a public security claim, or a new governed tool.

The E1 completion contract still records `human_uat_complete: false` and
`next_action: stop_for_human_uat`. E2-ID-005 therefore remains blocked pending actual E1 human-UAT
findings and a separate entry decision. The standing PIS-003 external-input wait is unchanged.
