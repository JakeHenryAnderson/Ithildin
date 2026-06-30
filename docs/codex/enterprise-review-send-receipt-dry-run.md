# Enterprise Review Send Receipt Dry Run

Status: fixture-only rehearsal for copied enterprise send receipts.

Run:

```sh
make enterprise-review-send-receipt-dry-run
```

## Purpose

This dry run proves the operator receipt transition without recording external review. It does not record external review.
It builds the current send receipt template, copies it into temporary fixture files, fills one
copied receipt as if the human send step has happened, and intentionally malforms another copied
receipt.

The expected result is:

```text
filled_receipt_ready: true
malformed_receipt_rejected: true
filled_next_operator_action: wait_for_responses_then_run_enterprise_response_paste_preflight
malformed_next_operator_action: fix_receipt_validation_failures
```

This is a rehearsal only. The temporary copied receipts are discarded. The dry run does not record
external review, does not normalize responses, does not write response files, does not mutate
findings, does not close `ERG-003` or `ERG-002`, and does not approve runtime behavior.

## Operator Flow

Use this after refreshing the send package and before the human send step:

```sh
make enterprise-review-send-refresh
make enterprise-review-send-receipt-dry-run
```

After the real send step, copy the ignored receipt template, fill the send timestamp, channel,
reviewer label, and thread URL or message ID, then validate that copied receipt:

```sh
make enterprise-review-send-receipt-validate RECEIPT=path/to/copied-receipt.json
```

Only after real reviewer responses arrive should the operator paste raw responses into the ignored
response inbox and run the response paste preflight.

## Boundary

The dry run keeps these flags false:

- `records_external_review`
- `normalizes_responses`
- `writes_response_files`
- `closes_erg_003`
- `closes_erg_002`
- `runtime_changes_allowed`
- `mission_control_runtime_allowed`
- `live_vm_inspection_allowed`
- `local_model_invocation_allowed`
- `sandbox_orchestration_allowed`
- `trusted_host_promotion_allowed`
- `siem_adapter_allowed`
- `compliance_automation_allowed`
- `public_security_product_positioning_allowed`
- `new_power_classes_allowed`

The current governed tool count remains `24`, and the selected capability remains `not selected`.
