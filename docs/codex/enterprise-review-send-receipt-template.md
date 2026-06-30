# Enterprise Review Send Receipt Template

Status: generated operator template for recording external-review send receipts after the human
send step.

Run:

```sh
make enterprise-review-send-receipt-template
```

Validate:

```sh
make enterprise-review-send-receipt-template-check
```

Validate the generated or copied receipt JSON before response intake:

```sh
make enterprise-review-send-receipt-validate
```

The generated template is written under:

```text
var/review-packets/v3/enterprise-review-send-receipt-template/
```

## Purpose

This template gives the operator a checked place to record what was actually sent after the
`ERG-003` and `ERG-002` packets leave Ithildin. It ties the generated send manifest, outbox hashes,
reviewer/channel placeholders, and expected raw-response paths together without asserting that an
external review has happened.

The template is intentionally not a response record. It does not record external review by itself,
does not normalize responses, does not write raw response files, does not mutate findings, does not
close `ERG-003` or `ERG-002`, and does not approve runtime behavior. In short, it does not close
`ERG-003` or `ERG-002`.

Required check phrase: does not close `ERG-003` or `ERG-002`.

Expected raw responses are later pasted under the ignored response inbox at
`var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-003.md` and
`var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-002.md`.

## Operator Flow

1. Run `make enterprise-dual-review-outbox`.
2. Run `make enterprise-review-send-manifest`.
3. Run `make enterprise-review-submission-prompt`.
4. Run `make enterprise-review-send-receipt-template`.
5. Run `make enterprise-review-send-receipt-validate`.
6. Run `make enterprise-review-send-receipt-dry-run`.
7. Run `make enterprise-review-send-package`.
8. Send `ERG-003` and `ERG-002` in separate review threads.
9. Copy the ignored generated receipt template after the human send step, then fill in the send
   timestamp, channel, reviewer label, thread URL or message ID, and expected raw-response path.
10. Run `make enterprise-review-send-receipt-validate RECEIPT=path/to/copied-receipt.json`.
11. Confirm the copied receipt reports
   `next_operator_action: wait_for_responses_then_run_enterprise_response_paste_preflight`.
12. Wait for real reviewer responses, then route responses through
   `make enterprise-dual-response-inbox`, `make enterprise-response-waiting-room`, and the
   lane-specific response kit.

## Boundary

The generated receipt template must keep these flags false:

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
