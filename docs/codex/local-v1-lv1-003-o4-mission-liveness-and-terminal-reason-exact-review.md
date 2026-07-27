# Local v1 LV1-003 O4 Mission Liveness And Terminal Reason Exact Review

Status: `GO_CODE_ONLY`

Date: 2026-07-26

## Exact Candidate

- Commit: `694e464d79afd00bc6af7f847acd3c7901fa4086`
- Tree: `2bdb9e12e9ae65ea71064e8caf20ae3ce5fcda58`
- Direct parent, initially reviewed candidate:
  `cfbaf448cbef89aa6a34f4339954051797f70afa`
- Consumed Attempt017 closure baseline:
  `96b19b3297d514a92abae1440afcbcbd052db3c8`

Relative to the consumed closure baseline, the candidate changes exactly these nine paths:

| Path | SHA-256 |
| --- | --- |
| `apps/node/src/ithildin_node/fixed_runner_bridge.py` | `a0ff5355295b8b694539676c0241c6627320606f8c9d5a389830d7966184b896` |
| `apps/node/src/ithildin_node/service.py` | `8b0487f803379e87471cdf15ca8cc42d7c18d390fb8ef0eb7d03a21b27b162f3` |
| `docs/codex/mission-command-runner-bridge-capability-decision.md` | `cc702776aede4805f2e7539a1b20181e94af9ce42a9cf0f5ef3db1c28b02005b` |
| `scripts/local_v1_lv1_003_o4_producer.py` | `798be3148b9a49837b3c2f8e8d50fa555be2295f663aac96ef814dee38be23ff` |
| `scripts/mission_command_runner_bridge_decision_check.py` | `5010506fb7934cf628e59a56844c39659915a6389f9ed5fddad4861cdf577195` |
| `tests/test_local_v1_lv1_003_o4_producer.py` | `c8260167e0be89a37adfe85559f11671da21cc2c2628b26779b46e0f4fe634a6` |
| `tests/test_mission_command_runner_bridge_decision_check.py` | `5fecf5b3d16d29996ff722c93e6ab8f29affee3dc18bda497deebe4a641a18e3` |
| `tests/test_node_client.py` | `28a14d7007a4a56024437aa9dc5d25ad3dd0e7d6b2f23497c35b68310e191aa8` |
| `tests/test_node_fixed_runner_bridge.py` | `1e502f7e2630ed146c53d657d6ca81ea7fbcea8dc5ab8f522802dea07e9eb21d` |

The direct repair commit changes only the fixed runner bridge and its focused tests. The pushed
upstream tracking ref equaled the repair candidate and the worktree was clean during the closure
review.

## Independent Review Disposition

One independent GPT-5.6 Sol high read-only review initially found one Medium issue: the cancellation
and successful-completion paths reused the heartbeat validated before the immediately preceding
mission-control poll instead of refreshing again immediately before the terminal runner report.
The candidate added the two missing refreshes and order-sensitive negative tests. The same reviewer
verified only that two-path repair and closed the finding.

Final findings:

- Critical: 0
- High: 0
- Medium: 0
- Low: 0

The exact-candidate disposition is `GO_CODE_ONLY`. Sol xhigh and Ultra were not used. This review
applies only to the exact commit, tree, lineage, path inventory, and file digests above.

## Reviewed Liveness Contract

The fixed mission session sends a signed mission-bound heartbeat and validates the Gateway response
immediately before each runner report and each mission-control poll. Validation requires the
Gateway to report the Node connected with the exact active configuration digest and exact current
mission binding. An unavailable or rejected heartbeat fails the fixed session closed before the
subsequent report or poll.

A successful two-operation mission therefore performs five in-session heartbeats: one before the
running report, one before each of three mission-control polls, and one before the successful
terminal report. A cancellation decision is followed by a separate fresh heartbeat before the
bounded cancellation-observed report. Rejection of either terminal-report heartbeat suppresses
that report and persists the closed reason `gateway_heartbeat_invalid`.

The private bridge receipt retains only a closed terminal reason code. Success records `none`;
failure or cancellation records an allowlisted stable code. The producer may project only the
allowlisted identity-free value and rejects an inconsistent success receipt. No response body,
exception text, credential, runner output, provider state, mission identity, Node identity, or
arbitrary private value is promoted.

## Boundary Review

The candidate adds no command, network destination, API family, retry, arbitrary host control,
Docker authority, provider authority, credential behavior, governed tool, or governed power.
Mission liveness remains Gateway-observed connectivity, not runner-reported state or model-provider
state. The governed tool count remains exactly 24.

The closed terminal reason is diagnostic evidence only. It does not establish causality, prove a
successful O4 journey, authorize a retry, or qualify a release.

## Validation

The manager checkpoint and independent review passed:

- the complete fixed-runner bridge test module, including the two order-sensitive terminal-report
  regressions;
- the three directly relevant tests independently selected by the reviewer;
- the previously collected focused Node runtime, producer, decision-validator, and client tests for
  the nine-path candidate;
- Ruff across the production and test paths;
- strict mypy across the production paths;
- the docs-site checks;
- the agent-workflow instruction check;
- the tool-surface invariant with exactly 24 tools;
- the no-new-powers guardrail with deferred boundaries unchanged;
- exact lineage, nine-path candidate inventory, two-path repair inventory, file digests, clean
  candidate diff, and `git diff --check`.

Pytest emitted only the known non-failing temporary-directory cleanup warnings.

## Consumed Authority And Next Gate

Attempt017 remains permanently consumed. Its execution budget is zero, all live authority remains
false, and it cannot be rerun.

This implementation, its tests, and this review do not authorize Attempt018, an annotated review
tag, producer execution, retry, automatic retry, Docker or Hermes activity, provider access,
release, promotion, production, or UAT.

This `GO_CODE_ONLY` disposition permits preparation of a separate exact-candidate, one-shot
Attempt018 execution gate. That gate must bind this implementation candidate and the committed
version of this review record, receive its own exact review, require a fixed annotated candidate
tag, retain the prior five-field maximum live-authority ceiling, and require immediate consumed
disposition after exactly one invocation. Until all of those conditions pass, every live,
execution, release, promotion, production, and UAT authority remains false.
