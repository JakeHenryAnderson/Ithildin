# Production Identity And Storage External Review Bundle

Status: launch bundle for `ERG-006` and `ERG-007` external architecture/source review.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Current `ERG-006` status before reviewer disposition: `planning_only`.

Current `ERG-007` status before reviewer disposition: `planning_only`.

Generate the bundle with:

```sh
make production-identity-storage-external-review-bundle
```

Validate the bundle wiring with:

```sh
make production-identity-storage-external-review-bundle-check
```

Output directory:

```text
var/review-packets/v3/production-identity-storage-external-review/
```

## Purpose

This is the reviewer-friendly launch artifact for the production identity and durable storage
architecture lane. It consolidates the architecture/disposition packet, response-intake template,
fail-closed closure gate, response dry-run evidence, queue status, and command evidence into a
single attachment-friendly handoff.

The review question is narrow:

> Can `ERG-006` and `ERG-007` continue architecture planning while runtime implementation,
> production identity, runtime Postgres, enterprise RBAC, remote admin, and hosted control-plane
> behavior remain blocked?

## Artifact Shape

The generated bundle contains:

- `00_PRODUCTION_IDENTITY_STORAGE_EXTERNAL_REVIEW_INDEX.md`
- `01_PRODUCTION_IDENTITY_STORAGE_EXTERNAL_REVIEW_PROMPT.md`
- `02_PRODUCTION_IDENTITY_STORAGE_DISPOSITION_PACKET.md`
- `03_PRODUCTION_IDENTITY_STORAGE_ARCHITECTURE_CONTRACTS.md`
- `04_PRODUCTION_IDENTITY_STORAGE_RESPONSE_CLOSURE_DRY_RUN.md`
- `05_PRODUCTION_IDENTITY_STORAGE_REPRODUCTION_QUEUE_STATUS.md`
- `06_PRODUCTION_IDENTITY_STORAGE_BOUNDARY_EVIDENCE.md`
- `07_PRODUCTION_IDENTITY_STORAGE_COMMAND_EVIDENCE.md`
- `production-identity-storage-external-review-artifact-hashes.json`

## Non-Goals

This launch bundle does not close `ERG-006` or `ERG-007`, does not record external review, and
does not approve implementation planning, production identity, enterprise RBAC, tenant/team
authorization runtime behavior, remote admin use, runtime Postgres, database migrations,
backup/restore runtime behavior, retention enforcement, hosted control plane, custody-grade audit
claims, compliance automation, hosted telemetry, remote MCP, SIEM adapter runtime behavior,
sandbox orchestration, local model invocation, trusted-host promotion, shell/Docker/Kubernetes/
browser governed powers, arbitrary HTTP, broad filesystem writes, plugin SDK behavior,
public/security-product positioning, or any new governed tool power.

`production-identity-storage-disposition-closure-gate.md` remains fail-closed until normalized
source-level response evidence exists. A separate committed triage update and post-RC decision
record are required before this lane can move beyond planning-only architecture work.

## Verification

The check command verifies:

- all bundle artifacts are generated;
- artifact hashes cover generated markdown files and exclude the hash manifest itself;
- the prompt uses `EXT-PROD-IAM-STORAGE-###`;
- command evidence includes fail-closed boundary flags;
- response intake, closure gate, and dry-run evidence are bundled;
- README, docs-site, review-doc metadata, release guardrails, release-check, review-candidate, and
  the enterprise queue all point to the launch bundle.
