# Enterprise Status Export

Status: display-only enterprise status export contract.

`make enterprise-status-export` generates an ignored JSON/Markdown status snapshot under
`var/review-packets/v3/enterprise-status-export/`. The export is intended for operator dashboard
display and Mission Control display/import experiments. It is not a policy source, not an approval
source, not audit custody, not a runtime authority, and not an enterprise lane closure record.

`make enterprise-status-export-check` validates the committed contract, wiring, and generated
artifact shape without approving runtime behavior.

`make mission-control-enterprise-status-import-check` validates the display-only Mission Control
import contract for this export without calling Mission Control or approving runtime importer
behavior.

`make mission-control-enterprise-status-fixtures` writes one valid and twelve negative display/import
fixtures for this export. `make mission-control-enterprise-status-fixtures-check` validates those
fixtures, artifact hashes, and safe rejection expectations.

## Source Inputs

The export composes existing checked reports instead of creating a new source of truth:

- `make enterprise-current-checkpoint`
- `make enterprise-operator-next-action`
- `make enterprise-progress-model`
- `make enterprise-review-send-readiness`
- `make enterprise-response-status-board`

The export includes current commit/dirty state, tool count, selected capability state, recommended
enterprise send set, current next action, safe action commands when a state has any, post-send receipt/response
breadcrumbs under `next_after_send_commands`, display-only handoff artifact pointers,
response/closure counts, progress bands, review-lane status, generated packet paths including the
enterprise review send quickstart, send package, send-session record, and blocked authority flags.
For the current PIS-003 external-input wait, the display export exposes an empty send set, empty
`action_commands`, empty `next_after_send_commands`, and zero handoff-ready packets. It displays the
reviewed authority record and contract only as handoff evidence. Mission Control does not execute
commands or convert the two proposal permissions into operational collection authority.

## Output Artifacts

Generated artifacts are ignored local evidence:

- `ENTERPRISE_STATUS_EXPORT.md`
- `enterprise-status-export.json`
- `enterprise-status-export-artifact-hashes.json`

The hash manifest covers the generated Markdown and JSON payloads and does not hash itself.

## Boundary

- It does not approve Mission Control runtime behavior.
- It does not approve live VM/container inspection.
- It does not approve sandbox orchestration.
- It does not approve trusted-host promotion.
- It does not approve SIEM adapter behavior.
- It does not approve compliance automation.
- It does not approve public/security-product positioning.
- It does not approve new governed tool powers.

Mission Control may later use this as a display/import fixture only after its importer validates the
schema, treats all authority flags as advisory status fields, and refuses to convert them into
runtime permissions.
The expected future importer states and safe rejection labels are mapped in
[mission-control-enterprise-status-acceptance-matrix.md](mission-control-enterprise-status-acceptance-matrix.md).
