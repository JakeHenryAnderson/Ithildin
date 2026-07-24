# Local v1 LV1-003 Exact Implementation Review

Status: `GO`

- Milestone: `LV1-003`
- Release outcome: `O4`
- Reviewed candidate: `da5fd021bddb48ad663aa0a409da036bc854b516`
- Reviewed parent: `ef226b28ba4806bfa3fb5ccfb0121afc5e9ae53b`
- Reviewed tree: `f489dee60235d04eb8bc64cc6bb55e8534db1f8e`
- Decision SHA-256:
  `sha256:2a5792c80b672e9e44b24e9ef1e7201990386c90c89e496f17ac2073e04efc72`
- Review date: `2026-07-24`
- Reviewer: independent GPT-5.6 Sol xhigh
- Critical findings: `0`
- High findings: `0`
- Medium findings: `0`
- Low findings: `0`

## Disposition

The exact 32-path candidate received `GO` for code use only. It may serve as the reviewed
`MCC-007` runtime-adapter and fixed runner-bridge implementation candidate. This disposition does
not authorize Docker lifecycle, live Hermes or provider access, `O4` evidence execution, prompt or
output custody, release, promotion, production use, UAT, arbitrary host control, generic process
control, shell execution, a Docker socket, a new governed power, or a governed tool-count change.

`LV1-003` remains `in_progress`, `O4` remains `not_started`, release outcomes remain `1/8`, and
critical-path milestones remain `3/8`. A separately reviewed live-evidence authorization is required
before any candidate-bound `O4` execution.

## Review Lineage

The review did not begin at zero findings. The complete retained lineage is:

| Stage | Candidate posture | Critical | High | Medium | Low | Result |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Initial audit | Dirty worktree candidate | 0 | 3 | 1 | 1 | `NO-GO` |
| First exact review | First bounded exact candidate | 0 | 2 | 1 | 1 | `NO-GO` |
| Exact rereview | Remediated exact candidate | 0 | 0 | 1 | 0 | `NO-GO` |
| Final exact review | Candidate `da5fd021bddb48ad663aa0a409da036bc854b516` | 0 | 0 | 0 | 0 | `GO` |

The final review confirmed that every earlier High, Medium, and Low finding was closed. The earlier
reviews remain findings lineage; they are not themselves a favorable disposition for the final
candidate.

## Exact Reviewed Inventory

The review compared candidate `da5fd021bddb48ad663aa0a409da036bc854b516` directly with parent
`ef226b28ba4806bfa3fb5ccfb0121afc5e9ae53b`. The changed-path inventory was exactly:

1. `Makefile`
2. `README.md`
3. `apps/mcp-server/src/ithildin_mcp_server/node_bridge.py`
4. `apps/node/src/ithildin_node/client.py`
5. `apps/node/src/ithildin_node/fixed_runner_bridge.py`
6. `apps/node/src/ithildin_node/service.py`
7. `deploy/hermes-node-bridge/Dockerfile`
8. `deploy/hermes-node-bridge/README.md`
9. `deploy/hermes-node-bridge/compose.yaml`
10. `deploy/hermes-node-bridge/config.yaml`
11. `deploy/hermes-node-bridge/fixed-instruction.md`
12. `deploy/hermes-node-bridge/profile.json`
13. `docs/codex/local-v1-completion-contract.md`
14. `docs/codex/local-v1-golden-path.md`
15. `docs/codex/mission-command-runner-bridge-authorization-record.md`
16. `docs/codex/mission-command-runner-bridge-capability-decision.md`
17. `scripts/local_v1_constrained_mission_journey.py`
18. `scripts/local_v1_constrained_mission_journey_check.py`
19. `scripts/local_v1_contract_check.py`
20. `scripts/local_v1_golden_path_check.py`
21. `scripts/mission_command_runner_bridge_authorization_check.py`
22. `scripts/mission_command_runner_bridge_decision_check.py`
23. `tests/test_api_service.py`
24. `tests/test_local_v1_constrained_mission_journey.py`
25. `tests/test_local_v1_contract.py`
26. `tests/test_local_v1_golden_path.py`
27. `tests/test_mission_command_runner_bridge_authorization_check.py`
28. `tests/test_mission_command_runner_bridge_decision_check.py`
29. `tests/test_node_client.py`
30. `tests/test_node_fixed_runner_bridge.py`
31. `tests/test_node_mcp_bridge.py`
32. `tests/test_node_service.py`

The post-review record that links to this disposition is not part of that reviewed candidate. It
may grant only the code authority described here and cannot replace the exact candidate identity.

## Final Authority Ceiling

The fixed governed tool count remains 24. The capability decision remains selection-only and
non-authorizing; this exact review and the separate authorization record are the code-authority
sources. Gateway truth, Node connectivity, runner-reported state, and model-provider state remain
separate.

Code authority is valid only while every current allowed runtime path exactly matches this reviewed
candidate. The authorization checker rejects staged, unstaged, deleted, renamed, and untracked
deltas, including recursive changes under `deploy/hermes-node-bridge`. Post-review control records
may change without silently authorizing changed runtime content.

All live Hermes/provider, Docker lifecycle, runner lifecycle, prompt/output evidence custody, `O4`,
release, promotion, production identity, UAT, host-control, and new-power authority remains false.
Tests, static evidence, and this review do not prove a live mission or authorize one.
