# Enterprise Review Send Preflight

Status: checked final operator preflight for the current enterprise review send.

Run:

```sh
make enterprise-review-send-preflight
```

To regenerate the current ignored send artifacts and then run this preflight in
one operator command, use:

```sh
make enterprise-review-send-refresh
```

This preflight now serves two modes. For a historical send route, it gives the operator one final
checked answer before sending a review packet. In the current post-disposition route, external
target identity and signed environment receipts are required and there is no current review send
set. It checks the operator next-action and response state without treating stale historical send
artifacts as active authority. Current action:
`await_external_operator_target_and_signed_receipt_inputs_before_separate_collection_action_authority`.
The current external target identity and signed environment receipts must come from the external
operator. This preflight does not authorize environment evidence collection action.

## Covered Components

The preflight is designed to run after these artifacts have been generated:

- `make enterprise-review-send-readiness`
- `make enterprise-dual-review-outbox`
- `make enterprise-review-send-manifest`
- `make enterprise-review-send-checklist`
- `make enterprise-review-send-quickstart`
- `make enterprise-review-submission-prompt`
- `make enterprise-review-send-receipt-template`
- `make enterprise-review-send-receipt-validate`
- `make enterprise-review-send-package`
- `make enterprise-review-upload-staging`
- `make enterprise-review-send-session-record`
- `make enterprise-dual-response-inbox`
- `make enterprise-dual-response-readiness`
- `make enterprise-response-status-board`
- `make enterprise-review-handoff-drill`
- `make enterprise-handoff-consistency-check`

For speed, the preflight does not recursively rebuild every component. It
checks the current operator state, response state, handoff consistency, required
generated files, and artifact hashes. If generated artifacts are missing or
stale, rerun the component command sequence below.

When the worktree is clean, the preflight also enforces that generated artifact
payloads were produced for the current commit and were not generated from a
dirty tree. When the worktree is dirty during development, that freshness check
is deferred until the next clean run.

In the current PIS-003 external-input wait mode it expects:

- no current review send set;
- current response-present count: `0`;
- current closure-ready count: `0`;
- active continuation decision:
  `docs/codex/production-identity-storage-pis-002-continuation-decision-record.md`;
- closed continuation contract:
  `docs/codex/production-identity-storage-pis-002-continuation-decision.json`;
- active finding namespace: `EXT-PROD-IAM-STORAGE-###`.

## Operator Use

The current route is intentionally commandless. The preflight itself may be rerun as a read-only
status check:

```sh
make enterprise-review-send-preflight
```

The historical ERG-003/ERG-002 dual-send refresh path remains:

```sh
make enterprise-review-send-refresh
```

Use that historical refresh path only when `make enterprise-operator-next-action` reports the
fallback ERG-003/ERG-002 route. It is not the active ERG-006/ERG-007 handoff route.

If the preflight fails because response evidence is present, stop the send flow
and switch to the response-intake flow instead.

After a real ERG-006/ERG-007 reviewer response arrives, run:

```sh
make production-identity-storage-response-dry-run
make production-identity-storage-disposition-closure-check
make production-identity-storage-external-response-intake-check
```

The accepted ERG-005 source-finding disposition remains recorded, but it does not close ERG-005 or
approve trusted-host promotion. Do not record an ERG-006/ERG-007 architecture disposition until the
production identity/storage dry run and closure gate accept a real reviewer response.

## Boundary

This preflight is read-only orchestration over existing checks. It does not authorize environment
evidence collection action, and it does not
send packets, does not record external review, does not normalize responses,
does not write response files beyond the existing ignored generated artifacts,
does not close `ERG-006` or `ERG-007`, and does not approve runtime behavior,
Mission Control runtime behavior, live VM inspection, sandbox orchestration,
trusted-host promotion, SIEM adapter behavior, compliance automation,
public/security-product positioning, or new governed tool powers.
