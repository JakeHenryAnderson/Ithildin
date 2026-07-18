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

The current remediation candidate fixes `001`, `003`, `004`, and `005`. `002` remains deferred
because it requires an explicit architecture and public evidence-contract decision. `006` is
partially remediated but remains deferred with the governance-drift evidence that depends on `002`.
This status does not close the findings or ERG-005; exact-candidate independent re-review is still
required.

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

Keep ERG-005 runtime source-review closure blocked until the deferred governance-binding decision is
made, the remaining implementation and evidence work is complete, and an independent reviewer
rechecks the exact clean remediation candidate.

Recommended handoff packet:

```sh
make trusted-host-promotion-runtime-source-review-bundle
```
