# Enterprise Review Handoff Drill

Status: generated operator drill for enterprise review send/receive readiness.

Run:

```sh
make enterprise-review-handoff-drill
```

Validate:

```sh
make enterprise-review-handoff-drill-check
```

The generated drill is written under:

```text
var/review-packets/v3/enterprise-review-handoff-drill/
```

## Purpose

Active enterprise route: `PIS-001` threat-model and dependency-decision planning under the recorded `ERG-006`/`ERG-007` architecture decision.

This drill gives the operator one checked view of the historical dual-send enterprise review
handoff loop. This drill
remains for ERG-003/ERG-002 provenance, receipt, and response-intake rehearsal. It
ties together:

- the current `ERG-003` and `ERG-002` send-ready outbox;
- the send manifest and artifact hashes;
- the submission prompt;
- the send receipt template;
- the dual-response inbox for the current `ERG-003` and `ERG-002` send set;
- the response status board;
- the fixture-only response-intake drill;
- the lane-specific dry-run and closure-gate commands.

It is intentionally a handoff drill, not a response record. It does not record external review,
does not normalize real responses, does not mutate findings, does not close any enterprise lane,
and does not approve runtime behavior.

## Historical Dual-Send Set

- `ERG-003`: static sandbox/VM preflight disposition.
- `ERG-002`: Mission Control display/importer planning review.

Generate the prerequisite artifacts first with:

```sh
make enterprise-dual-review-outbox
make enterprise-review-send-manifest
make enterprise-review-submission-prompt
make enterprise-review-send-receipt-template
make enterprise-review-send-receipt-copy
make enterprise-review-send-receipt-validate RECEIPT=path/to/copied-receipt.json
make enterprise-dual-response-inbox
make enterprise-response-waiting-room
make enterprise-response-now
make enterprise-response-paste-preflight
make enterprise-response-status-board
make enterprise-response-intake-drill
```

Or generate and check the whole operator drill with:

```sh
make enterprise-review-handoff-drill
make enterprise-review-handoff-drill-check
```

## Operator Flow

1. Generate the current outbox, send manifest, submission prompt, and send receipt template.
2. Send only the `ERG-003` and `ERG-002` attachment sets named in the manifest.
3. After sending, run `make enterprise-review-send-receipt-copy`, fill the copied local receipt, and
   validate it with
   `make enterprise-review-send-receipt-validate RECEIPT=path/to/copied-receipt.json`.
4. Generate the dual-response inbox.
5. Paste raw reviewer responses into the lane-specific ignored raw-response files under
   `var/review-runs/enterprise-dual-response-inbox/`:
   `var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-003.md` and
   `var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-002.md`.
6. Run `make enterprise-response-waiting-room`, then `make enterprise-response-now`, then
   `make enterprise-response-paste-preflight`.
7. Run the lane-specific response dry run.
8. Run the lane-specific closure gate.
9. Apply any favorable response through the committed lane-specific response-application path.

## Boundary

This drill does not approve:

- runtime changes;
- Mission Control runtime behavior;
- live VM/container inspection;
- local model invocation;
- sandbox orchestration;
- trusted-host promotion;
- SIEM adapters;
- compliance automation;
- public/security-product positioning;
- new governed tool powers.

The current governed tool count remains `24`, and the selected capability remains `not selected`.
