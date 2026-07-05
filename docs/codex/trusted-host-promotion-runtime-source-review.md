# Trusted-Host Promotion Runtime Source Review

Status: focused source-review handoff for the implemented staging-only `ERG-005` runtime slice.

Finding namespace: `EXT-TRUSTED-HOST-RUNTIME-###`.

## Scope

This source-review lane covers only the local-preview staging runtime:

- one stored sandbox/workspace artifact;
- one operator-created promotion proposal;
- one one-time approval;
- one placement into the configured local host-staging root;
- one read-only diagnostic/evidence surface.

It does not approve broad trusted-host promotion, arbitrary host paths, overwrite/delete/move
behavior, approved-output publishing, Mission Control runtime authority (historical name for the
current Ithildin Command Center runtime-authority boundary), sandbox orchestration,
SIEM adapter behavior, compliance automation, production identity, runtime Postgres, hosted
telemetry, remote MCP, shell, Docker, Kubernetes, browser automation, arbitrary HTTP, plugin SDK
behavior, or public/security-product positioning.

## Source Review Packet

Build the packet with:

```sh
make trusted-host-promotion-runtime-source-review-bundle
```

Validate packet wiring without regenerating command transcripts with:

```sh
make trusted-host-promotion-runtime-source-review-bundle-check
```

The generated packet lives under:

```text
var/review-packets/v3/trusted-host-promotion-runtime-source-review/
```

## Reviewer Questions

The reviewer should answer whether the staging-only runtime slice can be locally dispositioned for
continued local-preview development. If it cannot, the reviewer should record actionable findings
using `EXT-TRUSTED-HOST-RUNTIME-###`.

Review focus:

- admin-only route protection;
- absence of MCP/tool-manifest exposure;
- closed proposal/apply inputs;
- relative source artifact confinement;
- hidden, sensitive, symlink, hardlink, traversal, stale-hash, and replay denial;
- one-time approval binding and compare-and-set execution;
- create-exclusive host-staging placement with no overwrite behavior;
- safe API output and audit metadata;
- read-only diagnostics;
- no raw host path, file content, diff, prompt, or secret leakage.

## Current Internal Result

The internal source review result is recorded in
[`v3-trusted-host-promotion-runtime-internal-review.md`](v3-trusted-host-promotion-runtime-internal-review.md).
It found no critical/high implementation findings, but it is not an external closure decision.

The current internal closure addendum is recorded in
[`v3-trusted-host-promotion-runtime-review-closure.md`](v3-trusted-host-promotion-runtime-review-closure.md).
It preserves the same staging-only local-preview boundary and marks the lane
`local_reviewed_external_pending`.
