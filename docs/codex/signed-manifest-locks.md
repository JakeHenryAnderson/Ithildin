# Signed Manifest Locks

Ithildin can sign `tool-manifests.lock.json` with a local Ed25519 keypair. This is operator-local
trust evidence for the committed manifest lock. It is not external notarization, official hosted
supply-chain signing, or a plugin marketplace trust model.

## Key Setup

Generate a separate manifest-lock signing keypair:

```sh
make manifest-lock-keygen
```

Default paths:

- private key: `var/keys/manifest-lock-ed25519-private.pem`
- public key: `var/keys/manifest-lock-ed25519-public.pem`
- signature bundle: `var/signatures/tool-manifests.lock.sig.json`

Generated keys and signatures are local runtime state and are ignored by git.

## Sign And Verify

After intentional manifest edits:

```sh
make manifest-lock
make manifest-lock-check
make manifest-lock-sign
make manifest-lock-signature-check
```

`make manifest-lock-sign` signs the canonical current lock payload and records the lock digest, key
ID, algorithm, created timestamp, and signature. `make manifest-lock-signature-check` verifies the
signature against the current lock and trusted public key.

## Runtime Enforcement

Manifest hash-lock verification remains enabled by default through
`ITHILDIN_REQUIRE_MANIFEST_LOCK=true`.

Signed-lock enforcement is opt-in:

```sh
ITHILDIN_REQUIRE_SIGNED_MANIFEST_LOCK=true
```

When enabled, API and MCP startup fail closed if the signature bundle, public key, current lock
digest, key ID, or Ed25519 signature does not verify. When disabled, `/system/status` and
`make release-evidence` report unsigned or unverifiable status without blocking startup.
