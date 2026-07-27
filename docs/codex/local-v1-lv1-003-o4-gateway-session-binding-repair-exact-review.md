# Local v1 LV1-003 O4 Gateway Session-Binding Repair Exact Review

Status: `GO`

Date: 2026-07-26

## Exact Candidate

- Commit: `a9ef905ee2ec3d5ecb63443d5ad567bf6bc09300`
- Tree: `75816ab55d96be34f8d22c7e41ad925a1beaee24`
- Parent commit: `3a9d522f329f348df43168ccd78cacfbdc338a5e`
- `docs/codex/local-v1-lv1-003-o4-producer-contract.md`:
  `sha256:c0cede675f6bc1bcdb74ef331c498c3eae26b2aed46510edd57ffd3aa12a9b45`
- `scripts/local_v1_constrained_mission_journey.py`:
  `sha256:4719643b1513048410c2a5d4e12fefd95816856bd91d0c0a2f0a277abb7c1579`
- `scripts/local_v1_lv1_003_o4_producer.py`:
  `sha256:27b51fca84140762dbf6c323570fdb28ff80863275300573e1489e5f077340e3`
- `tests/test_local_v1_constrained_mission_journey.py`:
  `sha256:b91058467089fe140d5b8099d0325eb776c5abcc9ba05fb177f4f3ccc63f4e43`
- `tests/test_local_v1_lv1_003_o4_producer.py`:
  `sha256:1747b53b6a695ced86585dbac1a06c2f0f9f792e20eda90bd022e2a31bc8c89e`

The candidate changes exactly those five paths. The worktree and exact diff were
clean at review.

## Review Result

- Critical: 0
- High: 0
- Medium: 0
- Low: 0

The exact-candidate disposition is `GO`.

## Reviewed Trust Contract

The bridge-derived mission session remains distinct from the session stored by
Gateway for the AgentRun. The producer privately derives and requires the exact
Gateway wrapper:

```text
node:{server_derived_node_id}:cfg:{configuration_generation}:{configuration_digest}:{mission_session}
```

The persisted AgentRun and both completed-event contexts must match that exact
wrapped value. Public evidence never contains the raw wrapped session, Node
identity, or configuration material. Instead, the run and both event bindings
carry one canonical domain-separated digest with kind
`ithildin_gateway_agent_run_session_v1` and fixed binding source
`gateway_node_configuration_wrapped_mission_session`.

The constrained-journey assembler requires the digest shape, fixed binding
source, and identical digest across the run and both events. Existing run,
request, event, tool, mission, claim, envelope, lifecycle, principal, and
workspace bindings remain intact. The fake API reproduces the live Gateway
wrapper. Negative cases reject an unwrapped session, wrong Node, wrong
configuration generation, wrong configuration digest, event-context mismatch,
malformed or drifted session digest, and binding-source drift.

## Validation

- 338 producer and constrained-journey tests passed centrally.
- The independent reviewer reran 44 focused trust and privacy cases.
- Ruff passed for all four changed code and test paths.
- Strict mypy passed for both changed scripts.
- Agent-workflow, 24-tool invariant, no-new-powers, and diff checks passed.
- Only known non-failing temporary-directory cleanup warnings appeared.

The independent review did not inspect private evidence or run a producer,
Docker, provider, tag, commit, push, or broad release suite.

## Evidence Limits And Authority

This review proves source-contract, fake/live-shape, and bounded public-evidence
consistency only. It does not prove a future live mission, cleanup, release
readiness, production suitability, or human acceptance.

Attempt 020 remains permanently consumed and closed. This `GO` permits
preparation of a separate exact Attempt 021 one-shot authorization gate only.
It does not create a tag, grant live execution, retry an earlier attempt,
permit concurrent or automatic invocation, add a governed tool or power, or
authorize arbitrary host, shell, filesystem, Docker, network, provider,
release, promotion, production, credential-custody, O5, or UAT activity.
