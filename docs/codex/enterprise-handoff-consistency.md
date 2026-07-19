# Enterprise Handoff Consistency

Status: checked read-only enterprise handoff consistency gate.

`make enterprise-handoff-consistency-check` validates that the historical
dual-send handoff docs describe the same send/receive path for `ERG-003` and
`ERG-002`. This is a lineage/fallback gate, not the active next-send route.
After the recorded dispositions, the active operator route is the separate
`ERG-006`/`ERG-007` production identity/storage architecture-review path; this gate remains as a
consistency check for older dual-send artifacts.

Historical dual-send set: `ERG-003`, `ERG-002`.

Active send set: `ERG-006`, `ERG-007`.

Active route reminder: run `make enterprise-active-route-clarity` or
`make enterprise-send-now` for the current `ERG-006`/`ERG-007` architecture-review path.

The historical dual-response inbox root is:

- `var/review-runs/enterprise-dual-response-inbox`

The historical raw response paths are:

- `var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-003.md`
- `var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-002.md`

The required pre-send commands are the efficient operator path after code or artifact changes:

- `make release-check`
- `make review-candidate`
- `make enterprise-review-send-refresh`
- `make handoff-dry-run`
- `make enterprise-send-now`

The required historical dual-send flow commands span the post-send receipt step and the response
intake preflight. They are not all pre-send commands:

- `make enterprise-review-send-receipt-template`
- `make enterprise-review-send-receipt-copy`
- `make enterprise-review-send-receipt-validate RECEIPT=path/to/copied-receipt.json`
- `make enterprise-dual-response-inbox`
- `make enterprise-response-waiting-room`
- `make enterprise-response-now`
- `make enterprise-response-paste-preflight`

The required active `ERG-006`/`ERG-007` response commands are:

- `make production-identity-storage-response-kit-check`
- `make production-identity-storage-response-dry-run`
- `make production-identity-storage-external-response-intake-check`
- `make production-identity-storage-disposition-closure-check`
- `make enterprise-response-waiting-room`
- `make enterprise-response-now`

The check covers the operator-facing historical dual-send handoff docs:

- `docs/codex/enterprise-review-send-checklist.md`
- `docs/codex/enterprise-review-send-quickstart.md`
- `docs/codex/enterprise-review-submission-prompt.md`
- `docs/codex/enterprise-review-send-receipt-template.md`
- `docs/codex/enterprise-review-handoff-drill.md`
- `docs/codex/enterprise-north-star-roadmap.md`
- `docs/codex/enterprise-dependency-ladder.md`
- `docs/codex/enterprise-transition-map.md`
- `docs/codex/enterprise-operator-next-action.md` (active `ERG-006`/`ERG-007` route plus historical fallback)

It also rejects stale current-handoff paths under:

- `var/review-packets/v3/enterprise-dual-response-inbox`
- `var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-003.md`
- `var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-002.md`

## Boundary

This gate is documentation and process consistency only. It does not record external review.
It does not normalize responses, does not write response files,
does not close `ERG-003` or `ERG-002`, and does not approve runtime behavior,
Mission Control runtime behavior, live VM inspection, sandbox orchestration,
SIEM adapter behavior, compliance automation, public/security-product
positioning, or new governed tool powers.
