# Enterprise Response Paste Preflight

Status: deterministic preflight for pasted `ERG-003` and `ERG-002` reviewer responses.

Current governed tool count: `24`.

Run the deterministic docs/wiring check:

```sh
make enterprise-response-paste-preflight
```

Before running a lane-specific paste preflight, `make enterprise-response-waiting-room` can confirm
whether the ignored raw-response files are still placeholders or appear populated.
Use `make enterprise-response-now` when you want the compact lane-specific command sequence before
running any normalizer.

This preflight does not normalize responses, does not write response files, does not mutate
findings, does not record external review, does not close either lane, and does not approve runtime behavior.
It is a small guard between "paste raw reviewer text into the ignored inbox" and "run the existing
lane normalizer".

## ERG-003 Pasted Response

After pasting a real reviewer response into the generated inbox path, run:

```sh
uv run python scripts/enterprise_response_paste_preflight.py \
  --lane ERG-003 \
  --raw-response var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-003.md
```

Expected finding namespace: `EXT-SVP-###`.

The response must be UTF-8, size-bounded, not the generated placeholder, and must contain either the
expected finding namespace prefix or an explicit no-findings statement. Passing this preflight only
means the response is ready for the existing `ERG-003` normalizer and dry-run sequence:

```sh
uv run python scripts/external_response_normalize.py \
  --area sandbox-vm-static-preflight \
  --raw-response var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-003.md
make sandbox-vm-static-preflight-response-dry-run
make sandbox-vm-static-preflight-disposition-closure-check
```

## ERG-002 Pasted Response

After pasting a real reviewer response into the generated inbox path, run:

```sh
uv run python scripts/enterprise_response_paste_preflight.py \
  --lane ERG-002 \
  --raw-response var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-002.md
```

Expected finding namespace: `EXT-MC-DISPLAY-###`.

The response must be UTF-8, size-bounded, not the generated placeholder, and must contain either the
expected finding namespace prefix or an explicit no-findings statement. Passing this preflight only
means the response is ready for the existing `ERG-002` normalizer and dry-run sequence:

```sh
uv run python scripts/external_response_normalize.py \
  --area mission-control-display \
  --raw-response var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-002.md
make mission-control-display-response-dry-run
make mission-control-display-disposition-closure-check
```

The all-lane inbox paths under `var/review-runs/enterprise-response-inbox/` remain accepted for
fallback/manual flows, but the current `ERG-003`/`ERG-002` handoff should use the compact
dual-response inbox and generated cheat sheet.

## What This Proves

- The raw response was pasted to the expected ignored response-inbox path.
- The raw response is valid UTF-8 and below the configured size limit.
- The raw response does not still look like the generated placeholder.
- The raw response references the expected finding namespace or clearly says there are no findings.

## What This Does Not Prove

- It does not prove the reviewer performed source review.
- It does not prove the response is favorable.
- It does not prove the lane can close.
- It does not approve live VM/container inspection, Mission Control runtime importer behavior,
  sandbox orchestration, trusted-host promotion, SIEM adapter runtime behavior, compliance
  automation, public/security-product positioning, or new governed tool powers.

## Stop Conditions

Stop before normalization if:

- the pasted response is still the generated placeholder;
- the pasted response is not UTF-8 or exceeds the size limit;
- the response lacks both the expected finding namespace and an explicit no-findings statement;
- the response asks to skip the normalizer, dry-run, closure gate, or later committed triage update;
- the response directly approves runtime behavior or product positioning outside the lane boundary.
