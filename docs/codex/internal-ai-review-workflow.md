# Internal AI Review Workflow

This workflow uses high-intelligence AI/subagent review as repeatable internal pressure testing. It
is useful for catching drift and sharpening findings, but it is not an independent external audit
and does not replace GPT 5.5 Pro or human expert review at major gates.

## Command

```sh
make internal-review-packet
```

The command writes ignored prompt files under
`var/review-packets/v0.3/internal-ai-review-packet/`. It does not call an external model, mutate
runtime state, create approvals, write audit events, or add tool powers.

## Review Areas

- Patch apply approval binding and recovery evidence.
- Filesystem workspace and race semantics.
- HTTP fetch SSRF and canonicalization.
- Signed audit export and manifest-lock evidence.
- Policy preview/runtime parity.
- Manifest, principal, and workspace registry fail-closed behavior.
- Release evidence automation and guardrails.
- MCP ingress thinness.
- Review console approval evidence.

## Finding Intake

Every AI/subagent finding must be converted into
[reviewer-finding-template.md](reviewer-finding-template.md) format before it becomes backlog work.
Record source files/functions, claim tested, observed behavior, risk, recommended fix, blocking
status, disposition, and verification notes.

Internal findings may update [source-review-closure-matrix.md](source-review-closure-matrix.md), but
must be labeled as internal review. External rows remain pending until GPT 5.5 Pro or a human expert
reviews the relevant source/evidence.

## Use As A Proxy, Not A Gate

Internal AI review can run every hardening sprint. External review remains required before:

- adding any new powerful tool class;
- claiming broader platform support;
- public/security-product positioning;
- accepting or closing any critical/high internal finding;
- changing identity, storage, telemetry, MCP transport, or executor boundaries.

Use [autonomous-sprint-guardrails.md](autonomous-sprint-guardrails.md) for the stop conditions and
wall-hit status format that apply when internal review or test failures expose a possible boundary
problem.

The default tiering model is:

- Medium main driver for coordination, documentation, evidence, and gate execution.
- Low subagents only for mechanical review chores such as link scans, stale wording checks, packet
  inventory, and transcript summaries.
- High agents for implementation or review that touches runtime behavior, tests, policy, registry,
  audit, executor, release-gate, or UI trust surfaces.
- XHigh agents for milestone risk review, ambiguous product-boundary decisions, threat-model
  questions, and "should we proceed?" checkpoints.
- GPT 5.5 Pro or human expert review remains the external and break-glass path for major boundary
  decisions, new powerful tool classes, or unresolved critical/high findings.

Low-tier subagents must not independently modify runtime code, policy semantics, executor behavior,
approval or audit logic, manifests, MCP exposure, storage/auth boundaries, or public trust claims.
All AI/subagent review remains internal pressure testing unless an external reviewer explicitly
closes the relevant row.

For the v0.6 lane-by-lane proxy-review cadence, use
[v0.6-internal-proxy-review-operating-model.md](v0.6-internal-proxy-review-operating-model.md).

## Prompt Template

Use the generated area prompts as the source of truth. Each prompt asks the reviewer to inspect
specific files/functions, test concrete claims, cite evidence, and produce findings in the shared
template. If a reviewer proposes broad new capabilities, treat that as out of scope and convert only
trust-boundary or hardening findings into tasks.
