# Track B Node Release Artifact Architecture

Status: approved architecture for bounded local operator evidence.

Current governed tool count: `24`.

## Trust And Selection Flow

```text
clean Git commit + locked inputs + already built local OCI image
        |
        | dedicated local Ed25519 release-artifact key
        v
closed signed manifest: reference + immutable image ID + source/runtime posture
        |
        | trusted public key + explicit operator-selected local reference
        v
signature validation -> local image inspection -> exact ID/runtime/label comparison
        |
        v
safe valid/invalid operator evidence; no Gateway or service-manager action
```

The signature message is domain-separated as
`ITHILDIN-NODE-RELEASE-ARTIFACT-V1` and covers the full closed artifact plus signature metadata.
The trusted public key is supplied separately; an embedded public key is never self-authenticating.
The key ID includes algorithm, raw public key, and the dedicated release-artifact usage.

## Closed Artifact

The signed artifact contains only:

- `oci_image` artifact kind, selected reference, exact `sha256` image ID, and available repository
  digests;
- closed `MAJOR.MINOR.PATCH` Node version;
- clean 40-hex Git commit and `source_dirty: false`;
- raw SHA-256 digests of `deploy/Dockerfile.node` and `uv.lock`;
- timezone-aware creation time;
- Linux OS, closed architecture token, UID/GID `10002:10002`, exact
  `python -m ithildin_node` entrypoint, and an empty exposed-port list.

Unknown fields fail schema validation. The manifest does not contain environment variables, image
history, layers, source contents, credentials, private keys, or runner configuration.

## Upgrade And Rollback Meaning

Before an operator-managed replacement, the operator verifies the intended local image against its
signed manifest and trusted release public key. Rollback uses the same process with the previously
approved manifest and local image. Ithildin does not choose either artifact and does not perform the
replacement. Gateway version posture remains a separate later signed Node assertion, not proof that
the verified image ran.

## Non-Claims

This is local operator evidence, not official supply-chain signing, remote attestation, build
attestation, a transparency log, an updater, a registry, package provenance beyond the signed local
observation, Gateway enforcement, runner control, or production key custody.
