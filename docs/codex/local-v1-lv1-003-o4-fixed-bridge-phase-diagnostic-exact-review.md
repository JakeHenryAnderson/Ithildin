# Local v1 LV1-003 O4 Fixed-Bridge Phase Diagnostic Exact Review

Status: `GO_CODE_ONLY`

Date: 2026-07-26

## Exact Candidate

- Commit: `4972606a0677164d8de96a4b3e14ce5bead75033`
- Tree: `a7e5cbfb849f974a142c6861f79af26498bebb3d`
- Direct parent, rejected candidate:
  `f8af8a0ec471f607490df094ce5df4f4de3e9381`
- Consumed Attempt 012 closure baseline:
  `5446b1d65c09df515592fc61799b368035bfad8f`

Relative to the closure baseline, the candidate changes exactly these six paths:

| Path | SHA-256 |
| --- | --- |
| `apps/node/src/ithildin_node/fixed_runner_bridge.py` | `19b9ef3f73066c826560283b0209c9eab20696b2be235c9c50a2f95fc01f6f35` |
| `apps/node/src/ithildin_node/service.py` | `d61798ede4d11c149ddedd76339d2dc84b966ca9c2fd83b72396963c244d1fb9` |
| `scripts/local_v1_lv1_003_o4_producer.py` | `241de5ef6da3e47d9e760001a7eb1a4a3281c96e3b3010a12c6f187d8e09dafc` |
| `tests/test_node_fixed_runner_bridge.py` | `0852b55bf1ff216421030d796f7e3d68085877c7288728b2c7a8a995652bae8d` |
| `tests/test_node_service.py` | `0ebd161d5e39234b829601e6ed9a7bb7c3e16b8cb1e7d9c78e933576ac77e2ff` |
| `tests/test_local_v1_lv1_003_o4_producer.py` | `5cb506309d4a8e09142795ee11f603f3dd47bcba67da29ae7b9cf4a793287bd3` |

The direct repair commit changes only the producer and producer tests. The pushed upstream tracking
ref equaled the exact candidate and the worktree was clean during the final review.

## Independent Review Disposition

Independent GPT-5.6 Sol xhigh read-only review found:

- Critical: 0
- High: 0
- Medium: 0
- Low: 0

The exact-candidate disposition is `GO_CODE_ONLY`. The review applies only to the commit, tree,
lineage, exact path inventory, and file digests above.

The earlier candidate `f8af8a0ec471f607490df094ce5df4f4de3e9381` received `NO_GO` with one
Medium finding because a reserved exit code could project a named bridge phase even when the same
container observation was nonterminal or contradictory. That candidate was not tagged or used to
prepare execution authority. The replacement candidate closes the finding before serialization:
a named phase survives only when the bound observation is `exited`, not running, has absent health,
and has no OOM, dead, or engine-error signal. Every other accepted present observation normalizes
the phase to `not_reported`.

## Reviewed Diagnostic Contract

The fixed bridge emits one of nine closed, non-authoritative last-entered phase markers:

| Reserved exit | Closed phase |
| --- | --- |
| `80` | `fixed_bridge_entered` |
| `81` | `preclaim_validation_entered` |
| `82` | `mission_claim_entered` |
| `83` | `session_validation_entered` |
| `84` | `receipt_persistence_entered` |
| `85` | `socket_parent_validation_entered` |
| `86` | `socket_bind_entered` |
| `87` | `socket_permissions_entered` |
| `88` | `listener_accept_entered` |

The phase hook is default-noop, in-memory, and non-authoritative. Hook failure cannot change bridge
control flow. Reserved exits apply only to the fixed `hermes_fixed_node_bridge` adapter running
exactly one service cycle and only after a phase was entered. A pre-bridge failure remains exit
`1`; ordinary adapters and successful fixed cycles retain their existing behavior.

`listener_accept_entered` is emitted only after the socket is bound, ownership and mode validation
passes, `listen()` succeeds, and the listener timeout is installed. It says only that the listener
was ready before entering `accept()`. No phase establishes success, causality, root cause, retry
safety, or execution authority.

The producer converts a canonical reserved exit into the corresponding closed phase name and
discards the raw exit integer. A canonical present container with any other exit uses
`not_reported`; contradictory or nonterminal present observations also use `not_reported`; an
absent container uses `not_applicable`; and rejected or inconclusive collection uses `unknown`.
The retained diagnostic is the prior closed sequential projection plus
`fixed_bridge_last_entered_phase`. Its container observation still precedes the mission query and
does not claim one atomic snapshot.

## Boundary And Privacy Review

The candidate adds no Docker command, log access, stdout or stderr retention, file, mount, volume
read, API request, polling loop, retry, Hermes action, provider access, credential access, lifecycle
action, arbitrary host control, or governed tool. The exact command vocabulary, inspect count,
single diagnostic collection, no-Hermes-on-wait-failure behavior, and one cleanup remain unchanged.

The retained diagnostic contains no raw exit integer, container, Node, image, mission, or claim
identity, exception text, process output, log, environment, mount, configuration, credential,
prompt, or provider output. Missing, malformed, hostile, contradictory, interrupted, failed, or
inconclusive observations remain closed.

## Validation

The exact review and manager checkpoint passed:

- 315 focused tests: 27 fixed bridge, 18 Node service, and 270 producer;
- Ruff across the exact six paths;
- strict mypy across the three production paths;
- an independent 4,032-case audit spanning every accepted container lifecycle, running and failure
  Boolean combination, health state, and reserved exit;
- the agent-workflow instruction check;
- the tool-surface invariant with exactly 24 tools;
- the no-new-powers guardrail with deferred boundaries unchanged;
- exact six-path and direct two-path repair inventories;
- `git diff --check`; and
- a clean final worktree.

Pytest emitted only the known non-failing cleanup warnings for synthetic temporary directories
outside the repository.

## Consumed Authority And Next Gate

Attempt 012 remains consumed. Its execution budget is zero, retry and automatic retry are false,
and all nineteen live authority fields remain false. The existing Attempt 012 authorization
intentionally binds the previous thirteen-field diagnostic and cannot authorize this fourteen-field
candidate.

This implementation, its tests, and this review do not prove the fixed-Node root cause or a safe
repair, establish a successful O4 journey, create a retry, authorize a tag, access private retained
evidence, qualify a release, or complete UAT.

This review permits preparation of a separate exact-candidate, one-shot successor execution gate.
That gate must bind the candidate and this durable review record, receive its own independent exact
review, require a fixed annotated candidate tag, retain the prior five-field maximum live-authority
ceiling, and require immediate consumed disposition after exactly one invocation. Until those
conditions are satisfied, Docker, Hermes, provider, O4 execution, release, promotion, production,
and UAT authority remain false. The governed tool count remains exactly 24.
