# Ithildin Two-Lane Development Control Board

Status: Command Center exact-candidate finalization active; Gateway lane remains blocked on explicit
external/source review.

Base commit: `6a357bd4bb7e7a7dc10abeb4bfa834addf64175c`
Governed tool count: `24`
Selected next governed capability: `not selected`
Current product posture: local preview; not production or enterprise ready

This board coordinates the Command Center UI/UX and Gateway capability initiatives without merging
their authority. It does not approve a UI ticket, external review outcome, runtime implementation,
new governed tool, release, or enterprise/security-product claim.

## Lane A: Command Center UI/UX

Current ticket: `CC-PILOT-107-PRE-UAT-REMEDIATION`
Current state: `exact_candidate_finalization_active`
Previous tickets: `CC-PILOT-101` through `106`, implementation candidates complete

Completed evidence:

- [Command Center Initial Operator UAT Evidence](command-center-initial-operator-uat-evidence.md)
- [CC-PILOT-101 Authoritative Data Feasibility Map](command-center-cc-pilot-101-data-feasibility.md)
- [CC-PILOT-101 Implementation Handoff](command-center-cc-pilot-101-implementation-handoff.md)
- [CC-PILOT-102 Authoritative Data Feasibility Map](command-center-cc-pilot-102-data-feasibility.md)
- [CC-PILOT-102 Implementation Handoff](command-center-cc-pilot-102-implementation-handoff.md)
- [CC-PILOT-103 Authoritative Data Feasibility Map](command-center-cc-pilot-103-data-feasibility.md)
- [CC-PILOT-103 Implementation Handoff](command-center-cc-pilot-103-implementation-handoff.md)
- [CC-PILOT-104 Authoritative Data Feasibility Map](command-center-cc-pilot-104-data-feasibility.md)
- [CC-PILOT-104 Implementation Handoff](command-center-cc-pilot-104-implementation-handoff.md)
- [CC-PILOT-105 Authoritative Data Feasibility Map](command-center-cc-pilot-105-data-feasibility.md)
- [CC-PILOT-105 Implementation Handoff](command-center-cc-pilot-105-implementation-handoff.md)
- [CC-PILOT-106 Authoritative Data Feasibility Map](command-center-cc-pilot-106-data-feasibility.md)
- [CC-PILOT-106 Implementation Handoff](command-center-cc-pilot-106-implementation-handoff.md)
- [CC-PILOT-107 Fresh-Operator UAT Handoff](command-center-cc-pilot-107-uat-handoff.md)
- [Command Center Pre-UAT Accessibility, Authority, and UI Review](command-center-pre-uat-accessibility-authority-ui-review.md)
- [Independent Sol Ultra Pre-UAT Findings Register](command-center-sol-ultra-pre-uat-review.md).

The user's standing authorization carries the bounded remediation required by the independent
review. Fresh-operator UAT is prohibited until all high findings are closed, medium findings are
fixed or evidence-dispositioned, the candidate is reproducibly bound and validated, and an
independent closure review clears entry to `CC-PILOT-107`. Automated checks and internal review do
not substitute for that acceptance gate or authorize further Command Center initiative expansion.

No separate dated acceptance record was created at the historical `CC-PILOT-101` next gate. Later
tickets therefore remain integrated implementation candidates rather than individually human-
accepted slices. The active user-provided goal explicitly authorizes remediation and integrated
validation, but it does not retroactively fabricate per-ticket acceptance; the fresh-operator UAT
remains the product-comprehension gate for the combined candidate.

## Lane B: Gateway Capability and Enterprise Readiness

Current route: prepare the separate `PIS-002` entry decision record under the cleared `PIS-001` exact-candidate review; `ERG-006`/`ERG-007` remain planning-only scope
Computed next action: `prepare_pis_002_entry_decision_record`
Current response count: `0`
Current source-review status: `pis_001_internal_review_cleared_external_architecture_lineage_retained`
Runtime promotion allowed: `false`

Verified review package:

- trusted-host descriptor contract;
- decision intake;
- 12-state / 15-transition design state machine;
- 24 rejected negative fixtures;
- zone contract;
- implementation-planning contract;
- source-review and disposition packets;
- external-review bundle;
- response kit and absent/invalid-response dry run;
- internal design/source review with zero findings;
- limited-runtime plan and ticket skeleton;
- runtime implementation decision skeleton;
- observed negative transcripts;
- staging-only runtime source-review bundle.

Current packet entry points:

- `var/review-packets/v3/trusted-host-promotion-external-review/`
- `var/review-packets/v3/trusted-host-promotion-runtime-source-review/`
- `var/review-packets/v3/trusted-host-promotion-response-kit/`

Required human/external decision:

- identify or authorize the external/source reviewer and delivery route for the `ERG-005` package;
  or
- explicitly defer `ERG-005` external review while keeping promotion blocked.

Generating and validating a packet is not evidence that it was sent, received, reviewed, accepted,
or closed. No agent may fabricate a response or reclassify internal review as independent review.

## New Capability Selection

No new governed-tool candidate should be selected while the computed current route remains
`ERG-005` and `PRD-CAPABILITY-001` remains `no_go` for runtime implementation.

The next-capability readiness gate currently reports:

- `next_candidate: not selected`;
- `next_candidate_status: pending_selection`;
- `next_candidate_proposal_complete: false`;
- `next_candidate_plan_complete: false`;
- `next_candidate_implementation_allowed: false`;
- `broader_capability_expansion_allowed: false`;
- `new_power_classes_allowed: false`.

Candidate evaluation, proposal, and risk analysis remain allowed planning work. Manifest, executor,
policy, MCP/API, approval, audit, UI runtime, storage, sandbox, promotion, identity, SIEM, and other
runtime changes require a separate explicit decision for one bounded capability.

## Current Dirty-Candidate Validation Snapshot

The integrated remediated dirty candidate passed the following checks. They must still be rerun on
the exact clean commit before dispatching the closure review:

```text
make ui-test
make typecheck
make tool-surface-invariant-gate
make no-new-powers-guardrail
make agent-workflow-check
uv run pytest tests/test_release_readiness.py tests/test_docs_site.py -q
make lint
make docs-site
git diff --check
make release-check
```

Passed for the completed `ERG-005` source-finding disposition route:

```text
make enterprise-operator-next-action
make enterprise-current-checkpoint
make post-rc-decision-register-check
make next-capability-readiness
make enterprise-readiness-gap-matrix-check
make trusted-host-descriptor-contract-check
make trusted-host-promotion-decision-intake-check
make trusted-host-promotion-state-machine-check
make trusted-host-promotion-negative-fixtures-check
make trusted-host-promotion-zone-contract-check
make trusted-host-promotion-implementation-plan-check
make trusted-host-promotion-source-review-packet-check
make trusted-host-promotion-disposition-packet-check
make trusted-host-promotion-external-review-bundle-check
make trusted-host-promotion-response-kit-check
make trusted-host-promotion-response-dry-run
make trusted-host-promotion-internal-review-check
make trusted-host-promotion-implementation-gate-decision-check
make trusted-host-promotion-limited-runtime-plan-check
make trusted-host-promotion-limited-runtime-ticket-check
make trusted-host-promotion-runtime-implementation-decision-check
make trusted-host-promotion-negative-transcripts
make trusted-host-promotion-runtime-source-review-bundle-check
```

The current PIS-002 entry-decision preparation route passes:

```text
make production-identity-storage-pis-001-internal-review-check
make production-identity-storage-pis-001-decision-check
make production-identity-storage-pis-001-planning-gate-check
make no-new-powers-guardrail
make tool-surface-invariant-gate
```

The review-run contract now preserves historical manifests without rebinding them and requires an
exact commit, dirty state, and tree fingerprint for current-candidate records. The full dirty-tree
release gate passes. No current-candidate review record may be created until that review has
actually executed against the exact candidate.

## Next Authorized Transitions

1. A real fresh-operator `CC-PILOT-107` UAT record permits only human pilot disposition or bounded
   remediation of recorded UAT findings in Lane A.
2. The cleared PIS-001 exact-candidate review permits preparation of a separate PIS-002 entry
   decision in Lane B; it does not permit PIS-002 implementation.
3. A real external response permits response intake and disposition checks; it does not automatically
   permit runtime implementation.
4. A new capability sprint requires its own selected candidate, proposal, plan, implementation
   decision, tests, source review, and explicit approval.
5. Any third initiative or broader enterprise/security claim requires explicit user authorization.
