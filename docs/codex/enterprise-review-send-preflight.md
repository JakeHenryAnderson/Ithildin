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
send set is `ERG-005`: the trusted-host artifact promotion review packet. It
inspects the generated send artifacts, response
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

- current send set: `ERG-005`;
- current response-present count: `0`;
- current closure-ready count: `0`;
- active source-review packet:
  `var/review-packets/v3/trusted-host-promotion-external-review`;
- active trusted-host response kit:
  `var/review-packets/v3/trusted-host-promotion-response-kit`;
- active finding namespace: `EXT-TRUSTED-HOST-###`.

## Operator Use

Run this after refreshing the send artifacts and before manually sending the
review packet. The active ERG-005 sequence is:

```sh
make trusted-host-promotion-external-review-bundle-check
make trusted-host-promotion-response-kit-check
make trusted-host-promotion-response-dry-run
make enterprise-send-now
make enterprise-review-send-preflight
```

The historical ERG-003/ERG-002 dual-send refresh path remains:

```sh
make enterprise-review-send-refresh
```

Use that historical refresh path only when `make enterprise-operator-next-action` reports the
fallback ERG-003/ERG-002 route. It is not the active ERG-005 handoff route.

If the preflight fails because response evidence is present, stop the send flow
and switch to the response-intake flow instead.

After a real ERG-005 reviewer response arrives, run:

```sh
make trusted-host-promotion-response-dry-run
make trusted-host-promotion-disposition-closure-check
make trusted-host-promotion-external-response-intake-check
```

The ERG-004 descriptor-only local-development disposition remains recorded, but it is not a
trusted-host promotion approval. Do not record an ERG-005 disposition until the trusted-host dry run
and closure gate accept a real reviewer response.

## Boundary

This preflight is read-only orchestration over existing checks. It does not
send packets, does not record external review, does not normalize responses,
does not write response files beyond the existing ignored generated artifacts,
does not close `ERG-005`, and does not approve runtime behavior,
Mission Control runtime behavior, live VM inspection, sandbox orchestration,
trusted-host promotion, SIEM adapter behavior, compliance automation,
public/security-product positioning, or new governed tool powers.
