# PIS-005A Independent Implementation Review

Status: independent implementation review pending; no review disposition recorded.

Reviewed exact implementation commit: pending.

Reviewed exact tree: pending.

Review method: independent read-only Codex review in a clean detached worktree.

Candidate freeze complete: `true`.

Clean detached worktree verified: `false`.

Remote identity verified: `false`.

Focused gate passed: `false`.

Implementation review complete: `false`.

Human UAT complete: `false`.

Live remote transport authorized: `false`.

Release or promotion authorized: `false`.

Critical findings: pending.

High findings: pending.

Medium findings: pending.

Low findings: pending.

Open findings: pending.

E2-NODE-005 status: blocked; separate entry decision required.

Current governed tool count: exactly `24`.

## Pending Review Procedure

The exact implementation candidate is frozen and awaits independent review. The reviewer must fetch
`origin/codex/enterprise-e2-pis005a-review-repair-7` into matching exact local and remote-tracking
candidate refs, check out the exact candidate commit in a clean detached worktree, verify that both
refs, detached `HEAD`, and the exact tree match, and run:

```sh
make production-identity-storage-pis-005a-check
```

This is a fresh review of the entire repaired candidate, not a review limited to the repair diff.
The external exact commit/tree/live-remote preflight freezes the pending repair-7 identity. A
different structurally valid repair-6 child is a new candidate that requires its own preflight and
independent review; it must not inherit or be relabeled with repair-7 review evidence.
All six predecessor candidates are evidence only and remain rejected:

- `codex/enterprise-e2-pis005a-node-identity`,
  `fce0a3668db5150cf0aa75de1fd914b296a2e099`, tree
  `331adb70f2c2c24def540c3576fc6876e33c478c`; and
- `codex/enterprise-e2-pis005a-review-repair-2`,
  `1542bd0469e18a0ae52cc48920f30b4e41518513`, tree
  `ba9a40e929ff330c15c6c23766006eb1c26878ef`; and
- `codex/enterprise-e2-pis005a-review-repair-3`,
  `afd13f98440d4cd9c032b6a996db133bdf78055d`, tree
  `49e958caeba4f3bce51feaa4e842f8f622c00d4a`; and
- `codex/enterprise-e2-pis005a-review-repair-4`,
  `22566cae4a1bc84dca20747d7bd1531d77d7f025`, tree
  `44952292c183b4a481f15dc691e6c04e90e45d55`; and
- `codex/enterprise-e2-pis005a-review-repair-5`,
  `cedcf5d0bf3baeab12f54600a247a61a4671d7f9`, tree
  `6e4c4097680c97c77913ba10054dbb5e234abe4c`; and
- `codex/enterprise-e2-pis005a-review-repair-6`,
  `735877b2bb387a50dfbd376d6d3d8c047fd49c8f`, tree
  `04edcda705e8ab75b0a37eecb70dce7fafabe544`.

The repair-5 independent review returned `NO_GO` with `C0/H0/M0/L2`. Its arbitrary-descendant
topology acceptance and blocking FIFO-open findings are repair inputs only, not a positive
disposition for repair-5 or this new candidate.

The repair-6 independent review returned `NO_GO` with `C0/H0/M0/L1`. Historical finding L-04
demonstrated that a same-tree extra descendant could move both candidate refs and then use a
replacement object to make ordinary parent/tree/topology operations appear to describe repair-6.
That finding is a repair input only, not a positive disposition for repair-6 or this new candidate.

The fresh review must re-evaluate the entire candidate and independently verify every repair area:

- caller-owned guard coverage for every shared pre-v4 and PIS-005A pre-v7 backup-requiring path,
  with no direct owner `COMMIT` while a guard exists;
- locked-source provenance and dual no-clobber canonical/content-addressed hardlink publication for
  both backup and receipt, with stable descriptors retained through finalization and exact backup
  device/inode identity carried in the precommit receipt for self-describing restart verification;
- exact precommit receipt marker binding in existing `app_metadata`, commit ownership and outcome
  classification, and no postcommit failure reported as rolled back;
- descriptor-based restart classification, safe adoption of verified repair-3 schema-6 prepared
  artifacts, native target-schema distinction, legacy target-without-marker ambiguity, and
  competing-anchor rejection;
- bounded one-alias exact-inode repair, exact receipt projection restoration, repair-3 receipt
  upgrade before retry, and halt when neither backup alias preserves the receipt-bound exact-object
  continuity even if equivalent bytes survive on a different inode;
- deterministic substitution and crash coverage at helper-return/pre-DDL, during DDL,
  post-schema/precommit, after the final precommit check, during commit, and
  postcommit/pre-finalize;
- trusted/private/non-symlink directory enforcement plus unsupported no-follow/hardlink failure,
  permission, ownership, link-count, symlink, temp, canonical, anchor, marker, receipt, in-place,
  snapshot, same-content-different-inode, and bounded passive-FIFO attack coverage without weakening
  the explicit active same-UID writer nonclaim;
- exact PIS-004A gate recognition of the contract-bound named and detached PIS-005A successor,
  requiring exact local and fetched candidate refs, a sole raw direct repair-6 parent with its exact
  tree and refs, and unchanged accepted/rejected ancestry, with extra commits, merges, unrelated
  commits, missing refs, ref drift, and rejected predecessor topology failing closed;
- fail-closed rejection of replacement refs, redirected replacement namespaces, legacy grafts,
  shallow metadata, and inherited Git object/topology redirection, while every identity, tree,
  parent, diff, ref, and ancestry observation runs with replacement processing disabled;
- persisted trust-anchor/application-key-ID revalidation and canonical request cross-binding;
- durable ordinary enrollment expiry at the exact boundary;
- strict older-than nonce pruning with restart, replay, and concurrency behavior; and
- immutable original revocation cause with separately recorded replacement completion.

The reviewer must also verify the explicit residual nonclaims: the protocol is not an atomic
filesystem-plus-SQLite commit, content-addressed anchors are recovery aliases rather than immutable
objects, the protocol does not continuously defeat an indefinitely active same-UID actor with
arbitrary database-directory write, and no runtime or automatic restore capability exists.

The final record may be written only after the independent review reports zero open Critical,
High, Medium, and Low findings. The post-review descendant may change only this record, the
machine-readable review disposition, and the corresponding non-executable status projection in the
PIS-005A foundation document. Executable documentation registries are already part of the reviewed
candidate.

## Authority And Stop Lines

This pending record is not review evidence and does not authorize or prove implementation
completion, human UAT, release acceptance, production promotion, remote transport, live TLS or
mTLS, certificate issuance, CA or Node private-key custody, runtime PostgreSQL, production identity,
remote administration, or a new governed tool.

E2-NODE-005 remains blocked behind a separate entry decision and its own architecture, custody,
transport, external-review, and operator-UAT gates.
