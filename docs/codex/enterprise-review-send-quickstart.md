# Enterprise Review Send Quickstart

Status: generated operator quickstart for the current enterprise send set.

Current governed tool count: `24`.

Run:

```sh
make enterprise-review-send-quickstart
```

Validate:

```sh
make enterprise-review-send-quickstart-check
```

The generated quickstart is written under:

```text
var/review-packets/v3/enterprise-review-send-quickstart/
```

## Purpose

The send checklist, send manifest, submission prompt, receipt template, and dual-review outbox are
separate artifacts because each one has a different validation role. This quickstart is the
operator-facing one-page index over those artifacts. It names the exact `ERG-003` and `ERG-002`
directories to attach, the prompt file to paste, the hash manifest to keep with each request, and
the raw-response placeholder to use when responses arrive.

It does not record external review, does not normalize responses, does not write response files,
does not mutate findings, and does not close `ERG-003` or `ERG-002`.

## Expected Use

1. Run `make release-check`.
2. Run `make review-candidate`.
3. Run `make enterprise-review-send-refresh`.
4. Open the generated quickstart in
   `var/review-packets/v3/enterprise-review-send-quickstart/`.
5. Send `ERG-003` and `ERG-002` as separate review requests using the lane-local prompt and
   attachments named by the generated quickstart.
6. Preserve the generated send receipt template as local operator evidence after the human send
   step.
7. Wait for real reviewer responses before running response intake.

## Response Intake

When responses arrive, use the raw-response placeholders named by the generated quickstart, then
run:

```sh
make enterprise-review-send-receipt-template
make enterprise-dual-response-inbox
make enterprise-response-paste-preflight
make enterprise-response-intake-refresh
```

## Boundary

This quickstart does not approve:

- live VM/container inspection;
- Mission Control runtime behavior;
- local model invocation;
- sandbox orchestration;
- trusted-host promotion;
- SIEM adapter runtime behavior;
- production identity or runtime Postgres;
- compliance automation;
- public/security-product positioning;
- new governed tool powers.

