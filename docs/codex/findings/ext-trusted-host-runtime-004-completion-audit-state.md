# EXT-TRUSTED-HOST-RUNTIME-004 Completion Audit State

- Finding ID: EXT-TRUSTED-HOST-RUNTIME-004
- Severity: medium
- Area: trusted-host-promotion-runtime
- Affected files/functions: apps/api/src/ithildin_api/trusted_host_promotions.py; TrustedHostPromotionService.apply_approved; TrustedHostPromotionService.complete_with_evidence; apps/api/src/ithildin_api/app.py; apply_trusted_host_promotion
- Claim being tested: Diagnostics must not report a clean completed staging attempt when the final successful execution audit event was not written.
- Observed behavior: Independent packet-and-source review at commit 63c7ffd47853ed2f5f132772ca1af264555456be found that the attempt and proposal became completed before the route wrote tool.execution.completed.
- Risk: An audit write failure could leave terminal application state without its required success evidence while diagnostics falsely reported clean.
- Recommended fix: Keep the attempt and proposal nonterminal until successful completion audit evidence is written and make the interrupted state visible to diagnostics.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: apply_approved now leaves the attempt staged and the proposal completion_evidence_pending; the route finalizes them only after tool.execution.completed is written. An injected completion-audit failure leaves diagnostics ambiguous, the attempt staged, and the proposal nonterminal. Exact-candidate independent re-review remains required.
