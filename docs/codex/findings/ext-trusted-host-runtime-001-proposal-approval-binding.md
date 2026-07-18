# EXT-TRUSTED-HOST-RUNTIME-001 Proposal Approval Binding

- Finding ID: EXT-TRUSTED-HOST-RUNTIME-001
- Severity: high
- Area: trusted-host-promotion-runtime
- Affected files/functions: apps/api/src/ithildin_api/trusted_host_promotions.py; TrustedHostPromotionStore.bind_proposal_approval; TrustedHostPromotionService.approval_review; TrustedHostPromotionService.apply_approved
- Claim being tested: A trusted-host staging attempt must use the single approval created for the route proposal and must not accept a scope-compatible approval copied or selected from another proposal.
- Observed behavior: Independent packet-and-source review at commit 63c7ffd47853ed2f5f132772ca1af264555456be found that the route proposal ID and approval-scoped proposal identity could diverge and that attempts were unique only by approval ID.
- Risk: A caller with admin API access could apply an approved request to a different proposal or create more than one attempt for one proposal, weakening one-proposal and one-approval evidence semantics.
- Recommended fix: Persist the proposal-to-approval binding, revalidate route, proposal, request, scope, resource, and request-hash identity before execution, and enforce one deterministic attempt identity per proposal.
- Blocking status: blocking
- Disposition: fixed
- Verification notes: The remediation candidate stores the created approval ID in proposal metadata, rejects copied or cross-proposal approvals during approval review, derives the attempt ID from the proposal ID, and prevents a second proposal attempt. Focused tests cover cross-proposal use, a copied approval, sequential replay, and a concurrent double apply. Exact-candidate independent re-review remains required before external closure.
