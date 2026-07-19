# EXT-TRUSTED-HOST-RUNTIME-002 Governance Bindings

- Finding ID: EXT-TRUSTED-HOST-RUNTIME-002
- Severity: high
- Area: trusted-host-promotion-runtime
- Affected files/functions: apps/api/src/ithildin_api/trusted_host_promotions.py; TrustedHostPromotionService.create_proposal; TrustedHostPromotionService.apply_approved; trusted-host descriptor and policy integration boundary
- Claim being tested: Host staging must be bound to server-derived principal, trusted-host descriptor, policy, manifest, schema, and reviewed-candidate evidence and must revalidate those bindings immediately before placement.
- Observed behavior: Independent packet-and-source review at commit 63c7ffd47853ed2f5f132772ca1af264555456be found that the implemented runtime lacked the complete trusted-host, principal, policy, manifest, schema, and reviewed-candidate authority binding. The approved TGB implementation added those bindings, apply-time installed-candidate verification, terminal drift handling, and exact restart evidence.
- Risk: Without these controls, the staging slice could not prove that the destination host, caller identity, policy decision, governed surface, or reviewed implementation state was the one authorized for placement.
- Recommended fix: Define an explicit architecture and implementation gate for server-derived principal identity, immutable trusted-host descriptor identity and hash, policy and manifest versions and hashes, matched rules and obligations, input schema version, reviewed candidate identity, and pre-placement revalidation.
- Blocking status: blocking
- Disposition: fixed
- Verification notes: Independent Sol xhigh packet-and-source re-review of exact clean commit 919858e8d5886129d7c1fefc730795380cd45f73 and focused packet manifest sha256:02b060bb65d41b317b3a426cd1ad9786d101683303622cb9eedb34436bb9ed16 found no remaining defect in scope. The reviewer reproduced the persisted restart path: a missing verifier terminally stales the approved proposal before reservation or effect, preserves the approval, records zero attempts, and cannot revive after verifier restoration. The normalized exact-candidate response passed the runtime closure preflight with this finding explicitly fixed. This finding disposition does not close ERG-005 or authorize promotion, placement, release, UAT, production use, or new powers.
