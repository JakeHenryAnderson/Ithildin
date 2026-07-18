# EXT-TRUSTED-HOST-RUNTIME-002 Governance Bindings

- Finding ID: EXT-TRUSTED-HOST-RUNTIME-002
- Severity: high
- Area: trusted-host-promotion-runtime
- Affected files/functions: apps/api/src/ithildin_api/trusted_host_promotions.py; TrustedHostPromotionService.create_proposal; TrustedHostPromotionService.apply_approved; trusted-host descriptor and policy integration boundary
- Claim being tested: Host staging must be bound to server-derived principal, trusted-host descriptor, policy, manifest, schema, and reviewed-candidate evidence and must revalidate those bindings immediately before placement.
- Observed behavior: Independent packet-and-source review at commit 63c7ffd47853ed2f5f132772ca1af264555456be found that the implemented runtime stores sandbox and artifact evidence but does not have a runtime trusted-host descriptor or the required policy, manifest, schema, principal, and reviewed-candidate bindings described by the design contracts.
- Risk: The staging slice cannot yet prove that the destination host, caller identity, policy decision, governed surface, or reviewed implementation state is the one authorized for the placement.
- Recommended fix: Define an explicit architecture and implementation gate for server-derived principal identity, immutable trusted-host descriptor identity and hash, policy and manifest versions and hashes, matched rules and obligations, input schema version, reviewed candidate identity, and pre-placement revalidation.
- Blocking status: blocking
- Disposition: deferred
- Verification notes: This is intentionally deferred because completing it changes the public request and evidence contracts and introduces a new runtime trust binding that is outside the bounded remediation authority. ERG-005 runtime source-review closure and broader host-promotion claims remain blocked; no risk acceptance or approval is implied.
