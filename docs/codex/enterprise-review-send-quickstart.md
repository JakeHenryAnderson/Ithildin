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
directories, the manifest-listed files to attach, the prompt file to paste, the lane-local
`ATTACHMENT_MANIFEST.md`, the hash manifest to keep with each request, and the raw-response
placeholder to use when responses arrive. The generated quickstart also shows whether a lane fits a
10-attachment review surface and lists explicit batch file contents when a lane should be split.

It does not record external review, does not normalize responses, does not write response files,
does not mutate findings, and does not close `ERG-003` or `ERG-002`.

## Expected Use

1. Run `make release-check`.
2. Run `make review-candidate`.
3. Run `make enterprise-review-send-refresh`.
4. Run `make enterprise-send-quick-check` to confirm the copied-receipt dry run, current package,
   upload staging, and response waiting room still match the refreshed candidate.
   This quick path also runs `make enterprise-review-send-receipt-dry-run` so the copied-receipt
   transition remains rehearsed before the human send step.
5. Open the generated quickstart in
   `var/review-packets/v3/enterprise-review-send-quickstart/`.
6. Confirm the final preflight reports `valid: true`, `current_dirty: false`,
   `artifact_commits_match_current: true`, and `artifact_payloads_clean: true`.
7. Optionally open the generated package index in
   `var/review-packets/v3/enterprise-review-send-package/`.
8. Optionally open the generated upload staging batches in
   `var/review-packets/v3/enterprise-review-upload-staging/` or regenerate them with
   `make enterprise-review-upload-staging`.
9. Send `ERG-003` and `ERG-002` as separate review requests using the lane-local prompt and
   attachments named by the generated quickstart. If a lane exceeds a 10-attachment review surface,
   use the generated batch file lists instead of dropping files silently.
10. Preserve the generated send receipt template as local operator evidence after the human send
   step.
11. Wait for real reviewer responses before running response intake.

## Response Intake

When responses arrive, use the ignored dual-response inbox:

```text
var/review-runs/enterprise-dual-response-inbox
```

Paste the responses into the lane-local raw-response placeholders:

```text
var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-003.md
var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-002.md
```

Then run:

```sh
make enterprise-review-send-receipt-template
make enterprise-review-send-receipt-copy
make enterprise-review-send-receipt-validate RECEIPT=path/to/copied-receipt.json
make enterprise-dual-response-inbox
make enterprise-response-waiting-room
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
