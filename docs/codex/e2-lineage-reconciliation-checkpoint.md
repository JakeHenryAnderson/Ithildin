# E2 Lineage Reconciliation Checkpoint

Status: `candidate_independent_review_pending`.

This checkpoint reconciles two accepted development lineages without moving or reinterpreting
either source. The product-line checkpoint remains exact historical evidence of scoped Personal
technical-preview and bounded Enterprise E1 continuation acceptance. The later accepted PIS-005A
review disposition is layered over that historical snapshot as current PIS status.

## Exact Topology

- Product checkpoint `P`: commit
  `4a6b9e5061874a26c5f9d20a39818930866a6d55`, tree
  `2914c134d29e62c031f2778fa31fd858c4ac5276`, sole parent
  `9df7a04cec197fd4953de692793a32e69c107b49`.
- Reviewed PIS-005A repair-9 candidate `A`: commit
  `a23dd3c525bf748a632d8ad3ebd9597883dc0842`, tree
  `c37ff1043cdfe4511fa35a63cd7fd1675f85c797`, sole parent repair-8
  `88f9717198709bfa7b5d520bb4aa41c427543042`. Its independent review result is
  `C0/H0/M0/L0`, with zero open findings.
- Accepted PIS-005A disposition `D`: commit
  `afb81bdc023a300ba49d48d5fddcc8babbf44575`, tree
  `3afbe2381fcd490bf2e511695c00fb05dd226e9b`, sole raw parent `A`.
- Test-only fixture repair `F`: commit
  `c10c6051a62a62fb5618909295828782147428f2`, tree
  `1b3002c64e2891ae6a3a2519e4015ac3a1f56beb`, sole parent `D`. It changes only
  `tests/test_pis005a_contract.py` and grants no disposition or runtime authority.
- Deliberate integration merge `M`: commit
  `b06e8399674f17c188f6502c320a6d2746d24532`, tree
  `855dbd27cc6cc9788a955ff7a6a10e12583c3332`, with raw parents exactly `(F, P)`
  in that order.
- This reconciliation candidate `R` is the checked-out tip of
  `codex/e2-control-tower-lineage-reconciliation`. Its sole raw parent must be `M`; the checker
  reports its exact commit and tree at validation time. This avoids an impossible self-referential
  commit hash while still binding the reviewed candidate to one exact local branch tip.

The source refs for `main`, the product checkpoint, E2 preparation, PIS-004A, every protected
PIS-005A predecessor, and the repair-9 disposition remain pinned in the
[closed machine-readable record](e2-lineage-reconciliation-checkpoint.json). The reconciliation
checker compares local, tracking, and live remote identities and fails closed on movement.

## Preserved Acceptance And Authority

Product continuation acceptance is true only for the Personal technical preview and the bounded
Enterprise E1 single-site pilot. Prescribed human UAT was not executed and did not pass.

The checkpoint preserves exactly `24` governed tools and Gateway runtime authority. Enterprise E2
remains `preparation_complete_implementation_not_authorized`. The selected next recommendation is
the Command Center local authentication boundary and credential exit, but E2-ID-005A implementation
authorization is `false`.

PIS collection action, remote transport, production identity, runtime PostgreSQL, release,
production, promotion, and human-UAT-complete authority all remain `false`. This record does not
authorize E2-ID-005A implementation, change a public API, add an authentication or session
capability, move a protected ref, or turn an automated gate into independent review or acceptance.

## Validation Boundary

Run:

```sh
make e2-lineage-reconciliation-check
```

The target validates the closed record, exact source commits and trees, raw-parent order, protected
local/tracking/live refs, clean non-shallow state, unsafe Git metadata and redirects, byte-exact
product artifacts, frozen PIS review documents, the `F`/`M`/`R` path inventories, 24-tool and
Gateway ceilings, and all authority nonclaims. It uses safe temporary detached worktrees to:

- validate the product checkpoint at exact `P`;
- run both PIS report builders at exact `D`;
- run the complete repaired PIS fixture and attack-matrix test module using the exact `F` test blob
  and the exact `D` source root;
- validate E2 preparation at exact commit
  `e86f5a19e4e067d73141246f78304597e6cc28a0`.

The candidate-specific PIS and E2 checkers remain strict. They are not relaxed to accept this
downstream reconciliation tip.

## Separate Release Blocker

The unresolved PIS-002/PIS-003 enterprise-route artifact-validity blocker remains separate. It is
not repaired, waived, relabeled, or treated as resolved here. Consequently this checkpoint does not
run or claim success for `make release-check` or `make review-candidate`.

## Next Step

Obtain a fresh independent read-only review of the exact clean `R` commit and tree. Only a separate
zero-finding disposition may create the reviewed reconciliation baseline for a later, separately
authorized E2-ID-005A implementation lane.
