# Track B Node Release Artifact Implementation Plan

Status: approved bounded implementation plan.

Current governed tool count: `24`.

## Milestones

1. Define closed Pydantic models for the OCI artifact, platform, runtime, signature, and bundle.
2. Add dedicated mode-0600 Ed25519 key generation with usage-bound key IDs and no reuse of other
   Ithildin trust roots.
3. Add signing that requires a clean checkout and matching image version/source-revision labels,
   then binds the immutable image ID, source inputs, and no-listener unprivileged runtime shape.
4. Add verification requiring a separately trusted public key and explicit selected image
   reference, then compare the signed artifact against fresh local Docker inspection.
5. Add operator CLI and Make targets for clean image build, key generation, signing, and
   verification. No command accepts a registry credential, Docker socket path, package URL, or
   service action.
6. Cover valid verification, signature tamper, wrong selected reference, wrong local image,
   untrusted key, dirty source, permissive or linked private key, version/revision mismatch, root
   user, exposed port, and unexpected entrypoint.
7. Run a live proof from an exact clean commit: build the labeled image, sign it, verify it, reject
   tampering and a substituted image, and verify an explicitly selected prior signed artifact for
   operator-managed rollback evidence.
8. Run focused checks, `make release-check`, and `make review-candidate` before closing the
   checkpoint.

## Stop Conditions

Stop if implementation requires registry access, image transfer, package installation, Docker
socket access by Ithildin, service control, automatic upgrade/rollback, Gateway enforcement, a new
runtime API, a tool-count change, or a claim stronger than local signed operator evidence.
