# Local v1 LV1-003 O4 Mission Convergence Exact Review

Status: `GO_CODE_ONLY`

Date: 2026-07-26

## Exact Candidate

- Commit: `f222091c86b71162a3eef5e7518ef0f032cc65ec`
- Tree: `7683d2de4dbca2367189e2b807818e641f1e3e8b`
- Direct parent: `589c9bc721330e92e0298b86b873d007234b8c49`

Relative to the direct parent, the candidate changes exactly seven paths:

| Path | SHA-256 |
| --- | --- |
| `apps/mcp-server/src/ithildin_mcp_server/node_bridge.py` | `a6349d5a8556f53012594a6c254ce25153e4a089f210cc59008f26000a24ff17` |
| `apps/node/src/ithildin_node/fixed_runner_bridge.py` | `f2db686b921b7fad5942d2c1881b1b5e25c3aee6af49dff09f85480cd4396d3c` |
| `scripts/local_v1_lv1_003_o4_producer.py` | `bfbe59861cf4ccc8acb7bd2204010559aa8e43e2c730ad92a68aa20ada5e2e8e` |
| `tests/test_local_v1_lv1_003_o4_producer.py` | `3c0e360b42bdcec2a5d3aeb4b533d31c257cff601ed1fb02c630bb8186660a99` |
| `tests/test_node_client.py` | `7c7c0dcac8c505be40e60d7366498be49943a839986a92f370b7dc1ec15107ef` |
| `tests/test_node_fixed_runner_bridge.py` | `7c2d50cf01ee6049e6af32167dd9d98ffd69b031e32cf340feff13a2094399b4` |
| `tests/test_node_mcp_bridge.py` | `74175632afe0d8a3954de92b43a3830ec78bfa800888b90cf75a33e87dcc885a` |

The exact candidate and its upstream tracking ref were clean during the final review.

## Independent Review Disposition

One independent GPT-5.6 Sol high read-only review initially found one Medium issue. A denied or
otherwise terminal bridge response could derive a non-`none` `next_required_affordance` solely from
the retained operation index, even though the session was terminating and restart was blocked.

The amended candidate closes the finding:

- request errors fail-close a nonterminal receipt before rendering the denial;
- existing terminal states such as `cancel_observed` remain intact;
- every terminal receipt projects `next_required_affordance` as `none`; and
- negative tests cover malformed-request denial, an unadvanced Gateway report, and cancellation.

The same reviewer verified the amended exact candidate and closed the finding.

Final findings:

- Critical: 0
- High: 0
- Medium: 0
- Low: 0

The exact-candidate disposition is `GO_CODE_ONLY`. Sol xhigh and Ultra were not used. This review
applies only to the exact commit, tree, parent, seven-path inventory, and file digests above.

## Reviewed Convergence Semantics

The fixed runner bridge now records `runner_reported_running` or `runner_reported_succeeded` only
after the synchronous Gateway response reports the matching lifecycle state and a valid lifecycle
revision. A missing, malformed, or unadvanced response fail-closes the local receipt and does not
advance it.

The MCP bridge still exposes only the existing three no-argument affordances. Its server
instructions, tool descriptions, and identity-free `next_required_affordance` value explain the
already reviewed fixed sequence; they do not invoke a tool, complete a mission automatically, add
an affordance, or grant authority.

After Hermes exits successfully, the producer copies the existing Node receipt once before checking
the Gateway journey. If the journey fails, the private diagnostic can distinguish a closed
`completion_pending` observation from `completion_recorded` without retaining raw mission, claim,
envelope, nonce, Node, project, container, or provider identity. The raw receipt remains subject to
the existing exact success binding and is not published.

## Boundary Review

Gateway lifecycle truth remains Gateway-owned. The Node receipt remains runner-reported evidence.
The model provider state remains explicitly unknown. The candidate adds no retry, polling loop,
automatic completion, Docker command, network target, credential behavior, arbitrary host control,
public evidence, governed tool, or governed power. The governed tool count remains exactly 24.

The candidate does not prove why Attempt 016 remained running, predict a later attempt's success,
authorize Attempt 017, establish successful O4 evidence, or qualify release, promotion,
production, or UAT.

## Validation

The manager checkpoint and independent review passed:

- 344 tests across the complete producer, fixed runner bridge, MCP bridge, and Node client files
  before the review repair;
- 37 complete fixed-runner/MCP bridge tests after the review repair;
- five focused terminal-denial, Gateway-report, cancellation, and happy-path tests;
- Ruff across all seven changed paths;
- strict mypy across all three changed runtime modules;
- the agent-workflow instruction check;
- the tool-surface invariant with exactly 24 tools;
- the no-new-powers guardrail with deferred boundaries unchanged; and
- exact lineage, seven-path inventory, file digests, clean candidate state, and
  `git diff --check`.

Pytest emitted only the known non-failing ambient temporary-directory cleanup warnings.

## Authority And Next Gate

This review grants a code-only disposition for the exact candidate. It does not authorize another
O4 execution, retry, automatic retry, Docker lifecycle, Hermes execution, model-provider access,
credential custody, arbitrary host/process/shell/Docker-socket control, release, promotion,
production, or UAT.

Attempt 017 requires a separate exact-candidate authorization gate with one bounded supervised
budget, its own annotated review tag, and immediate consumed disposition after invocation. No
execution authority exists in this record.
