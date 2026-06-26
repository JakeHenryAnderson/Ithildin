# Enterprise Next Review Handoff

Status: operator handoff pointer for the current enterprise external-review queue.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Recommended next enterprise review: `ERG-003` static sandbox/VM preflight disposition.

Generate the handoff with:

```sh
make enterprise-next-review-handoff
```

Validate it with:

```sh
make enterprise-next-review-handoff-check
```

The generated handoff is written under:

```text
var/review-packets/v3/enterprise-next-review-handoff/
```

## Purpose

This document is the small operator-facing pointer for the next enterprise review. It exists because
the enterprise queue has many lanes, while the current next action is narrow: send the `ERG-003`
static sandbox/VM preflight external-review bundle and then process any response through the
fail-closed response path.

## Packet To Send

The current packet to send is:

```text
var/review-packets/v3/sandbox-vm-static-preflight-external-review/
```

Regenerate it with:

```sh
make sandbox-vm-static-preflight-external-review-bundle
```

The reviewer prompt is:

```text
01_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_PROMPT.md
```

The finding namespace is:

```text
EXT-SVP-###
```

## Response Path

After review, use:

```sh
make sandbox-vm-static-preflight-response-kit
make sandbox-vm-static-preflight-response-dry-run
make sandbox-vm-static-preflight-disposition-closure-check
```

Then follow:

```text
docs/codex/sandbox-vm-static-preflight-triage-update.md
```

Only a later committed triage update may move `ERG-003`, and only if normalized source-level
review evidence supports it.

## Boundary

This handoff does not close `ERG-003`, does not record external review, does not approve live VM/container inspection, and does not approve local model invocation.

It also does not approve VM/container lifecycle management, sandbox orchestration, Mission Control
runtime behavior, trusted-host promotion, network expansion, API/MCP profile loading, new governed
tool powers, production identity, runtime Postgres, hosted telemetry, remote MCP, SIEM delivery,
compliance automation, or public/security-product positioning.
