# v3 Trusted-Host Promotion Runtime Internal Review

Status: internal source review pass for the staging-only `ERG-005` runtime slice.

Review date: 2026-07-05.

Reviewer: Codex internal source review.

Reviewed scope:

- `apps/api/src/ithildin_api/trusted_host_promotions.py`
- `apps/api/src/ithildin_api/app.py`
- `apps/api/src/ithildin_api/config.py`
- `tests/test_api_service.py`
- `scripts/trusted_host_promotion_negative_transcripts.py`
- `docs/codex/trusted-host-promotion-runtime-implementation.md`

Internal finding namespace: `INT-TRUSTED-HOST-RUNTIME-###`.

External/source-review finding namespace for the next handoff:
`EXT-TRUSTED-HOST-RUNTIME-###`.

## Overall Judgment

No critical or high implementation findings were found in this internal pass for the local-preview
staging-only slice.

The lane is locally reviewed for continued local-preview development and ready for focused external
or human source review. This does not approve broad trusted-host promotion, arbitrary host writes,
approved-output publishing, Mission Control runtime authority (historical name for the current
Ithildin Command Center runtime-authority boundary), sandbox orchestration, SIEM custody,
compliance automation, production positioning, or public/security-product claims.

## Claims Tested

| Claim | Evidence inspected | Result |
| --- | --- | --- |
| Admin-only runtime surface | FastAPI route dependencies for `/trusted-host-promotions/*` | no finding |
| No new governed tool or MCP exposure | no manifest/MCP changes; tool count remains `24` | no finding |
| One artifact only | proposal schema accepts one source artifact path and one staging label | no finding |
| Approval-gated staging | proposal creates pending approval; apply requires approved one-time approval | no finding |
| Replay fails closed | approval compare-and-set execution path rejects executed approvals | no finding |
| Stale artifact rejected | source artifact is re-read and hash-checked before staging | no finding |
| No raw host paths accepted | API accepts `host-staging://` label only, destination resolved from local config | no finding |
| No overwrite | destination write uses create-exclusive open | no finding |
| Safe outputs | API/audit metadata include IDs, labels, hashes, sizes, statuses, and output policy only | no finding |
| Diagnostics read-only | diagnostics report state and recommendations without repair or retry behavior | no finding |

## Residual Risks

- This is an internal review, not external closure.
- The local host remains trusted computing base.
- The staging root is local operator-managed storage, not custody-grade evidence.
- Destination labels are intentionally narrow and not a general host-transfer system.
- Promotion to `approved://` output remains unimplemented and requires a separate decision.

## Findings

No actionable findings were recorded in this pass.

## Follow-Up Queue

- Use the closure addendum in
  [`v3-trusted-host-promotion-runtime-review-closure.md`](v3-trusted-host-promotion-runtime-review-closure.md)
  and the focused runtime source-review bundle before treating `ERG-005` as externally dispositioned.
- Keep capability expansion blocked unless the source-review bundle returns no blocking findings.
- Defer approved-output publishing, Mission Control runtime integration, sandbox orchestration,
  SIEM adapter behavior, and compliance mapping runtime to separate milestones.

## TGB-005 Follow-Up Trust Review

Review date: 2026-07-18.

Reviewer: Codex Sol xhigh read-only trust review.

Reviewed scope included the version-3 migration, trusted-host approval dispatch, proposal/apply and
diagnostic responses, production-readiness construction, completion audit ordering and concurrency,
Command Center evidence rendering, accessibility behavior, redaction tests, and the final worktree
validation results.

Disposition: pass for the `TGB-005` implementation candidate. No unresolved critical, high, or
claim-affecting-medium finding remains. The review does not constitute the independent external
source review required by `TGB-006` and does not authorize broader capability or product claims.

Remediated findings:

- trusted-host approval review now uses its own binding-aware reviewer instead of patch review;
- audit-chain head selection and persistence are serialized under one SQLite write transaction;
- production readiness independently verifies the candidate, detached authorization, database,
  YAML policy, enforced registries, 24-tool manifest lock, input schema, placement primitives,
  staging-root descriptor, and disabled internal fixtures;
- malformed authority evidence and migrated legacy recovery records fail safely into operator
  review states;
- denied, expired, and superseded approvals use server-derived effective states and the Command
  Center states that approval closed without placement;
- schema-2-to-schema-3 table copies use explicit columns; and
- Evidence navigation has visible programmatic focus with semantic, non-color-only state text.

One nonblocking low advisory remains: Command Center currently fetches the proposal list and
diagnostics separately, so a lifecycle transition between those responses can briefly show two
different Gateway snapshots until refresh. Both surfaces remain server-returned Gateway truth. A
future bounded cleanup may consume the proposal list embedded in the diagnostics response to render
one snapshot.
