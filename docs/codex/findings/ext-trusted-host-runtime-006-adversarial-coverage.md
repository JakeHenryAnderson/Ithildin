# EXT-TRUSTED-HOST-RUNTIME-006 Adversarial Coverage

- Finding ID: EXT-TRUSTED-HOST-RUNTIME-006
- Severity: medium
- Area: trusted-host-promotion-runtime
- Affected files/functions: tests/test_api_service.py; scripts/trusted_host_promotion_negative_transcripts.py; scripts/trusted_host_promotion_runtime_source_review_bundle.py; FOCUSED_TEST_COMMAND
- Claim being tested: The runtime handoff must include direct evidence for binding mismatch, concurrency, unsafe source object types, destination conflict, audit interruption, and governance drift.
- Observed behavior: Independent packet-and-source review at commit 63c7ffd47853ed2f5f132772ca1af264555456be found the focused tests and generated transcripts too narrow for the documented trust claims. The TGB implementation expanded the matrix across identity, host descriptor, policy, manifest, schema, candidate, approval, source/destination, migration, and evidence drift, including direct installed-file mutation and missing-verifier restart proofs.
- Risk: Without the expanded evidence, review could miss a replay, overwrite, object-race, incomplete-evidence, governance-drift, or stale-review-identity regression while relying on a nominal happy-path packet.
- Recommended fix: Expand focused API tests, observed negative transcripts, and the packet command to cover each adversarial category and retain safe output assertions.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: Independent Sol xhigh packet-and-source re-review of exact clean commit 919858e8d5886129d7c1fefc730795380cd45f73 and focused packet manifest sha256:02b060bb65d41b317b3a426cd1ad9786d101683303622cb9eedb34436bb9ed16 found no remaining defect in scope and reproduced 108 focused tests. The response gate requires both prior findings explicitly fixed, a full reviewed commit equal to the focused packet source commit, and the actual SHA-256 of the focused artifact-hash manifest; missing, abbreviated, stale, synthetic, and mismatched identities fail closed. The normalized exact-candidate response passed the runtime closure preflight. This finding disposition does not close ERG-005 or authorize promotion, placement, release, UAT, production use, or new powers.
