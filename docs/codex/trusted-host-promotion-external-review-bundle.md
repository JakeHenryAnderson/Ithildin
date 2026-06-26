# Trusted-Host Promotion External Review Bundle

Status: reviewer launch bundle for `ERG-005`.

This document describes the generated bundle for the trusted-host promotion design-only lane. The
bundle exists to make external/source review easier by consolidating the source-review packet,
disposition packet, contracts, negative fixtures, response intake, closure gate, dry-run evidence,
queue status, command evidence, and artifact hashes into one handoff directory.

Generate it with:

```sh
make trusted-host-promotion-external-review-bundle
```

Validate wiring without regenerating the full handoff with:

```sh
make trusted-host-promotion-external-review-bundle-check
```

Default output:

```text
var/review-packets/v3/trusted-host-promotion-external-review/
```

## Generated Artifacts

The bundle contains exactly these review files plus one hash manifest:

1. `00_TRUSTED_HOST_PROMOTION_EXTERNAL_REVIEW_INDEX.md`
2. `01_TRUSTED_HOST_PROMOTION_EXTERNAL_REVIEW_PROMPT.md`
3. `02_TRUSTED_HOST_PROMOTION_SOURCE_PACKET.md`
4. `03_TRUSTED_HOST_PROMOTION_DISPOSITION_PACKET.md`
5. `04_TRUSTED_HOST_PROMOTION_CONTRACTS.md`
6. `05_TRUSTED_HOST_PROMOTION_FIXTURES_NEGATIVES.md`
7. `06_TRUSTED_HOST_PROMOTION_RESPONSE_CLOSURE_DRY_RUN.md`
8. `07_TRUSTED_HOST_PROMOTION_REPRODUCTION_QUEUE_STATUS.md`
9. `08_TRUSTED_HOST_PROMOTION_COMMAND_EVIDENCE.md`
10. `trusted-host-promotion-external-review-artifact-hashes.json`

## Review Question

The bundle asks whether `ERG-005` can continue design-only planning while trusted-host promotion,
direct host writes, overwrite/delete/move behavior, broad archive extraction, automatic promotion,
Mission Control runtime behavior, local model invocation, sandbox orchestration, SIEM adapters,
production identity, runtime Postgres, hosted telemetry, remote MCP, compliance automation,
public/security-product positioning, and new governed tool powers remain blocked.

The finding namespace is:

```text
EXT-TRUSTED-HOST-###
```

## Boundary

This bundle does not close `ERG-005`, does not record external review, and does not approve runtime
implementation planning. It is a handoff artifact only.

It does not approve:

- trusted-host promotion;
- direct host writes;
- overwrite/delete/move behavior;
- broad archive extraction;
- automatic promotion;
- promotion without exact artifact hash binding and approval evidence;
- Mission Control runtime behavior;
- local model invocation;
- VM/container lifecycle management;
- sandbox orchestration;
- SIEM adapter runtime behavior;
- production identity or runtime Postgres;
- compliance automation or public/security-product positioning.

## Validation

The check target verifies that:

- all generated bundle artifacts exist;
- artifact hashes cover the generated review files and do not hash the hash manifest itself;
- the prompt uses the `EXT-TRUSTED-HOST-###` finding namespace;
- command evidence keeps all blocked runtime flags false;
- README, docs site, review docs, enterprise queue, enterprise runway, and enterprise gap matrix
  reference this launch bundle;
- `release-check` includes `trusted-host-promotion-external-review-bundle-check`;
- `review-candidate` regenerates `trusted-host-promotion-external-review-bundle`.

The bundle is also included in `make review-candidate` so the v1.0 RC review packet can carry the
latest ERG-005 handoff alongside ERG-002 and ERG-003 without implying that any of those lanes are
closed.
