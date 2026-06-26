# Mission Control Display Disposition Packet

Status: external-disposition handoff packet for `ERG-002` and `PRD-MC-DISPLAY-001`.

Current governed tool count: `24`.

Current `ERG-002` status: `planning_only`.

This packet defines the review question for the Mission Control display/importer lane. It asks
whether the existing Ithildin-side proposal, importer plan, schema contract, negative fixtures,
Mission Control-side handoff plan, implementation ticket, and review packet are coherent enough to
continue design-only Mission Control-side planning.

This packet does not approve runtime behavior, API callbacks, MCP transports, Mission Control
execution behavior, Mission Control policy authority, Mission Control approval authority, Mission
Control audit authority, local model invocation, VM/container lifecycle management, sandbox
orchestration, trusted-host promotion, SIEM adapters, production identity, runtime Postgres, hosted
telemetry, shell, Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem
writes, compliance automation, public/security-product positioning, or new governed tool powers.

Validate this packet with:

```sh
make mission-control-display-disposition-packet-check
make mission-control-display-external-response-intake-check
```

Generate the focused disposition handoff with:

```sh
make mission-control-display-disposition-packet
```

## Required Reviewer Question

A reviewer should answer:

Can the Mission Control display/importer lane continue design-only planning from the current
Ithildin-side evidence, or must the lane be revised before any Mission Control-side implementation
ticket is attempted?

Allowed reviewer dispositions:

- `continue_design_only`: the current evidence is coherent for additional Mission Control-side
  design, static fixtures, source-review packet work, and implementation-ticket refinement.
- `revise_before_more_planning`: the handoff packet has missing evidence, ambiguous authority
  language, unsafe display expectations, or incomplete negative fixtures that should be fixed before
  more planning.
- `block_runtime_implementation`: the lane has a blocking product-boundary or trust-boundary issue
  and must not move toward importer implementation until a later decision resolves it.

## Current Evidence Set

The reviewer should inspect:

| Evidence | Source |
| --- | --- |
| Display proposal | `mission-control-display-integration-proposal.md` |
| Importer plan | `mission-control-display-importer-plan.md` |
| Decision intake | `mission-control-display-decision-intake.md` |
| Response intake template | `mission-control-display-external-response-intake.md` |
| Mission Control-side handoff | `mission-control-side-handoff-plan.md` |
| Mission Control implementation ticket | `mission-control-integration-implementation-ticket.md` |
| Handoff schema contract | `mission-control-handoff-schema-contract.md` |
| Negative fixture plan | `mission-control-handoff-negative-fixtures.md` |
| Seed handoff evidence | `hello-world-mission-control-handoff.md` |
| Review packet | `make mission-control-display-review-packet` |
| No-new-powers evidence | `make no-new-powers-guardrail` and `make tool-surface-invariant-gate` |

## Required Boundary Flags

Current output must continue to report:

- Mission Control planning allowed: `true`;
- Mission Control runtime allowed: `false`;
- Mission Control execution authority allowed: `false`;
- Mission Control policy authority allowed: `false`;
- Mission Control approval authority allowed: `false`;
- Mission Control audit authority allowed: `false`;
- local model invocation allowed: `false`;
- sandbox orchestration allowed: `false`;
- trusted-host promotion allowed: `false`;
- SIEM adapter allowed: `false`;
- new power classes allowed: `false`;
- public/security-product positioning allowed: `false`;
- closes `ERG-002`: `false`.

## Required Negative Review Focus

The disposition review should look for:

- schema fields that imply Mission Control can execute, approve, audit, or enforce policy;
- display fields that could leak raw prompts, file contents, diffs, response bodies, token values,
  private keys, raw host paths, environment values, dependency names, package script values, or raw
  sandbox-internal paths;
- stale, mismatched, or missing commit/hash evidence;
- unsafe attachment paths, absolute paths, parent traversal, URLs, or runtime instructions;
- missing warning chips for stale, mismatched, unverified, degraded, or local-preview-only states;
- wording that implies live importer behavior exists today;
- wording that implies Mission Control is the system of record for Ithildin policy, approval,
  execution, or audit evidence.

## Current Allowed State

This packet supports docs, schema contracts, static fixtures, review packets, review prompts, and
operator warning design. It does not close `ERG-002`, and it does not authorize Mission Control
runtime importer behavior. A later post-RC decision record must record the reviewer response before
any Mission Control-side importer implementation begins.
