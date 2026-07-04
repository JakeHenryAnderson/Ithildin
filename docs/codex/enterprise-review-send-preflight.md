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

This preflight gives the operator one final checked answer before sending the
current enterprise review packet. In the current post-disposition route, that
send set is `ERG-004`: the descriptor-only sandbox/VM live POC runtime
source-review packet. It inspects the generated send artifacts, response
landing pad, handoff drill, response-readiness state, operator next-action
state, and handoff consistency gate.

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

It expects:

- current send set: `ERG-004`;
- current response-present count: `0`;
- current closure-ready count: `0`;
- active source-review packet:
  `var/review-packets/v3/sandbox-vm-live-poc-runtime-descriptor-only-source-review`;
- active descriptor-only response inbox:
  `var/review-runs/sandbox-vm-live-poc-runtime-descriptor-only-response-inbox`;
- raw response paths:
  `var/review-runs/sandbox-vm-live-poc-runtime-descriptor-only-response-inbox/RAW_RESPONSE_ERG-004-DESCRIPTOR-ONLY.md`.

## Operator Use

Run this after refreshing the send artifacts and before manually sending the
review packet. The active ERG-004 sequence is:

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle-check
make sandbox-vm-live-poc-runtime-descriptor-only-response-inbox-check
make enterprise-send-now
make enterprise-review-send-preflight
```

The historical ERG-003/ERG-002 dual-send refresh path remains:

```sh
make enterprise-review-send-refresh
```

Use that historical refresh path only when `make enterprise-operator-next-action` reports the
fallback ERG-003/ERG-002 route. It is not the active ERG-004 handoff route.

If the preflight fails because response evidence is present, stop the send flow
and switch to the response-intake flow instead.

After a real ERG-004 reviewer response arrives, paste it into the descriptor-only raw response file
and run:

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run
make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check
```

Do not record a descriptor-only disposition until the dry run and application preflight accept a real
reviewer response.

## Boundary

This preflight is read-only orchestration over existing checks. It does not
send packets, does not record external review, does not normalize responses,
does not write response files beyond the existing ignored generated artifacts,
does not close `ERG-003`, `ERG-002`, or `ERG-004`, and does not approve runtime behavior,
Mission Control runtime behavior, live VM inspection, sandbox orchestration,
trusted-host promotion, SIEM adapter behavior, compliance automation,
public/security-product positioning, or new governed tool powers.
