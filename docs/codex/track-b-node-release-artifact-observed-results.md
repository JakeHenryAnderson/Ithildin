# Track B Node Release Artifact Observed Results

Status: **observed local signed OCI artifact POC passed** on 2026-07-16.

Evidence root: ignored local path `var/node-release-artifact-poc-20260716`.

Current governed tool count: `24`.

## Observed Sequence

1. A clean Ithildin checkout built two local Node OCI images with the digest-pinned base image,
   dependency lock, explicit version label, and exact source-revision label: current `0.1.0` and
   prior rollback selection `0.0.9`.
2. A dedicated local Ed25519 Node release-artifact keypair was generated. The private key was mode
   `0600`, the public key was mode `0644`, and its usage-bound key ID was distinct from Ithildin's
   audit, manifest-lock, Node-configuration, and Node-identity trust roots.
3. The operator utility created a closed signed manifest for each image. Each bound the explicit
   image reference, immutable local image ID, version, clean source commit, Dockerfile and lockfile
   digests, Linux architecture, UID/GID `10002:10002`, fixed Node entrypoint, and zero exposed ports.
4. Verification required the trusted public key and the explicitly selected local reference. Both
   the current and prior rollback artifacts verified successfully, and their immutable image IDs
   were distinct.
5. Changing the signed Dockerfile digest invalidated the signature.
6. Presenting the current manifest while explicitly selecting the rollback reference was denied.
7. Verification with an independently generated untrusted public key was denied.
8. Retargeting the mutable current tag to the prior image was denied because the freshly inspected
   local image ID no longer matched the signed artifact. The original tag was restored afterward.
9. A dirty cloned checkout was denied before signing.
10. Safe evidence retained only public metadata, digests, bounded failures, and nonclaim posture;
    private signing material was absent and the governed tool count remained 24.

## Reproduce

```sh
uv run python scripts/node_release_artifact_poc.py --replace
make track-b-node-release-artifact-evidence-check
```

The POC requires a clean checkout. It builds only local images, creates only ignored local evidence,
uses no registry credential or Docker socket inside Ithildin, and restores the current tag after the
substitution test. `--replace` deletes only the selected generated POC evidence root under
repository `var/`.

## Evidence Claim

The highest supported claim is
`local_signed_node_oci_selection_and_rollback_artifact_evidence`.

This proves that the dedicated local operator key signed the closed manifests and that the
explicitly selected local current and rollback images matched their immutable IDs, clean source
commit, locked-input digests, labels, platform, and closed runtime posture in the observed fixture.

It does not prove registry provenance, image transfer, who controlled the build host, reproducible
builds, remote or build-system attestation, source review, dependency safety, SBOM completeness,
vulnerability status, transparency-log inclusion, HSM/KMS custody, code signing, notarization,
official hosted supply-chain signing, Gateway enforcement, Node self-update, automatic rollback,
runner control, production readiness, release approval, or human UAT.
