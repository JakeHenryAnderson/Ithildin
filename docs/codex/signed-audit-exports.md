# Signed Audit Exports

Ithildin can produce a local Ed25519-signed audit export bundle. This is v0.2 trust evidence: it
helps prove that a copied export has not changed since it was signed by a local key. It is not
external notarization, hosted custody, or a guarantee that the local runtime cannot be changed before
export.

## Key Setup

Generate a local signing keypair:

```sh
make audit-keygen
```

The default paths are:

- private key: `var/keys/audit-ed25519-private.pem`
- public key: `var/keys/audit-ed25519-public.pem`

The API does not create signing keys automatically. Keep the private key local and outside version
control. If the private key is lost, old signed exports can still be checked with the public key, but
new exports need a new keypair and will have a different key ID.

## Export

The existing JSONL export remains available:

```sh
curl -H "Authorization: Bearer $ITHILDIN_ADMIN_TOKEN" \
  http://127.0.0.1:8000/audit-events/export \
  -o ithildin-audit-export.jsonl
```

After key generation, download a signed JSON bundle:

```sh
curl -H "Authorization: Bearer $ITHILDIN_ADMIN_TOKEN" \
  http://127.0.0.1:8000/audit-events/export/signed \
  -o ithildin-audit-export-signed.json
```

The review console also exposes separate JSONL and signed export actions.

## Verify

Verify a signed bundle with the embedded public key:

```sh
make audit-export-verify FILE=ithildin-audit-export-signed.json
```

Verify against a trusted public key file:

```sh
make audit-export-verify FILE=ithildin-audit-export-signed.json \
  PUBLIC_KEY=var/keys/audit-ed25519-public.pem
```

Verification checks the Ed25519 signature, the event JSONL digest, and the embedded audit hash chain.
The signed bundle records audit verification status at export time, including failed verification if
the local audit chain was already tampered or truncated.

## Demo Verification

For review packets, generate and verify the non-production signed-evidence demo:

```sh
make signed-evidence-demo
make signed-evidence-demo-verify
```

The verifier re-checks the signed audit demo bundle with the demo public key, confirms the tampered
audit demo bundle fails verification, and verifies the demo manifest-lock signature. This is local
fixture evidence only; runtime signing may still be unconfigured by default.
