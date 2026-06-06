# Autonomous Sprint Guardrails

This protocol defines how Ithildin can make autonomous progress without turning review automation
into self-certification. It supports goal-driven implementation, but preserves explicit stop points
for status updates, reassessment, and external consultation.

## Sprint Protocol

- Work one formal goal at a time.
- Split each goal into task checkpoints with separate commits.
- Run the relevant focused tests before each checkpoint commit.
- Run full gates before moving to the next task when the task touches trust boundaries, generated
  evidence, policy, approvals, executors, MCP, or review-console behavior.
- Do not add a new powerful tool class without external/source review closure.
- Keep shell execution, Docker socket access, Kubernetes, browser automation, broad writes, plugin
  SDKs, production identity, runtime Postgres, hosted telemetry, and remote MCP deferred until a
  separate reviewed plan changes the boundary.

## Stop Conditions

Stop implementation and give a current status update when any of these happen:

- the same blocking failure repeats three times;
- a test reveals a trust-boundary regression;
- the implementation requires changing the product boundary or deferred-power list;
- a critical/high internal finding appears;
- source behavior contradicts the threat model, evidence contract, or release packet;
- the task cannot be completed without user input, secrets, admin credentials, or external state;
- the repo cannot be returned to a clean, verified checkpoint without risky rollback.

## Wall-Hit Status Format

When a wall is hit, stop and report:

- current commit and dirty state;
- active task and intended checkpoint;
- failing command or blocked action;
- suspected cause;
- attempted fixes or investigations;
- risk to the current boundary;
- recommended next options;
- whether external consultation is recommended.

Do not keep retrying blindly. External consultation is recommended when the issue touches security
architecture, unclear product scope, repeated executor/policy failures, or a possible release
blocking claim.

## External Review Cadence

External GPT 5.5 Pro / human expert review is required before:

- any new powerful tool class;
- broader public/security-product positioning;
- broad platform-support claims;
- closing a critical/high internal finding;
- changing production identity, storage, telemetry, MCP transport, or executor boundaries.

External review is also required after every 3-5 autonomous hardening sprints, or sooner if a
critical/high finding appears. It is optional after purely mechanical docs/evidence cleanup, as long
as the release packet and guardrails still pass.

## Internal Review Cadence

Run `make internal-review-packet` whenever a sprint touches a reviewed trust surface. Internal
AI/subagent review can produce backlog candidates, but it cannot independently close external-review
rows or authorize new tool powers.

## Model Tiering

Use this tiering model to keep autonomous work efficient without blurring review authority:

- Medium main driver: sprint coordination, sequencing, documentation, gate execution, evidence
  summaries, and escalation decisions.
- Low subagents: mechanical chores such as link checks, stale-wording scans, artifact inventories,
  packet sanity checks, and transcript summaries.
- High agents: implementation or review that touches API/runtime behavior, tests, policy,
  registries, audit evidence, executors, release gates, or review-console behavior.
- XHigh agents: milestone risk review, ambiguous architecture or product-boundary decisions,
  threat-model review, material disagreement resolution, and "should we proceed?" checkpoints.
- GPT 5.5 Pro / human expert review: external or break-glass consultation for new powerful tool
  classes, broader public/security-product positioning, unresolved critical/high findings, or
  material disagreement that internal review cannot resolve cleanly.

Low-tier agents must not independently change runtime code, policy semantics, executor behavior,
approval or audit logic, manifests, MCP exposure, auth/storage boundaries, or public trust claims.

Run `make review-candidate` before sending a new packet for external review. If it fails, treat the
packet as draft evidence and report status before continuing.
