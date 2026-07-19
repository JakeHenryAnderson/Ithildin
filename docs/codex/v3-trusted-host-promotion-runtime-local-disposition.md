# v3 Trusted-Host Promotion Runtime Local Disposition

Status: external review received; bounded remediation candidate implemented; closure remains blocked.

Disposition date: 2026-07-06.

Reviewer: Codex manager source review.

Disposition: `external_review_received_remediation_pending`.

Historical internal disposition: `local_disposition_ready_external_pending`.

Finding namespace: `EXT-TRUSTED-HOST-RUNTIME-###`.

## Scope

This disposition records a final local pass over the current staging-only trusted-host promotion
runtime slice after the Command Center naming cleanup and runtime closure addendum.

Reviewed evidence:

- `apps/api/src/ithildin_api/trusted_host_promotions.py`
- `tests/test_api_service.py`
- `docs/codex/trusted-host-promotion-runtime-implementation.md`
- `docs/codex/v3-trusted-host-promotion-runtime-internal-review.md`
- `docs/codex/v3-trusted-host-promotion-runtime-review-closure.md`
- `docs/codex/trusted-host-promotion-runtime-source-review.md`
- `docs/codex/ithildin-command-center-boundary.md`

## External Review Update

An independent packet-and-source review of exact commit
`63c7ffd47853ed2f5f132772ca1af264555456be` recorded six findings:

- `EXT-TRUSTED-HOST-RUNTIME-001` and `EXT-TRUSTED-HOST-RUNTIME-002` were high and blocking;
- `EXT-TRUSTED-HOST-RUNTIME-003` through `EXT-TRUSTED-HOST-RUNTIME-006` were medium and
  should-fix;
- the overall disposition was `block_runtime_source_review_closure`.

Exact-candidate re-review at commit `4dcf8ad26df4c3a6f4c2271d3fbe6c35566c67b6` confirmed
`001`, `003`, `004`, and the original scope of `005` fixed. It kept `002` blocking and `006`
partially remediated/deferred, and recorded a seventh finding,
`EXT-TRUSTED-HOST-RUNTIME-007`, for contradictory embedded packet self-evidence.

The current remediation candidate also fixes `007` with two-pass packet generation and final
exact-candidate self-validation. Re-review of commit
`8755a39585993fc057cfd30564cb867098cf7f52` confirmed that behavior and recorded an eighth finding,
`EXT-TRUSTED-HOST-RUNTIME-008`, because an interrupted, hash-consistent intermediate packet could
still pass the public checker with contradictory embedded evidence. The current candidate fixes
`008` by requiring embedded packet evidence to match live packet evidence.

That review state kept `002` and `006` deferred until an explicit architecture, completed TGB
implementation, packet-bound governance-drift evidence, and exact-candidate independent re-review
were available.

The final TGB remediation re-review inspected exact clean commit
`919858e8d5886129d7c1fefc730795380cd45f73` and focused packet manifest
`sha256:02b060bb65d41b317b3a426cd1ad9786d101683303622cb9eedb34436bb9ed16`. It found no
remaining defect in the requested scope and dispositioned `002` and `006` as `fixed`. The
normalized response passed the exact runtime closure preflight and reached
`runtime_source_review_ready_for_triage`. `ERG-005` remains blocked, and no runtime placement,
broader promotion, release, UAT, production-use, or new-power authority is created by this result.

## Historical Local Disposition

No critical, high, medium, low, or informational findings were recorded in the earlier internal
proxy disposition. That historical result has been superseded by the external findings above.

The staging-only `ERG-005` runtime slice is locally dispositioned for continued local-preview
development and focused source-review handoff. This is not external closure and does not approve
broader trusted-host promotion.

The local disposition covers only:

- one stored sandbox/workspace artifact;
- one operator-created promotion proposal;
- one one-time approval;
- one create-exclusive placement into the configured local host-staging root;
- read-only diagnostics and safe evidence surfaces.

## Source Claims Rechecked

| Claim | Evidence | Result |
| --- | --- | --- |
| Runtime routes are admin protected | API tests require bearer auth for proposal/apply/diagnostics paths | no finding |
| No MCP or governed-tool surface was added | Runtime slice is an admin API path; tool count remains `24` | no finding |
| Inputs are bounded | Proposal/apply models reject unsupported fields, raw host paths, traversal, hidden/sensitive names, control characters, and unsafe labels | no finding |
| Source artifact is revalidated | Apply re-reads source bytes and rejects stale artifact hashes before staging | no finding |
| Host staging is create-exclusive | Placement uses a safe generated destination under the configured staging root and `O_EXCL` write semantics | no finding |
| Replay remains denied | Approval execution is one-time and replayed apply attempts fail | no finding |
| Output remains secret-free | API/audit/diagnostic output exposes IDs, labels, hashes, sizes, statuses, and output-policy flags only | no finding |
| Command Center has no runtime authority | Command Center boundary doc keeps promotion execution inside the Gateway API slice | no finding |

## Non-Approvals

This disposition does not approve:

- broad trusted-host promotion;
- arbitrary host paths, overwrite, delete, move, chmod, archive extraction, or broad host writes;
- approved-output publishing;
- Ithildin Command Center runtime authority;
- sandbox orchestration, VM/container lifecycle management, or local model invocation;
- SIEM adapter behavior, compliance automation, production identity, runtime Postgres, hosted
  telemetry, remote MCP, shell, Docker, Kubernetes, browser automation, arbitrary HTTP, or plugin
  SDK behavior;
- public/security-product positioning.

## Next Step

Keep ERG-005 blocked while the accepted runtime source-finding disposition is committed and the
separate enterprise-lane decision is evaluated. Do not treat the fixed findings as promotion,
release, UAT, production-use, or new-power authorization.

Recommended handoff packet:

```sh
make trusted-host-promotion-runtime-source-review-bundle
```
