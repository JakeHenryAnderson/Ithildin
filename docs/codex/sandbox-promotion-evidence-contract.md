# Sandbox Promotion Evidence Contract

Status: design-only evidence contract.

This contract defines the evidence required when an artifact moves from a sandbox/staging root back
to a trusted host location. It does not implement promotion, copying, approval mutation, filesystem
writes, VM orchestration, Mission Control behavior, or SIEM export.

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
- no file contents, prompts, secrets, raw host paths, VM logs, shell output, or unrelated directory
  listings are recorded.

## Non-Goals

This contract is not a SIEM adapter, custody-grade audit, compliance automation, production identity
system, host sandbox, VM controller, or broad write approval. It is an evidence shape for a future
explicitly approved promotion implementation.
