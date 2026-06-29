# Enterprise Review Submission Prompt

Status: generated operator paste prompt for current enterprise external-review packets.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Generate the prompt with:

```sh
make enterprise-review-submission-prompt
```

Validate it with:

```sh
make enterprise-review-submission-prompt-check
```

Before sending, run:

```sh
make enterprise-review-send-checklist
```

See [Enterprise Review Send Checklist](enterprise-review-send-checklist.md).

The generated prompt is written under:

```text
var/review-packets/v3/enterprise-review-submission-prompt/
```

## Purpose

The dual-review outbox and send manifest define the current `ERG-003` and `ERG-002` packet set.
This prompt is the final operator-facing paste layer: it tells the operator to use separate review
threads, attach every file from the lane directory, preserve the required finding namespace, and
follow the lane-specific response kit after reviewer feedback arrives.

It exists to reduce copy/paste mistakes. It does not record external review, does not normalize
responses, does not mutate findings, does not close either lane, and does not approve runtime
behavior.

## Expected Use

1. Run `make enterprise-dual-review-outbox`.
2. Run `make enterprise-review-send-manifest`.
3. Run `make enterprise-review-send-checklist`.
4. Run `make enterprise-review-submission-prompt`.
5. Run `make enterprise-review-send-receipt-template` if you want a local operator template for
   recording the send thread, reviewer label, packet hashes, and response path after the human send
   step.
6. For `ERG-003`, attach every file from the generated `ERG-003/` outbox directory and paste the
   `ERG-003` section of the generated prompt.
7. For `ERG-002`, use a separate review request, attach every file from the generated `ERG-002/`
   outbox directory, and paste the `ERG-002` section of the generated prompt.
8. After a response arrives, run `make enterprise-dual-response-inbox`, open
   `ENTERPRISE_DUAL_RESPONSE_CHEATSHEET.md`, save each raw response in the matching ignored
   placeholder, run `make enterprise-response-paste-preflight`, and then run the lane-specific
   normalization, dry-run, and closure gate before any committed status update.

## Boundary

This prompt does not approve live VM/container inspection, Mission Control runtime behavior, local
model invocation, sandbox orchestration, trusted-host promotion, SIEM adapters, compliance
automation, public/security-product positioning, new governed tool powers, production identity,
runtime Postgres, hosted telemetry, remote MCP, or broader runtime changes.

The generated artifact hashes are handoff-integrity evidence only. They are not notarization,
custody-grade evidence, source-review disposition, or implementation approval.
