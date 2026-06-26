# Enterprise Dual Review Handoff

Status: operator handoff pointer for the two currently send-ready enterprise reviews.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Recommended enterprise reviews:

- `ERG-003`: static sandbox/VM preflight disposition.
- `ERG-002`: Mission Control display/import planning review.

Generate the handoff with:

```sh
make enterprise-dual-review-handoff
```

Validate it with:

```sh
make enterprise-dual-review-handoff-check
```

Before sending either packet, run:

```sh
make enterprise-review-send-readiness
```

## Purpose

This document is the operator-facing pointer for the two enterprise review packets that are
mechanically ready to send now. It exists because `ERG-003` remains the primary next enterprise
review, while `ERG-002` can be sent in parallel as a conservative Mission Control display/import
planning review.

This handoff does not close either lane, does not record external review, does not approve Mission Control runtime behavior, does not approve live VM/container inspection, and does not approve local model invocation.

## Packets To Send

Send `ERG-003` from:

```text
var/review-packets/v3/sandbox-vm-static-preflight-external-review/
```

Reviewer prompt:

```text
01_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_PROMPT.md
```

Finding namespace:

```text
EXT-SVP-###
```

Send `ERG-002` from:

```text
var/review-packets/v3/mission-control-display-external-review/
```

Reviewer prompt:

```text
01_MISSION_CONTROL_DISPLAY_EXTERNAL_REVIEW_PROMPT.md
```

Finding namespace:

```text
EXT-MC-DISPLAY-###
```

## Attachment Integrity

Before sending each packet, verify its artifact hash manifest:

```text
var/review-packets/v3/sandbox-vm-static-preflight-external-review/sandbox-vm-static-preflight-external-review-artifact-hashes.json
var/review-packets/v3/mission-control-display-external-review/mission-control-display-external-review-artifact-hashes.json
```

The generated dual handoff recomputes byte counts and SHA-256 digests for both packet directories.
This is handoff-integrity evidence only; it is not notarization, custody-grade proof, or a
source-review disposition.

## Response Path

For `ERG-003`, use:

```sh
make sandbox-vm-static-preflight-response-kit
make sandbox-vm-static-preflight-response-dry-run
make sandbox-vm-static-preflight-disposition-closure-check
```

Then follow:

```text
docs/codex/sandbox-vm-static-preflight-external-response-intake.md
docs/codex/sandbox-vm-static-preflight-triage-update.md
docs/codex/sandbox-vm-static-preflight-response-application-record.md
```

For `ERG-002`, use:

```sh
make mission-control-display-response-kit
make mission-control-display-response-dry-run
make mission-control-display-disposition-closure-check
```

Then follow:

```text
docs/codex/mission-control-display-external-response-intake.md
docs/codex/mission-control-display-disposition-closure-gate.md
```

Only later committed response-intake and triage records may update either lane.

## Boundary

This handoff does not approve VM/container lifecycle management, sandbox orchestration, Mission
Control runtime importer behavior, Mission Control execution authority, Ithildin polling callbacks,
trusted-host promotion, network expansion, API/MCP profile loading, new governed tool powers,
production identity, runtime Postgres, hosted telemetry, remote MCP, SIEM delivery, compliance
automation, or public/security-product positioning.
