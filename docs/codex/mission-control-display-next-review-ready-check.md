# Mission Control Display Next Review Ready Check

Status: operator send-readiness check for the `ERG-002` Mission Control display/import review lane.

Current governed tool count: `24`.

Recommended next Mission Control review: `ERG-002` display/import planning.

Recommended packet: `var/review-packets/v3/mission-control-display-external-review/`.

Run:

```sh
make mission-control-display-next-review-ready-check
```

## Purpose

This check gives the operator one small command before sending the Mission Control display/import
packet. It verifies that the external-review bundle, integration readiness packet, response kit,
response dry run, and fail-closed closure gate are all valid and still waiting for real normalized
review response evidence.

It is handoff readiness evidence only. It does not record external review, does not close `ERG-002`,
does not approve Mission Control runtime importer behavior, does not approve Mission Control execution authority,
does not approve Mission Control policy, approval, or audit authority, does not approve local model invocation,
and does not approve sandbox orchestration.

## Ready-To-Send Sequence

Regenerate the packet set:

```sh
make mission-control-display-external-review-bundle
make mission-control-integration-readiness-packet
make mission-control-display-response-kit
make mission-control-display-next-review-ready-check
```

Send the packet directory listed above. The reviewer prompt is:

```text
01_MISSION_CONTROL_DISPLAY_EXTERNAL_REVIEW_PROMPT.md
```

The finding namespace remains:

```text
EXT-MC-DISPLAY-###
```

## Response Boundary

After receiving real source-level review feedback, use the response kit and closure gate:

```sh
make mission-control-display-response-kit
make mission-control-display-response-dry-run
make mission-control-display-disposition-closure-check
```

Only a later committed triage update may move `ERG-002`, and only if normalized source-level
evidence supports it. Mission Control remains display/import planning only unless a later decision
record explicitly approves implementation planning.

## Blocked Boundaries

This ready check does not approve:

- Mission Control runtime importer behavior;
- Mission Control execution authority;
- Mission Control policy authority;
- Mission Control approval authority;
- Mission Control audit authority;
- API callbacks or polling/mutating Ithildin APIs;
- local model invocation;
- VM/container lifecycle management;
- sandbox orchestration;
- trusted-host promotion;
- SIEM adapter behavior;
- production identity, runtime Postgres, hosted telemetry, remote MCP, compliance automation,
  new governed tool powers, or public/security-product positioning.
