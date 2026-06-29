# Enterprise Review Send Checklist

Status: operator checklist for sending the current enterprise review packets.

Current governed tool count: `24`.

Run:

```sh
make enterprise-review-send-checklist
```

This checklist sits above the generated outbox and send manifest. It helps an operator send the
current `ERG-003` and `ERG-002` packets consistently, then route any reviewer response to the
fail-closed response inbox. It does not record external review, does not normalize responses, does
not write response files, and does not close `ERG-003` or `ERG-002`. It also does not approve
runtime behavior or approve new governed tool powers.

## Current Send Set

Send these as two separate review requests:

- `ERG-003`: `var/review-packets/v3/enterprise-dual-review-outbox/ERG-003/`
- `ERG-002`: `var/review-packets/v3/enterprise-dual-review-outbox/ERG-002/`

Attach the lane-local artifact hash manifest for each request:

- `ERG-003/sandbox-vm-static-preflight-external-review-artifact-hashes.json`
- `ERG-002/mission-control-display-external-review-artifact-hashes.json`

Attach the lane-local generated attachment manifest for each request:

- `ERG-003/ATTACHMENT_MANIFEST.md`
- `ERG-002/ATTACHMENT_MANIFEST.md`

Use the generated send manifest for the overall handoff:

- `var/review-packets/v3/enterprise-review-send-manifest/ENTERPRISE_REVIEW_SEND_MANIFEST.md`
- `var/review-packets/v3/enterprise-review-send-manifest/enterprise-review-send-manifest.json`
- `var/review-packets/v3/enterprise-review-send-manifest/enterprise-review-send-manifest-artifact-hashes.json`

Use the generated send quickstart as the one-page operator index:

- `var/review-packets/v3/enterprise-review-send-quickstart/ENTERPRISE_REVIEW_SEND_QUICKSTART.md`
- `var/review-packets/v3/enterprise-review-send-quickstart/enterprise-review-send-quickstart.json`
- `var/review-packets/v3/enterprise-review-send-quickstart/enterprise-review-send-quickstart-artifact-hashes.json`

## Prompt Files

Paste the lane prompt for each review:

- `ERG-003/01_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_PROMPT.md`
- `ERG-002/01_MISSION_CONTROL_DISPLAY_EXTERNAL_REVIEW_PROMPT.md`

Do not merge the two prompts into one reviewer request unless the reviewer is explicitly asked to
review both lanes independently.

## Response Inbox

When responses come back, store raw reviewer text in the ignored response inbox:

- `ERG-003`: `var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-003.md`
- `ERG-002`: `var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-002.md`

Then run:

```sh
make enterprise-response-waiting-room
make enterprise-response-paste-preflight
make enterprise-dual-response-readiness
make enterprise-response-intake-drill
```

For lane-specific closure checks:

```sh
make sandbox-vm-static-preflight-disposition-closure-check
make mission-control-display-disposition-closure-check
```

## Send-Time Verification

Before sending, run:

```sh
make enterprise-review-send-readiness
make enterprise-dual-review-outbox
make enterprise-review-send-manifest
make enterprise-review-send-quickstart
make enterprise-review-submission-prompt
make enterprise-review-send-receipt-template
make enterprise-dual-response-inbox
make enterprise-review-send-checklist
make packet-redaction-scan
```

Expected state:

- `tool_count: 24`
- `recommended_now: ERG-003, ERG-002`
- `response_present_count: 0`
- `closure_ready_count: 0`
- `runtime_changes_allowed: false`
- `mission_control_runtime_allowed: false`
- `live_vm_inspection_allowed: false`
- `sandbox_orchestration_allowed: false`
- `trusted_host_promotion_allowed: false`
- `siem_adapter_allowed: false`
- `compliance_automation_allowed: false`
- `public_security_product_positioning_allowed: false`
- `new_power_classes_allowed: false`

## What This Does Not Do

This checklist does not:

- record external review;
- normalize reviewer responses;
- write response files;
- mutate finding docs;
- close `ERG-003` or `ERG-002`;
- approve Mission Control runtime importer behavior;
- approve live VM/container inspection;
- approve local model invocation;
- approve sandbox orchestration;
- approve trusted-host promotion;
- approve SIEM adapter runtime behavior;
- approve compliance automation;
- approve public/security-product positioning;
- approve new governed tool powers.

The only allowed next action after sending is waiting for raw reviewer responses and processing them
through the existing response intake, dry-run, and closure checks.
