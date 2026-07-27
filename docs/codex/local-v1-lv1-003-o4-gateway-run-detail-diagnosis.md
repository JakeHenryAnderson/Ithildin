# Local v1 LV1-003 O4 Gateway Run-Detail Diagnosis

Status: `SOURCE_DIAGNOSIS_COMPLETE_REPAIR_NOT_YET_REVIEWED_NO_LIVE_AUTHORITY`

Date: 2026-07-26

## Bounded Evidence

Attempt019 is permanently consumed. Its identity-free disposition records:

- the terminal mission-level projection gate passed before the later failure;
- the Node receipt reached `completion_recorded`;
- the Node receipt last closed status is `runner_reported_succeeded`;
- the Node receipt last closed reason is `none`;
- the producer then failed with `gateway_run_detail_invalid`;
- cleanup completed and recovery is not required; and
- execution budget is zero with all 19 authority fields false.

The terminal mission-gate observation is source-control-flow evidence only. No Gateway mission
projection was stored or reproduced, and the observation does not establish overall O4 success.
This diagnosis does not reproduce any private run, project, container, image, Node, mission, claim,
provider, output, or credential identity.

## Source Diagnosis

The producer first validates the Gateway mission projection, its single exactly correlated Agent Run
summary, and the expected two governed tool calls. It then reads the Agent Run detail and validates
the run record plus the two `tool.execution.completed` audit timeline events.

The live Agent Run contract stores the complete authenticated Node and mission provenance in the
Agent Run record's `metadata` object:

- `ingress_kind=node_governed_access`;
- `identity_source=gateway_derived_node`;
- the Gateway-derived Node identity and display name;
- the read-only authorization profile;
- configuration generation and digest;
- `offline_fallback_allowed=false`;
- `runner_enforcement_proven=false`;
- mission, claim, and envelope bindings; and
- `mission_binding_source=gateway_validated_claim_session`.

Each audit timeline event deliberately receives only `AgentRunContext.metadata()` plus its own
execution metadata. The Agent Run context contains run, session, workspace, and principal
correlation. It does not duplicate the mission, claim, or envelope fields from the Agent Run
record.

The producer's fake API fixture does duplicate those three mission fields on every completed event.
The live producer therefore requires an event shape that its own real Gateway does not emit:
`event.metadata.mission_id`, `event.metadata.mission_claim_id`, and
`event.metadata.mission_envelope_digest`. That fixture-to-runtime contract mismatch is the bounded
source cause of `gateway_run_detail_invalid`.

## Smallest Defensible Repair

The producer should validate authority at the surfaces where the Gateway actually stores it:

1. Validate the Agent Run's principal, workspace, session, status, and tool-call count.
2. Validate the Agent Run record's complete authenticated Node and mission provenance against the
   enrolled Node, assigned configuration, admitted mission, delivered claim, and envelope.
3. Validate each completed audit event's run, session, workspace, and principal correlation from
   `AgentRunContext`.
4. Continue validating each event's ID, hash, request ID, type, exact tool name, order, and completed
   status.
5. Update the fake API to reproduce the real run-record and event-metadata contracts.
6. Add negative tests for missing or conflicting run-record provenance and mismatched event
   correlation.

This tightens the evidence check rather than weakening it: mission authority moves from a
nonexistent duplicated event field to the authoritative persisted Agent Run record, while every
event remains exactly correlated to that run.

## Boundary And Authority

The proposed repair:

- changes no Gateway, Node, MCP, runner, or provider behavior;
- adds no tool, endpoint, input, capability, Docker authority, host control, credential access, or
  model-provider authority;
- keeps the governed tool count exactly 24;
- preserves Gateway truth, Node connectivity, runner-reported state, and model-provider state as
  separate observations;
- does not relabel Attempt019 as successful; and
- does not authorize Attempt020, execution, retry, release, promotion, production, or UAT.

Implementation should be limited to the producer and its focused tests. It requires proportional
Sol-high exact review because it changes evidence validation on a trust-boundary path. Sol xhigh and
Ultra are not required. Any later live evidence run requires a new separate one-shot authorization
gate and immediate consumed disposition.
