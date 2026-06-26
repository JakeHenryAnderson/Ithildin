# Enterprise Next Review Ready Check

Status: operator send-readiness check for the current enterprise external-review queue.

Current governed tool count: `24`.

Recommended next enterprise review: `ERG-003` static sandbox/VM preflight disposition.

Recommended packet: `var/review-packets/v3/sandbox-vm-static-preflight-external-review/`.

Run:

```sh
make enterprise-next-review-ready-check
```

## Purpose

This check gives the operator one small command before sending the next review packet. It verifies
that the `ERG-003` static preflight external-review bundle is valid, the enterprise next-review
handoff is valid, the reviewed-packet hash helper is available, and the fail-closed closure gate is
still waiting for real normalized response evidence.

It is handoff readiness evidence only. It does not record external review, does not close `ERG-003`,
does not approve live VM/container inspection, does not approve local model invocation,
does not approve sandbox orchestration, and does not approve Mission Control runtime behavior.

## Ready-To-Send Sequence

Regenerate the packet and pointer:

```sh
make sandbox-vm-static-preflight-external-review-bundle
make enterprise-next-review-handoff
make enterprise-next-review-ready-check
```

Copy the reviewed-packet hash for later response normalization:

```sh
make sandbox-vm-static-preflight-reviewed-packet-hash
```

Send the packet directory listed above. The reviewer prompt is:

```text
01_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_PROMPT.md
```

The finding namespace remains:

```text
EXT-SVP-###
```

## Response Boundary

After receiving real source-level review feedback, use the response kit and closure gate:

```sh
make sandbox-vm-static-preflight-response-kit
make sandbox-vm-static-preflight-response-dry-run
make sandbox-vm-static-preflight-disposition-closure-check
make sandbox-vm-static-preflight-response-application-record-check
```

Only a later committed triage update may move `ERG-003`, and only if normalized source-level
evidence supports it. `ERG-004` remains blocked until `ERG-003` is favorably dispositioned.

## Blocked Boundaries

This ready check does not approve:

- live VM/container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- Mission Control runtime behavior;
- local model invocation;
- trusted-host promotion;
- network expansion;
- API/MCP profile loading;
- new governed tool powers;
- production identity, runtime Postgres, hosted telemetry, remote MCP, SIEM delivery, compliance
  automation, or public/security-product positioning.
