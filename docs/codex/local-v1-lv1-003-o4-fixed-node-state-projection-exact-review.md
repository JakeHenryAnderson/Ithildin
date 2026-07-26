# Local v1 LV1-003 O4 Fixed-Node State Projection Exact Review

Status: `GO_CODE_ONLY`

Date: 2026-07-26

## Exact Candidate

- Commit: `2683641c619e8ae5ac93bdec0d9503f83dd79a35`
- Tree: `0bfa56ac2fb4c614c5fcc5695d05a664f804beac`
- Exact parent: `fa23ddef1e8b98c24c312d91d482bac79b44bd68`
- `scripts/local_v1_lv1_003_o4_producer.py`:
  `sha256:e2e7e91e2314fd7322a6dcee8f02e14fb61f02c4afa007e8c29cdd66a1302ae8`
- `tests/test_local_v1_lv1_003_o4_producer.py`:
  `sha256:1d704b16729f28f2cc2cecb1957f4478850323c58f89a9279e215df713eb60ea`

The exact candidate changes only those two paths. All thirteen non-target governed runtime paths
are byte-identical to the exact parent.

## Independent Review Disposition

Independent GPT-5.6 Sol xhigh read-only review found:

- Critical: 0
- High: 0
- Medium: 0
- Low: 0

The exact-candidate disposition is `GO_CODE_ONLY`. The review applies only to the commit, tree,
parent, path inventory, and file digests above.

## Reviewed Refinement

The exact candidate refines only the already collected fixed-Node startup diagnostic scalars. It
adds no executor command, API request, retry, polling loop, log collection, lifecycle action,
Hermes action, provider access, credential access, or host-control capability.

Every diagnostic record uses the same closed thirteen-key schema. Container observations normalize
to:

- presence: `present`, `missing`, or `unknown`;
- lifecycle: the closed Docker lifecycle values, `not_applicable`, or `unknown`;
- running state: `running`, `not_running`, `not_applicable`, or `unknown`;
- exit class: `zero`, `nonzero`, `not_applicable`, or `unknown`;
- health: `absent`, `starting`, `healthy`, `unhealthy`, `not_applicable`, or `unknown`;
- failure signal: `none`, `oom_killed`, `dead_flag`, `engine_error_present`, `multiple`,
  `not_applicable`, or `unknown`; and
- observation semantics: `sequential_container_then_mission` or `not_collected`.

The retained mission projection remains limited to `mission_lifecycle_state`, `delivery_state`, and
`evidence_state`. Complete diagnostic results no longer use the generic
`fixed_node_runtime_state_inconsistent` classification. They distinguish closed observational
categories for noncanonical exited state, zero exit with a later claim observation, running
without a health observation, running while health is starting, running while healthy,
noncanonical running state, and paused state. Existing precise missing, created, runtime-error,
claim-inconsistency, nonzero-exit, queued-zero-exit, and unhealthy socket-health categories remain.

The container observation precedes the mission query. The normalized fields are sequential
point-in-time observations, not one atomic snapshot. Category names and retained fields do not
claim causality or establish a fixed-Node root cause.

## Privacy And Failure Semantics

The retained projection contains no raw container, Node, image, mission, or claim identity; raw
exit integer; engine-error text; stdout; stderr; log; environment; mount; configuration; requester;
digest; whole mission object; credential; prompt; provider output; or arbitrary API object.

Missing, malformed, ambiguous, hostile, oversized, non-ASCII, control-character, secret-like,
interrupted, timed-out, failed, or unforeseen collection remains fail-closed as `inconclusive` or
`output_rejected`. Diagnostic failure does not mask primary `fixed_node_start_failed`. The
producer still collects at most once, discards the temporarily bound container identity, performs
no Hermes attempt or retry after the primary failure, and invokes the existing cleanup once.

## Validation

The exact review and manager checkpoint passed:

- 242 producer tests;
- 28 unchanged Node service and fixed-runner-bridge tests;
- the fake-only producer, authorization-negative, and constrained-journey static suite;
- Ruff and strict mypy for the changed production module;
- the agent-workflow instruction check;
- the tool-surface invariant with exactly 24 tools;
- the no-new-powers guardrail with deferred boundaries unchanged;
- an independent 67,200-case classifier audit spanning every parser-accepted container lifecycle,
  boolean signal combination, representative zero and nonzero exit value, health state, mission
  lifecycle, and delivery state;
- exact non-target runtime parity; and
- `git diff --check` and a clean final worktree.

Pytest emitted only known non-failing cleanup warnings for synthetic temporary directories outside
the repository.

## Consumed Authority

Attempt 011 remains consumed. Its execution budget is zero, retry is false, and all nineteen
authority fields remain false. The existing source-binding validator rejects the reviewed
refinement because both changed file digests intentionally differ from the Attempt 011
authorization. Live execution, Docker lifecycle, Hermes, provider access, O4 evidence execution,
release, promotion, production, and UAT therefore remain unavailable.

## Evidence Limits And Next Gate

This implementation, its tests, and the exact review are code and diagnostic-design evidence only.
They do not prove the fixed-Node root cause, prove that a future attempt will succeed, establish a
safe retry, reproduce or inspect private Attempt 011 receipt contents, prove generic runtime or
service absence, complete O4, qualify a release candidate, or complete UAT.

This review permits preparation of a separate candidate-bound, one-shot diagnostic execution
authorization for a future Attempt 012. Such preparation must remain a distinct control record and
must receive its own exact-candidate review before any tag or execution can exist. This record does
not authorize that attempt, a tag, Docker or provider activity, cleanup, release, promotion,
production, or UAT. The governed tool count remains exactly 24.
