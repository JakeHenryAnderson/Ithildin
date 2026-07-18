# EXT-TRUSTED-HOST-RUNTIME-009 Approver Role Enforcement

- Finding ID: EXT-TRUSTED-HOST-RUNTIME-009
- Severity: high
- Area: identity, authorization, and approval-role binding
- Affected files/functions: apps/api/src/ithildin_api/app.py; approve_approval; deny_approval; apps/api/src/ithildin_api/trusted_host_promotions.py; approval_decision_context; _require_current_approval_decision; _production_readiness
- Claim being tested: A trusted-host promotion can be decided and placed only when the current server-derived deciding principal possesses every role declared in the immutable approval scope.
- Observed behavior: Independent exact-candidate review at commit 43a1a4a38195a91cc7e76cde34103f68ff31916a reproduced proposal, approval, and placement completion with a registry principal whose roles were `Admin` and `Auditor`, omitting the required `Approver` role.
- Risk: A principal lacking a declared mandatory authorization role could approve and complete a host-staging filesystem effect.
- Recommended fix: Enforce the complete required approver role set before any trusted-host approval transition, fail production readiness when the configured principal lacks that set, revalidate it at apply time, and include a no-effect negative case in exact-candidate evidence.
- Blocking status: blocking
- Disposition: fixed
- Verification notes: Trusted-host approval and denial now use a current server-derived decision context and reject a missing required role before transition. Apply revalidates the role set, production readiness fails closed, and focused API coverage proves the approval remains pending, no promotion attempt is recorded, and no staging effect occurs. The governance-drift matrix and source-review focused command include the regression. A regenerated clean exact-candidate packet and independent re-review remain required before closure.
