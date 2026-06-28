# Enterprise Dual Review Outbox

Status: generated send-ready outbox for the current two enterprise reviews.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Generate the outbox with:

```sh
make enterprise-dual-review-outbox
```

Validate it with:

```sh
make enterprise-dual-review-outbox-check
```

For the human operator send checklist over this outbox, run:

```sh
make enterprise-review-send-checklist
```

See [Enterprise Review Send Checklist](enterprise-review-send-checklist.md).

## Purpose

The dual-review handoff tells an operator which `ERG-003` and `ERG-002` files are ready to send.
The outbox copies those exact generated files into one ignored directory so the operator can attach
the right packet without manually walking two review-packet trees.

Default output:

```text
var/review-packets/v3/enterprise-dual-review-outbox/
```

The generated outbox contains:

- `ENTERPRISE_DUAL_REVIEW_OUTBOX_INDEX.md`;
- `enterprise-dual-review-outbox.json`;
- `enterprise-dual-review-outbox-artifact-hashes.json`;
- `ERG-003/` with the static sandbox/VM preflight review packet files;
- `ERG-002/` with the Mission Control display/import planning review packet files.

## Boundary

This outbox does not record external review, does not normalize reviewer responses, does not mutate
findings, does not close either lane, and does not approve runtime behavior.

It does not approve Mission Control runtime behavior, live VM/container inspection, local model
invocation, sandbox orchestration, trusted-host promotion, SIEM adapters, compliance automation,
public/security-product positioning, new governed tool powers, production identity, runtime
Postgres, hosted telemetry, or remote MCP.

## Operator Flow

1. Run `make enterprise-review-send-readiness`.
2. Run `make enterprise-dual-review-handoff`.
3. Run `make enterprise-dual-review-outbox`.
4. Send the `ERG-003/` directory as one review packet.
5. Send the `ERG-002/` directory as a separate review packet.
6. Keep `ENTERPRISE_DUAL_REVIEW_OUTBOX_INDEX.md` and
   `enterprise-dual-review-outbox-artifact-hashes.json` with the handoff notes.
7. Run `make enterprise-review-send-manifest` to capture the send set, outbox hash manifest,
   lane-specific response paths, and blocked-boundary flags in one generated manifest.
8. Run `make enterprise-review-send-checklist` to validate the current attachment, prompt, and
   response-path instructions.
9. Run `make enterprise-review-submission-prompt` to generate the final paste-ready operator prompt
   for the separate `ERG-003` and `ERG-002` review requests.
10. After responses arrive, run `make enterprise-dual-response-inbox`, paste reviewer text into the
   matching ignored raw-response placeholder, then run `make enterprise-dual-response-readiness` and
   follow the lane-specific response kit. Do not edit lane status by hand.

The artifact hashes are handoff-integrity evidence only. They are not notarization,
custody-grade evidence, source-review disposition, or implementation approval.
