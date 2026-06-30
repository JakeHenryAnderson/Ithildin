# Enterprise Review Send Receipt Validation

Status: read-only validation for operator send receipts before response intake.

Run:

```sh
make enterprise-review-send-receipt-validate
```

To validate a copied, filled receipt instead of the generated unsent template:

```sh
uv run python scripts/enterprise_review_send_receipt_validate.py --receipt path/to/copied-receipt.json
```

The default command validates the generated receipt template under
`var/review-packets/v3/enterprise-review-send-receipt-template/`. A valid unsent template remains
`ready_for_response_intake: false`; that is expected until the operator fills the send evidence
after actually sending `ERG-003` and `ERG-002`.

## Ready For Response Intake

A copied receipt becomes ready for response intake only when all of these are true:

- the top-level `sent` field is `true`;
- both receipt rows, exactly `ERG-003` and `ERG-002`, have `sent: true`;
- each sent row includes `sent_at`, `channel`, `reviewer_label`, and either `thread_or_message_url`
  or `message_id`;
- raw response paths still point to
  `var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-003.md` and
  `var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-002.md`;
- the tool count is `24`, selected capability is `not selected`, and blocked-boundary flags remain
  false.

## Boundary

This validator does not record external review, normalize responses, write response files, mutate
findings, close lanes, approve runtime behavior, or allow new powers. It only tells the operator
whether a send receipt is structurally ready for the existing response-intake path.

Required boundary phrases: does not normalize responses; does not write response files; does not close lanes.
