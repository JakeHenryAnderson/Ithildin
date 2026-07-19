# Trusted-Host Promotion Runtime Source Review

Status: exact-candidate source-review handoff for the implemented staging-only `ERG-005` runtime
slice and its `TGB-001` through `TGB-006` governance binding.

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

If a generated packet is present, the check also requires both packet commit labels to match the
current `HEAD`, requires the packet to report a clean generation tree, and verifies every recorded
artifact hash against the generated files. A missing generated packet does not fail source wiring
checks in a fresh checkout; a present stale or internally modified packet does fail. Regenerate the
packet on the exact clean candidate before review rather than relabeling packet files by hand.

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

The current local proxy disposition is recorded in
[`v3-trusted-host-promotion-runtime-local-disposition.md`](v3-trusted-host-promotion-runtime-local-disposition.md).
It records the external review and current bounded remediation posture. It is not external closure
and does not approve broader trusted-host promotion.

## External Review Result

An independent Sol xhigh packet-and-source review inspected exact commit
`63c7ffd47853ed2f5f132772ca1af264555456be` and the packet identified by
`sha256:4c4e741272339bd77cbc5174c0107db2ba2f77122276a00a2a2f3c385efc879f`.
It recorded `EXT-TRUSTED-HOST-RUNTIME-001` through `006` and returned
`block_runtime_source_review_closure`.

Exact-candidate re-review at commit `4dcf8ad26df4c3a6f4c2271d3fbe6c35566c67b6` confirmed
`001`, `003`, `004`, and the original scope of `005` fixed; it kept `002` blocking and `006`
partially remediated/deferred, and recorded the new medium packet-integrity finding
`EXT-TRUSTED-HOST-RUNTIME-007`.

The current bounded remediation candidate also fixes `007` by making the generated packet embed
self-evidence for the newly generated exact candidate. Re-review of commit
`8755a39585993fc057cfd30564cb867098cf7f52` confirmed that behavior but recorded
`EXT-TRUSTED-HOST-RUNTIME-008`: an interrupted, hash-consistent intermediate packet could still
pass the public checker with contradictory embedded evidence. The current candidate fixes `008` by
requiring embedded packet evidence to match live packet evidence.

The governance-binding architecture, authorization record, and `TGB-001` through `TGB-006`
implementation packet now govern the current candidate; the former statement that complete binding
was only a deferred architecture decision is historical. A later exact-candidate review found that
the service still reused startup-cached runtime-candidate evidence instead of rehashing the closed
installed inventory immediately before reservation. That kept `EXT-TRUSTED-HOST-RUNTIME-002` and
`EXT-TRUSTED-HOST-RUNTIME-006` deferred.

The current remediation retains the startup-selected verifier paths, freshly verifies the closed
installed inventory during apply-time authority recomputation, terminally stales the proposal on
verification failure before reservation, and adds a direct post-approval installed-file drift
proof with no attempt or staging effect. Those changes remain an implementation candidate until a
fresh exact-candidate independent response is normalized and separately triaged. `ERG-005`, broad
trusted-host promotion, release authorization, and UAT remain blocked.

The committed finding records live under `docs/codex/findings/` with the
`EXT-TRUSTED-HOST-RUNTIME-###` namespace.
