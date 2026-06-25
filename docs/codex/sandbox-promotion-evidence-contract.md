# Sandbox Promotion Evidence Contract

Status: design-only evidence contract.

This contract defines the evidence required when an artifact moves from a sandbox/staging root back
to a trusted host location. It does not implement promotion, copying, approval mutation, filesystem
writes, VM orchestration, Mission Control behavior, or SIEM export.

The contract is a future review shape only. Today, `sandbox.artifact.write_text` can create bounded
sandbox-labeled artifacts through Ithildin, and the Hello World Mission Control handoff can display
evidence about that observed flow. Trusted-host promotion remains blocked until a separate proposal,
implementation plan, implementation gate, source review, negative transcripts, and release
readiness wiring explicitly approve it.

## Required Evidence Fields

```json
{
  "schema_version": "1",
  "promotion_id": "promotion_...",
  "mission_id": "mc-demo-...",
  "run_id": "run_...",
  "workspace_id": "demo",
  "sandbox_id": "local-demo-sandbox",
  "source_artifact_label": "sandbox://hello-demo/hello.txt",
  "source_artifact_sha256": "sha256:...",
  "host_staging_label": "host-staging://hello-demo/hello.txt",
  "host_staging_sha256": "sha256:...",
  "approved_host_label": "approved://hello-demo/hello.txt",
  "approved_host_sha256": "sha256:...",
  "approval_id": "appr_...",
  "operator_principal": "admin:local-ui",
  "policy_hash": "sha256:...",
  "manifest_hash": "sha256:...",
  "created_at": "timestamp",
  "auto_promotion_performed": false
}
```

## Required Checks

- sandbox source hash equals host staging hash;
- host staging hash equals approved host hash;
- approval ID is present before trusted host placement;
- promotion target is not hidden, `.git`, symlink, hardlink, or outside the approved host root;
- no file contents, prompts, secrets, VM logs, shell output, or unrelated directory listings are
  recorded;
- no raw host paths are recorded.

## Operator Review States

- `not_promoted`: the default state for current Hello World and sandbox artifact demos.
- `promotion_requested`: a future operator has asked to move an artifact toward trusted-host
  staging, but no host write has occurred.
- `promotion_approved`: a future approval binds the exact artifact hash, staging label, approved
  host label, policy hash, manifest hash, operator principal, and expiry.
- `promotion_completed`: a future implementation records matching source, staging, and approved
  hashes after the copy occurs.
- `promotion_rejected`: promotion is denied or abandoned and no trusted-host write occurs.

Current packets may record `promotion_status: not_promoted` only.
Any other state requires a future explicitly approved promotion implementation.

## Zone Labels

Promotion evidence should use labels, not raw host paths:

- `sandbox://...` for the source artifact label;
- `host-staging://...` for a reviewed staging label;
- `approved://...` for the final approved host label.

These labels are not filesystem authority by themselves. They are evidence identifiers that must be
resolved by a future explicitly approved promotion implementation.

## Non-Goals

This contract is not a SIEM adapter, custody-grade audit, compliance automation, production identity
system, host sandbox, VM controller, Mission Control runtime behavior, sandbox orchestration, or
broad write approval. It is an evidence shape for a future explicitly approved promotion
implementation.
