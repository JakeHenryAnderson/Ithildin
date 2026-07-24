# Local v1 LV1-002 Exact Review

Status: `GO`

- Milestone: `LV1-002`
- Release outcome: `O3`
- Runtime-evidence candidate: `fabdba7ee81d4ecca4353559dd109ff0008d8091`
- Evidence run: `20260724T163316Z-9b94b8da`
- Review date: `2026-07-24`
- Reviewer: independent GPT-5.6 Sol xhigh
- Critical findings: `0`
- High findings: `0`
- Medium findings: `0`
- Low findings: `0`

## Disposition

The exact candidate and retained evidence are sufficient to mark `O3` and `LV1-002` complete. The
reviewed implementation candidate was clean and pushed before the journey ran. The later durable
documentation commit records that result; it is not replacement runtime evidence.

The live command completed once against the exact candidate:

```sh
make local-v1-node-journey
```

The printed success-only checker then passed against the explicit run and candidate:

```sh
make local-v1-node-journey-check \
  LOCAL_V1_NODE_JOURNEY_REPORT=var/local-v1-node-journey/20260724T163316Z-9b94b8da \
  LOCAL_V1_NODE_JOURNEY_CANDIDATE=fabdba7ee81d4ecca4353559dd109ff0008d8091
```

## Retained Evidence

- JSON:
  `var/local-v1-node-journey/20260724T163316Z-9b94b8da/local-v1-node-journey.json`
- JSON SHA-256: `205ca4fceef1e98b044ed36d9f2d68723c4a6ca693aa2b6b74725507b5c3d54b`
- Markdown:
  `var/local-v1-node-journey/20260724T163316Z-9b94b8da/local-v1-node-journey.md`
- Markdown SHA-256: `54395aa267612511ee8764e33eb082328e1b541caa986e292ac422e75f1dcfb7`
- File modes: owner read/write only (`0600`)

The checker bound the report to the exact candidate, clean start and finish observations, fresh
timestamps, a completed result, exact closed fields, deterministic Markdown rendering, complete
cleanup, all-false authority fields, and the required nonclaims.

## Final Recovery Lineage

Before the successful run, exact-reviewed intermediate candidate
`26da66cb60e24445d9ba478453411e429e102c3c` passed the authenticated system-status readiness stage
but failed closed at Node-inventory projection with `gateway_response_contains_secret_fields`.
Retained run `20260724T154527Z-1b08248f` has JSON SHA-256
`3653a775cc5b1e3bb3f2eee0c2056350ac4f992ea2fd2e61bc797ffd74f9563b` and Markdown SHA-256
`f287950e1c507add182390d0f0bed757ba727c20cece4e5f618de7319cbd70f3`.

The failed run had a safely known, revoked Node identity and required no enrollment recovery. Its
profile-owned volume survived the original teardown command. After exact read-only inspection, that
single synthetic volume and run-specific runtime directory were permanently removed. Candidate
`fabdba7ee81d4ecca4353559dd109ff0008d8091` then added the closed Node-inventory projection and
profile-aware teardown used by the successful run. This lineage records the failed attempt and
cleanup; it does not turn either into success evidence.

## Observed Acceptance Evidence

- The normal API and Command Center stack was healthy with SQLite, the `unreviewed_local` runtime
  posture, and the fixed 24-tool surface.
- The active `demo` workspace was selected from Gateway inventory.
- The one-time code was returned once, sent only through Compose stdin, and not recorded.
- The Gateway derived and bound the Node ID, `agent:node.<node_id>` principal, and workspace.
- Signed configuration generation `1` and its digest matched assignment, desired state,
  acknowledgement, and last-observed configuration.
- Configuration truth remained `stored_not_enforced` and `stored_current_not_enforced`.
- Connectivity was specifically a Gateway-accepted heartbeat; runner and model-provider health
  remained separately unknown.
- Gateway revocation completed and a subsequent signed heartbeat was rejected.
- The redaction scan found zero forbidden-value or generic-secret matches and recorded no raw HTTP
  headers, bodies, or subprocess output.

## Cleanup And Authority

Cleanup completed with Node stop and revocation, Compose teardown, run-specific image, resource,
and volume removal, and isolated runtime-state removal. Direct read-only inspection found no
retained run-specific containers, volumes, networks, images, or runtime files.
`recovery_required` is false.

All runtime, release, promotion, production identity/storage, and UAT authority fields remain
false. This evidence does not authorize another live retry, release, promotion, production use, or
UAT completion.

## Remaining Nonclaims

- No governed tool call or real agent mission was exercised.
- No runner or model-provider health was established.
- Configuration was stored and acknowledged, not enforced.
- No restart, replay, partition, stale-configuration, or rollback behavior was exercised.
- No production identity, PostgreSQL, release, promotion, or UAT authority was established.
- Candidate identity and cleanliness are observations, not authorization or approval.

This closes only `O3` and `LV1-002`. It does not close `O1`, `O2`, `O4` through `O8`, the Local-v1
release gate, release acceptance, or human UAT. `MCC-007` remains a separate bounded capability
decision for `LV1-003`; this record does not authorize its implementation.
