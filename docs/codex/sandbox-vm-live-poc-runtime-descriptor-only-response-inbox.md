# Sandbox/VM Live POC Runtime Descriptor-Only Response Inbox

Status: generated response inbox for the active ERG-004 runtime descriptor-only review.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Run:

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-response-inbox
make sandbox-vm-live-poc-runtime-descriptor-only-response-inbox-check
```

This inbox creates ignored local artifacts under:

```text
var/review-runs/sandbox-vm-live-poc-runtime-descriptor-only-response-inbox/
```

It gives the active `EXT-LIVE-DESC-###` response path an exact raw-response placeholder, reviewed
packet hash, and normalization command for the current descriptor-only source-review packet:

```text
var/review-packets/v3/sandbox-vm-live-poc-runtime-descriptor-only-source-review
```

## What It Does

- Creates `RAW_RESPONSE_ERG-004-DESCRIPTOR-ONLY.md`.
- Creates `ERG004_RUNTIME_DESCRIPTOR_ONLY_CHEATSHEET.md`.
- Creates `erg004-runtime-descriptor-only-response-inbox.json`.
- Creates `erg004-runtime-descriptor-only-response-inbox-artifact-hashes.json`.
- Records the exact `sandbox-vm-live-poc-runtime-descriptor-only` normalization area.
- Records the `EXT-LIVE-DESC-###` finding namespace.
- Records the reviewed packet hash for the generated descriptor-only source-review packet.

## What It Does Not Do

This inbox does not normalize responses, does not write normalized response files, does not mutate
findings, does not record external review, does not close `ERG-004`, does not approve descriptor-only local preview disposition, does not approve runtime implementation, approve live VM/container
inspection, approve VM/container lifecycle management, approve sandbox orchestration, approve Mission
Control runtime behavior, approve local model invocation, approve trusted-host promotion, approve
host writes, approve network expansion, approve API/MCP profile loading, approve SIEM adapter
behavior, approve new governed tool powers, or approve public/security-product positioning.

## Use Order

1. Run `make sandbox-vm-live-poc-runtime-descriptor-only-response-inbox`.
2. Paste a real `EXT-LIVE-DESC-###` reviewer response into the generated raw-response placeholder.
3. Use the generated cheat sheet's normalizer command so the reviewed packet hash is exact.
4. Run `make sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run`.
5. Run `make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check`.
6. Commit a later manager-owned disposition update only if the normalized response explicitly
   supports the allowed transition and no critical/high `EXT-LIVE-DESC-###` finding is open.

The only later transition this path can support is:

```text
descriptor_only_runtime_implemented_source_review_pending -> descriptor_only_local_preview_disposition_ready
```

That transition still does not approve runtime implementation.

## Validation

Run:

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-response-inbox-check
make sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake-check
make sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run
make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check
```
