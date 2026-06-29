# Enterprise Handoff Consistency

Status: checked read-only enterprise handoff consistency gate.

`make enterprise-handoff-consistency-check` validates that the active enterprise
review handoff docs describe the same current send/receive path for `ERG-003`
and `ERG-002`.

The current response inbox root is:

- `var/review-runs/enterprise-dual-response-inbox`

The current raw response paths are:

- `var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-003.md`
- `var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-002.md`

The required current-flow commands are:

- `make enterprise-review-send-receipt-template`
- `make enterprise-dual-response-inbox`
- `make enterprise-response-paste-preflight`

The check covers the operator-facing current handoff docs:

- `docs/codex/enterprise-review-send-checklist.md`
- `docs/codex/enterprise-review-submission-prompt.md`
- `docs/codex/enterprise-review-send-receipt-template.md`
- `docs/codex/enterprise-review-handoff-drill.md`
- `docs/codex/enterprise-current-checkpoint.md`
- `docs/codex/enterprise-north-star-roadmap.md`
- `docs/codex/enterprise-dependency-ladder.md`
- `docs/codex/enterprise-transition-map.md`
- `docs/codex/enterprise-operator-next-action.md`

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
