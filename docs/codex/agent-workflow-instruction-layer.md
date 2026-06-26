# Agent Workflow Instruction Layer

This document records the repository-level planner-implementer workflow encoded in
[`AGENTS.md`](../../AGENTS.md). The goal is to reduce repeated prompt overhead while preserving
Ithildin's local-preview safety model.

`AGENTS.md` is always-on agent guidance. It is not a policy engine, sandbox, approval workflow, or security boundary. The enforceable controls remain the committed gates, tests, source-review
workflow, and human/user review.

## Roles

| Role | Allowed Work | Must Not Do |
| --- | --- | --- |
| Main Codex manager | Scope work, choose gates, review diffs, decide safety, commit. | Delegate final safety judgment. |
| Low Codex implementer | Preferred `gpt-5.4-mini` low-reasoning report-first path for docs links, stale wording scans, repetitive test wiring suggestions, packet inventories, and boilerplate from an existing pattern. Use one at a time by default. | Edit manifests, executors, policy semantics, approval/audit logic, MCP/API behavior, storage/auth boundaries, or trust claims. |
| Gemma/local-model suggester | Optional offline advisory pass for broad but shallow scans when latency is acceptable. | Directly edit files, act as the default implementer, or make safety/product judgments. |
| High implementer/reviewer | Bounded runtime/test work under an explicit plan and manager review. | Approve new product boundaries alone. |
| XHigh reviewer | Milestone risk review, ambiguous boundary review, break-glass consultation. | Replace external review for public/security-product positioning. |

## Delegation Packet Shape

When using a Low Codex implementer or optional Gemma/local-model suggester, give one narrow
assignment at a time:

```text
Task:
Allowed files:
Forbidden files:
Required phrases:
Forbidden changes:
Focused check:
Return only:
```

The main manager reviews the full diff before any commit. If the output is inconsistent, the manager
patches or discards it.

Low Codex delegation is report-first by default. Direct edits should remain disabled until several
read-only trials have produced useful suggestions with low cleanup cost and no boundary drift.

## Context Handoff

The main Codex manager should raise its hand and recommend a fresh chat when the current thread
becomes too context-heavy for reliable planning, review, or product-boundary judgment. This is an
efficiency practice, not a failure condition.

A handoff prompt should be paste-ready and include:

- current repo path, branch, commit, dirty state, and tool count;
- latest completed sprint and generated packet paths;
- gates that passed and any local ignored artifacts refreshed;
- current product boundary, deferred powers, delegation rules, and stop conditions;
- the next recommended sprint options and the commands a new chat should run first.

## Boundaries

The workflow must preserve the existing deferred-power list: no shell execution, Docker socket,
Kubernetes tools, browser automation, arbitrary HTTP methods/headers/bodies, broad filesystem writes,
production identity, runtime Postgres, hosted telemetry, remote MCP hosting, plugin SDK behavior,
secrets-manager tools, sandbox orchestration, SIEM adapters, compliance automation, or public
security-product claims.

Tool-count changes require explicit proposal, plan, gate, manifest lock update, policy/parity
coverage, source-review handoff, and release/readiness updates. The current governed tool count is 24.

## Validation

Run:

```sh
make agent-workflow-check
```

The check verifies that `AGENTS.md`, this role contract, README command references, docs-site inputs,
and review-doc metadata preserve the workflow and boundary language.
