# PIS-005A Independent Implementation Review

Status: independent implementation review complete; no open findings.

Review disposition: `go_record_pis_005a_repair_9_independent_review_only`.

Review date: `2026-07-31`.

Independent review task: `019fb777-e9de-79d1-affd-5303f115fb90`.

Reviewed exact implementation commit: `a23dd3c525bf748a632d8ad3ebd9597883dc0842`.

Reviewed exact tree: `c37ff1043cdfe4511fa35a63cd7fd1675f85c797`.

Reviewed candidate sole raw parent: `88f9717198709bfa7b5d520bb4aa41c427543042`.

Review method: independent read-only Codex review in a clean detached worktree.

Candidate freeze complete: `true`.

Clean detached worktree verified: `true`.

Remote identity verified: `true`.

Focused gate passed: `true`.

Implementation review complete: `true`.

Human UAT complete: `false`.

Live remote transport authorized: `false`.

Release or promotion authorized: `false`.

Critical findings: `0`.

High findings: `0`.

Medium findings: `0`.

Low findings: `0`.

Open findings: `0`.

E2-NODE-005 status: blocked; separate entry decision required.

Current governed tool count: exactly `24`.

## Candidate Identity And Review Method

The exact implementation candidate was independently reviewed in a clean detached worktree. The
reviewer fetched `origin/codex/enterprise-e2-pis005a-review-repair-9`, reproduced the exact commit
and tree above, and verified that its sole raw parent is rejected repair-8 commit
`88f9717198709bfa7b5d520bb4aa41c427543042`, tree
`4963c5a5bef659d52ba7490a8c311991c9168e1b`. Exactly one commit separates repair-8 from the reviewed
candidate.

The named candidate ref, remote-tracking ref, detached `HEAD`, and live remote all matched the
reviewed commit. The named and detached worktrees were clean and non-shallow. All accepted and
rejected predecessor refs, trees, raw parent order, and objects remained exact through repair-8.
Full strict object connectivity passed, and no replacement ref, graft, shallow metadata,
alternate-object metadata, inherited Git redirect, or unsafe repository-local configuration was
present.

The independent review was adversarial and read-only. It inspected the entire cumulative PIS-005A
candidate, not only the repair-9 diff, and reproduced the lifecycle and Git-redirection attack
matrices in disposable repositories and worktrees. It did not edit, stage, commit, push, or write a
disposition to the reviewed candidate.

## Validation Evidence

The review observed the following results at the exact candidate:

- focused lifecycle and Git adversarial suite: 119 tests passed;
- authoritative `make production-identity-storage-pis-005a-check`: valid pending report, 268 tests
  passed, focused Ruff passed, and strict MyPy passed for all 10 checked files;
- cumulative `make production-identity-storage-pis-004a-check`: valid report, 176 tests passed,
  focused Ruff passed, and strict MyPy passed for all 9 checked files;
- E2 named report and tests: valid and 29 tests passed;
- E2 detached report and tests: valid and 29 tests passed;
- named `make enterprise-e2-preparation-check`: passed, including E1 contract, tool-surface, and
  no-new-powers checks;
- `make agent-workflow-check`, `make lint`, `make no-new-powers-guardrail`, and
  `make tool-surface-invariant-gate`: passed; and
- final `git diff --check`, clean/non-shallow state, live identity, raw topology, configuration,
  metadata, worktree binding, and strict object-connectivity audits: passed.

The E2 projection remained `preparation_complete_implementation_not_authorized` with
`production_identity_allowed: false` in named and detached report/test paths. That result is a
preparation ceiling, not E2 entry authority.

## Cumulative Finding Disposition

The fresh review re-dispositioned every historical PIS-005A finding from the accepted PIS-004A
foundation through repair-9:

| Finding | Disposition | Independent closure evidence |
|---|---|---|
| `H-01` — unverified pre-v7 backup | closed | Locked-source substitution, backup provenance, inode continuity, rollback, receipt, and no-blessed-backup regressions passed. |
| `M-01` — incomplete request cross-binding | closed | Persisted trust-anchor, enrollment transaction, canonical application-key ID, certificate reissue/drift, and signed-message binding tests passed. |
| `L-01` — expiry not terminalized | closed | Ordinary and replacement enrollment expiry persisted under the write lock, including exact-boundary and concurrent retry cases. |
| `L-02` — nonce retention | closed | Strict older-than pruning, exact-boundary, restart, replay, concurrency, and revocation-race cases passed. |
| `L-03` — overwritten revocation cause | closed | Original operator, key-compromise, and scope-revocation causes remained immutable while replacement completion was recorded separately. |
| `M-02` — partial publication and no-clobber recovery | closed | Temporary, canonical, and anchor publication failures; child-process crashes; commit ambiguity; retry; fail-stuck; marker; and exact-alias recovery matrices passed. |
| `L-04` — descendant and topology laundering | closed | Raw sole-parent, tree, and ref checks rejected arbitrary or same-tree descendants, merges, predecessor drift, replacement laundering, and missing refs. |
| `L-05` — blocking or nonregular filesystem objects | closed | macOS FIFO, passive FIFO timeout, socket, directory, symlink, unsupported no-follow, permission, link-count, and descriptor-closing cases passed. |
| `L-06` — completed-review lifecycle | closed | An exact legitimate disposition passed both PIS checkers in named and detached modes; nonexact descendant, identity, path, and lifecycle states failed closed. |
| `L-07` — Git trust path | closed | All three checkers used canonical raw-Git binding; repository-local redirection, includes, worktree configuration, config symlinks, alternates, environment redirects, replacements, grafts, shallow state, and linked-worktree attacks were exercised. |

The eight earlier candidates remain rejected evidence. None is relabeled or mutated by this
repair-9 disposition. Their prior findings are repair lineage, not inherited positive review
evidence.

## Completed-Lifecycle And Git-Trust Attacks

The legitimate completed-review simulation contained exactly one descendant whose sole raw parent
was the reviewed repair-9 commit. Its complete per-commit inventory contained exactly three `M`
entries for the existing contract, this review record, and the foundation status projection. It
bound the exact reviewed commit and tree, used the independent detached-review method, and recorded
zero Critical, High, Medium, Low, and open findings. PIS-005A and cumulative PIS-004A passed in
named and detached modes.

The negative matrix rejected or detected second empty and same-tree descendants, another
allowlisted-path descendant, merges, structurally valid siblings, self-binding, wrong reviewed
commit or tree, local/tracking/live and predecessor ref movement, pending/completed narrative
contradictions, nonzero findings, a fourth path including whitespace-only content, deletion,
rename, missing inventory, and any added or otherwise non-`M` review file.

All three reports failed closed when the actual supplied root was contaminated and repository-local
`core.worktree` attempted to redirect observations to a pristine checkout. The matrix also covered
`include.path`, `includeIf`, per-worktree configuration and `extensions.worktreeConfig`, config
symlinks, alternate objects, repository format/config interpretation, inherited environment and
command/config redirects, packed or namespaced replacement refs, grafts, shallow metadata, and
linked-worktree indirection. Ordinary clean named, detached, and legitimate linked worktrees still
passed with canonical supplied-root equality.

## Authority, Release Blocker, And Next Stop

This disposition records independent review closure only. It does not authorize or prove E2 entry,
production identity, runtime behavior, human UAT completion, release acceptance, production
promotion, live TLS or mTLS, certificate issuance, CA or Node private-key custody, remote transport,
runtime PostgreSQL, production credentials, external PIS collection, a new governed tool, or any
broader authority.

The pre-existing PIS-002/PIS-003 enterprise-route artifact-validity condition remains an unrelated
release-train blocker. It was neither repaired, waived, nor relabeled by this review or disposition.

PIS-005A now stops for lineage reconciliation. Only after that separate reconciliation may a
separately authorized E2-ID-005A or E2-NODE-005 milestone be considered; this record supplies no
entry or implementation authority for either milestone.
