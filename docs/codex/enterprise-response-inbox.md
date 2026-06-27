# Enterprise Response Inbox

Status: generated response inbox for all enterprise external-review lanes.

Use:

```sh
make enterprise-response-inbox
```

Check:

```sh
make enterprise-response-inbox-check
```

Before using lane-specific normalization commands, `make enterprise-response-normalization-coverage`
verifies that every enterprise response lane has a supported normalizer area and finding namespace.

The generated inbox lives under `var/review-runs/enterprise-response-inbox/` and creates
raw-response placeholders for all enterprise review lanes, exact
`scripts/external_response_normalize.py` commands, reviewed-packet hashes, lane dry-run or closure
commands, and artifact hashes.

This inbox does not normalize responses, does not write normalized response files, does not record external review, does not mutate findings, does not close any enterprise lane, and does not approve Mission Control runtime behavior, live VM/container inspection, local model invocation, sandbox orchestration, trusted-host promotion, SIEM adapters, compliance automation, public/security-product positioning, or new governed tool powers.

## Generated Files

- `ENTERPRISE_RESPONSE_INBOX.md`
- `enterprise-response-inbox.json`
- one `RAW_RESPONSE_*.md` placeholder per enterprise lane
- `enterprise-response-inbox-artifact-hashes.json`

The raw-response placeholders are intentionally ignored runtime/review-run artifacts. Paste real
reviewer text there only for local normalization and triage. Do not commit raw reviewer prose unless
a later explicit review-intake task asks for a curated committed record.

## Lane Flow

For any enterprise lane:

1. Paste the reviewer response into the matching `RAW_RESPONSE_*.md` file.
2. Run the exact normalization command in `ENTERPRISE_RESPONSE_INBOX.md`.
3. Run the lane-specific dry-run command when one exists.
4. Run the lane-specific closure gate.
5. Commit a later triage/update record only if the closure gate proves the response is favorable.

The generated inbox covers:

- `ERG-003`: `sandbox-vm-static-preflight`
- `ERG-002`: `mission-control-display`
- `ERG-005`: `trusted-host-promotion`
- `ERG-006/ERG-007`: `production-identity-storage`
- `ERG-008`: `siem-export-adapter`
- `ERG-009`: `compliance-mapping`
- `ERG-004`: `sandbox-vm-live-poc`
- `ERG-010`: `public-security-product-positioning`

The narrower [Enterprise Dual Response Inbox](enterprise-dual-response-inbox.md) remains the
recommended landing pad for the current `ERG-003` and `ERG-002` parallel handoff. This all-lane inbox
is the general fallback when any other enterprise reviewer response arrives first.

To exercise the response-intake path with temporary fixtures before a real response arrives, run:

```sh
make enterprise-response-intake-drill
```

See [Enterprise Response Intake Drill](enterprise-response-intake-drill.md).
