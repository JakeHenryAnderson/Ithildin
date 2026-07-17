# Track B Node Release Artifact Capability Decision

Status: **approved for bounded local operator signing and verification of one Node OCI image**.

Decision date: 2026-07-16

Current governed tool count: `24`.

## Decision

Ithildin may provide an offline operator utility that creates a closed, Ed25519-signed Node release
artifact manifest from a clean Git checkout and an already built local OCI image. The manifest may
bind the exact local image ID, explicit image reference, Node version, clean source commit,
Dockerfile digest, dependency-lock digest, OS and architecture, unprivileged user, fixed Node
entrypoint, zero exposed ports, and creation time.

Verification requires a separately supplied trusted public key and an explicit operator-selected
local image reference. It validates the closed schema, domain-separated signature, key identity,
selected reference, local image ID, platform, runtime shape, version label, and source-revision
label. A mutable tag alone is never sufficient.

The Node release-artifact trust root is dedicated. Audit-export, tool-manifest-lock,
Node-configuration, and Node-identity keys must not be reused.

## Required Safety Semantics

- Signing refuses a dirty or unavailable Git checkout.
- Signing refuses a Node image whose version or source-revision labels do not match the requested
  version and clean checkout commit.
- The private key must be a regular non-symlink file with mode `0600`; generated public keys use
  mode `0644`.
- Verification fails closed for unknown fields, malformed values, signature tampering, untrusted
  keys, a different operator-selected image reference, a changed local image ID, exposed ports,
  root execution, or an unexpected entrypoint.
- Safe output contains only digests, version, commit, key ID, boolean posture, and a bounded failure
  reason. It contains no private key, credential, image layer, environment value, or source body.

## Explicit Non-Approvals

This decision does not approve an image registry, image upload or download, Node self-update,
package installation, automatic upgrade or rollback, update rings, group rollout, service-manager
control, runner lifecycle control, Docker socket access by Ithildin, Kubernetes behavior, Gateway
artifact enforcement, remote attestation, build-system attestation, reproducible-build claims,
SBOM or vulnerability claims, transparency-log anchoring, HSM/KMS custody, code signing,
notarization, official hosted supply-chain signing, production identity, or a new governed tool.

A valid manifest proves that the local operator key signed the observed manifest and that the
currently selected local image matches it. It does not prove who controlled the build host, whether
the source was independently reviewed, whether dependencies are safe, or whether the image later
reported the same version to the Gateway.

Tests and generated evidence do not authorize deployment, promotion, release, UAT acceptance, or
public security-product claims.
