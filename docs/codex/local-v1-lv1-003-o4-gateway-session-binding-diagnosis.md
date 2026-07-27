# Local v1 LV1-003 O4 Gateway Session-Binding Diagnosis

Status: `SOURCE_DIAGNOSIS_COMPLETE_NO_ATTEMPT_021_OR_REPAIR_AUTHORITY`

Date: 2026-07-26

## Bound Failure

Attempt `LV1-003-O4-ATTEMPT-020` is permanently consumed on exact reviewed
candidate `506cc00267bcedbe00f0384b64a3bf11111bd752`, tree
`6bfb7077a9af05f22095740114b39607b9d715c8`. Its immediate closure is
`af9f1ed6e5d4722c41ca8143cf03f2490e9aca5a`, tree
`70955b57ce70bc730b48956582da7eb1b85c41a8`.

The attempt failed closed with `gateway_run_detail_invalid` after the terminal
mission projection reached `runner_reported_succeeded`. The identity-free Node
receipt projection reached `completion_recorded` and
`runner_reported_succeeded`. Cleanup failures were empty. The attempt budget is
zero, all 19 live-authority fields are false, and release, promotion,
production, and UAT remain false.

No private run, project, Node, mission, claim, container, image, provider, or
session identity is reproduced by this diagnosis.

## Source-Derived Cause

The fixed runner bridge derives a mission-scoped session in
`apps/node/src/ithildin_node/fixed_runner_bridge.py`:

```text
mission:{mission_id}:{claim_id}:{envelope_digest_prefix}
```

The Node client sends that value as the governed-call payload session. Gateway
then deliberately derives the stored AgentRun session in
`apps/api/src/ithildin_api/node_governed_access.py` by wrapping the supplied
session with authenticated Node and configuration context:

```text
node:{server_derived_node_id}:cfg:{configuration_generation}:{configuration_digest}:{supplied_session}
```

That wrapper is a trust-boundary property. It prevents a caller-supplied
session label from erasing the server-derived Node and configuration binding.

The Attempt 020 producer still expects the unwrapped mission session in both
the persisted AgentRun record and its correlated timeline-event metadata.
`tests/test_local_v1_lv1_003_o4_producer.py` also models the persisted record
and events with that unwrapped value. The live Gateway record therefore fails
the producer's exact session comparison before the completed-event binding
loop. This deterministically explains the observed
`gateway_run_detail_invalid` without reading or publishing a raw private
identity.

The constrained-journey schema has the same semantic conflation:
`mission_session_id`, `gateway_agent_runs[].session_id`, and
`gateway_operation_bindings[].session_id` are all required to equal the
bridge-derived mission session even though the latter two represent
Gateway-stored AgentRun context.

## Smallest Defensible Repair

Preserve both truth sources rather than weakening Gateway session derivation:

1. Keep the bridge-derived `mission_session_id` as the bounded mission-session
   projection.
2. Derive the exact expected Gateway AgentRun session privately from the
   authenticated Node identity, configuration generation, configuration
   digest, and mission session.
3. Require the persisted AgentRun record and every correlated completed event
   to match that exact server-derived value.
4. Never publish the raw Gateway AgentRun session because it embeds the private
   Node identity and configuration digest.
5. Replace public `session_id` fields on Gateway AgentRun and event bindings
   with one domain-separated `agent_run_session_digest` plus a fixed
   `session_binding_source` value.
6. Require exact digest equality across the run and both operation bindings,
   while continuing to bind run, request, event, tool, mission, claim,
   envelope, principal, workspace, and lifecycle evidence.
7. Update the fake API and negative matrices to reproduce the real wrapped
   AgentRunContext and to reject wrong wrapper components, raw-session
   publication, digest drift, or binding-source drift.

This repair must not change Node enrollment, Gateway identity derivation,
configuration enforcement, policy, the governed tool surface, runner powers,
or Docker/provider authority.

## Authority And Evidence Limits

This source diagnosis authorizes only preparation and review of the bounded
session-truth repair. It does not authorize Attempt 021, a tag, a live
producer, Docker or provider activity, retry, recovery, cleanup, a new governed
tool or power, release, promotion, production, credential custody, O5, or UAT.

Tests of the repair can prove schema and source-contract consistency only.
They cannot prove a future live mission, cleanup, release readiness, or human
acceptance.
