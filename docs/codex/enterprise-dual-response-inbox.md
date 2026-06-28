# Enterprise Dual Response Inbox

Status: generated response inbox for the current dual enterprise review handoff.

Use:

```sh
make enterprise-dual-response-inbox
```

Check:

```sh
make enterprise-dual-response-inbox-check
```

Before using lane-specific normalization commands, `make enterprise-response-normalization-coverage`
verifies that every enterprise response lane has a supported normalizer area and finding namespace.
For a general response landing pad covering all enterprise lanes, use `make enterprise-response-inbox`.
For the compact `ERG-003` and `ERG-002` receive-and-apply sequence after a real response arrives,
use `make enterprise-response-intake-quickstart`.

The generated inbox lives under
`var/review-runs/enterprise-dual-response-inbox/` and creates raw-response placeholders for
`ERG-003` and `ERG-002`, exact `scripts/external_response_normalize.py` commands, reviewed-packet
hashes, lane dry-run commands, lane closure-gate commands, a compact operator cheat sheet, and
artifact hashes.

This inbox does not normalize responses, does not record external review, does not mutate findings,
does not close either lane, and does not approve Mission Control runtime behavior, live VM/container
inspection, local model invocation, sandbox orchestration, trusted-host promotion, SIEM adapters,
compliance automation, public/security-product positioning, or new governed tool powers.

## Generated Files

- `ENTERPRISE_DUAL_RESPONSE_INBOX.md`
- `ENTERPRISE_DUAL_RESPONSE_CHEATSHEET.md`
- `enterprise-dual-response-inbox.json`
- `RAW_RESPONSE_ERG-003.md`
- `RAW_RESPONSE_ERG-002.md`
- `enterprise-dual-response-inbox-artifact-hashes.json`

The raw-response placeholders are intentionally ignored runtime/review-run artifacts. Paste real
reviewer text there only for local normalization and triage. Do not commit raw reviewer prose unless
a later explicit review-intake task asks for a curated committed record.

## Lane Flow

For `ERG-003`, paste the reviewer response into `RAW_RESPONSE_ERG-003.md`, normalize it with area
`sandbox-vm-static-preflight`, then run:

```sh
make sandbox-vm-static-preflight-response-dry-run
make sandbox-vm-static-preflight-disposition-closure-check
```

For `ERG-002`, paste the reviewer response into `RAW_RESPONSE_ERG-002.md`, normalize it with area
`mission-control-display`, then run:

```sh
make mission-control-display-response-dry-run
make mission-control-display-disposition-closure-check
```

Only a later committed triage/update record may move `ERG-003` or `ERG-002` after the lane-specific
checks prove the normalized response is favorable. This inbox is just the local landing pad that
keeps the first response-handling step repeatable and secret-free.

If a response arrives for a lane other than `ERG-003` or `ERG-002`, use
[Enterprise Response Inbox](enterprise-response-inbox.md) instead of this dual-lane inbox.
