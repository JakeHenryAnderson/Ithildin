# Local v1 LV1-003 O4 Two-Operation Terminal Repair Exact Review

Status: `GO_CODE_ONLY`

Date: 2026-07-26

## Exact Candidate

- Commit: `897b22de9b3bd82113f37dc894fb8034f1a8799b`
- Tree: `b0ffb159a5449dfe1a5497c0016e15bafa92f2c1`
- Sole parent: `f33776a190bf9aa18e32741839a594b958d11a2d`

Relative to its sole parent, the candidate changes exactly these twelve paths:

| Path | SHA-256 |
| --- | --- |
| `apps/mcp-server/src/ithildin_mcp_server/node_bridge.py` | `f18f25744c089e12bf7a4a7ad2be3b92d6c0818cc3c296aef66b47dd73cc9ce3` |
| `apps/node/src/ithildin_node/fixed_runner_bridge.py` | `8f8e2600c096a973d2fe76cd84a3092f5c2f01e63418d6d2033f2ab5dd386e51` |
| `deploy/hermes-node-bridge/README.md` | `4feefc01ca37b2e7e1c6d7735f54932a08ba3a044e5a2b242ff072e2a3e50a93` |
| `deploy/hermes-node-bridge/compose.yaml` | `b0ae7d6bb3623f87fa3269120663dbbaa8bf8554d997c32da160054190f2153a` |
| `deploy/hermes-node-bridge/config.yaml` | `7d4b19943c26ff9ac7f277fa598f810790d7977ddcc2436aefba27523b2b17fb` |
| `deploy/hermes-node-bridge/fixed-instruction.md` | `a67a8e3c601e7eb6b0250c137817da63049721dc3743f7368d4efbdfac771745` |
| `deploy/hermes-node-bridge/profile.json` | `6f59c98cc2c47fd48e2aa2e2798df47ea201d88a1d80c33dfd89664a73e20b1e` |
| `docs/codex/mission-command-runner-bridge-capability-decision.md` | `0a3a9e0e729e92d589115b9529b46bbb33ae542adcc6cda0ef72c5d9df828c04` |
| `scripts/mission_command_runner_bridge_decision_check.py` | `d6a4f3d025681b3c34c6629983c4eae2cd20108dcddcbf801ee0b759f61b61ab` |
| `tests/test_mission_command_runner_bridge_decision_check.py` | `39542d7bf41ab1f8e87a60c5a92090788d6581e070b7585ac5cdd6741474b892` |
| `tests/test_node_fixed_runner_bridge.py` | `a83753b76823a63b5a0d65f19b64b9f2a3897b555925191dfe78ce7390f037b1` |
| `tests/test_node_mcp_bridge.py` | `a6eed1f857da15977c31fd54ee47dc34988d8a842af57a1a08d68cbacdee4d1a` |

The pushed upstream tracking ref equaled the candidate and the worktree was clean during review.

## Independent Review Disposition

One independent GPT-5.6 Sol high read-only review examined only the exact twelve-path candidate.
Sol xhigh and Ultra were not used.

Final findings:

- Critical: 0
- High: 0
- Medium: 0
- Low: 0

The exact-candidate disposition is `GO_CODE_ONLY`.

## Reviewed Terminal Contract

Only `mission.step.1` and `mission.step.2` are model-visible. They remain fixed, no-argument,
ordered bindings to `project.structure.summary` and `project.test.summary`.

After the second governed operation validates and closes, Node-owned logic polls signed mission
control, refreshes mission-bound liveness again immediately before reporting, submits
`runner_succeeded`, requires the Gateway lifecycle to advance to `runner_reported_succeeded`,
persists the terminal receipt, and returns terminal status. The response retains the second
operation's affordance, operation index, tool name, and governed-result binding while applying the
Node-owned terminal lifecycle fields. No third model-selected bookkeeping affordance is exposed or
required.

Invalid operation order, binding drift, malformed or unsuccessful governed results, rejected
heartbeat, invalid control state, cancellation, Gateway ambiguity, or an unadvanced terminal report
fails closed without publishing terminal success. A failure after the second governed operation
closes retains next operation index `3` only as private receipt progress; there is no corresponding
runner-visible affordance or retry authority.

## Boundary Review

The profile and Hermes configuration digests are internally consistent across the Node, MCP bridge,
immutable profile, and focused tests. The candidate adds no policy, manifest, API, schema,
dependency, tool, network destination, credential behavior, arbitrary host control, Docker
authority, provider authority, automatic retry, or governed power. The governed Gateway surface
remains exactly 24 tools.

Gateway lifecycle truth, Node connectivity, runner-reported lifecycle, and model-provider state
remain separate. Terminal success is still a validated runner report recorded by the Gateway; it
does not prove model correctness, output quality, provider completion, process exit, release
fitness, or UAT acceptance.

## Validation

The manager checkpoint and independent review passed:

- 48 focused fixed-runner bridge, MCP bridge, and decision-contract tests;
- Ruff across the changed production, validator, and test paths;
- strict mypy across the changed production and validator paths;
- JSON validation and immutable profile-digest parity;
- the runner-bridge decision validator with live authority false;
- the agent-workflow instruction check;
- the tool-surface invariant with exactly 24 tools;
- the no-new-powers guardrail with deferred boundaries unchanged;
- exact commit, tree, parent, twelve-path inventory, file digests, clean worktree, upstream parity,
  and `git diff --check`.

Pytest emitted only known non-failing temporary-directory cleanup warnings.

## Authority And Next Gate

Attempt018 remains permanently consumed. Its execution budget is zero and it cannot be rerun.

This implementation, its tests, and this review do not authorize Attempt019, an execution-review
tag, producer execution, Docker or Hermes activity, provider access, credential inspection,
release, promotion, production, or UAT.

This `GO_CODE_ONLY` permits preparation of a separate exact-candidate, one-shot Attempt019 execution
gate. That gate must bind this implementation candidate and the committed version of this review
record, receive its own bounded Sol-high exact review, require a fixed annotated candidate tag,
retain the prior five-field maximum live-authority ceiling, and require immediate consumed
disposition after exactly one invocation. Until all of those conditions pass, every live,
execution, release, promotion, production, and UAT authority remains false.
