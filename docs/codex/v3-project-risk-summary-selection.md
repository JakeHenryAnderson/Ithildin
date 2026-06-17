# Project Risk Summary Candidate Selection

Status: historical design-only candidate selection.

`project.risk.summary` was selected as the next bounded read-only project-intelligence candidate.
At selection time, implementation was blocked until a later explicit implementation-boundary sprint
approved a manifest, executor, policy/runtime resource wiring, MCP exposure, audit coverage,
negative transcripts, and source-review handoff.

Post-implementation note: `project.risk.summary` has since advanced through a bounded read-only
runtime implementation. The current implementation boundary is recorded in
[v3 project.risk.summary Implementation](v3-project-risk-summary-implementation.md), and this
selection document is retained as historical proposal evidence.

## Selection Rationale

`project.risk.summary` extends the existing project metadata family without introducing a new power
class. The intended capability is count-only risk-signal posture metadata from workspace-local files,
using safe labels rather than filenames, dependency names, package names, CVE IDs, secrets, config
values, commands, raw paths, file contents, or vulnerability conclusions.

This is useful because an operator often needs to know whether a project has broad risk-shaped
signals, such as secrets-adjacent file patterns, release/config/CI/test/docs signal gaps, or
policy-sensitive metadata categories, without exposing the underlying sensitive material.

## Boundary

This selection does not add a manifest, executor, policy rule, API/MCP behavior, UI runtime
behavior, approval behavior, audit behavior, or governed tool power.

Future implementation must remain:

- local workspace only;
- read-only;
- count-only and label-only;
- bounded by `workspace_id`, `root`, `max_depth`, `limit`, and optional safe category filters;
- resource-normalized as `project_risk`;
- subject to policy preview/runtime parity before execution;
- covered by negative transcripts and source review before release readiness.

## Candidate Comparison

| Candidate | Value | Decision |
| --- | --- | --- |
| `project.risk.summary` | Count-only signal posture that can guide review without exposing sensitive material. | Selected for design-only planning. |
| `project.quality.summary` | Useful repo-hygiene posture, but overlaps with existing docs/test/config/CI summaries. | Defer until risk-signal boundaries are clearer. |
| `project.lifecycle.summary` | Useful lifecycle posture, but overlaps with CI/release/docs/test summaries. | Defer until the current project-intelligence family has more operator feedback. |

## Strict Non-Goals

The proposal must not expose filenames, raw paths, file contents, dependency names, package names,
CVE IDs, secret values, secret names, environment names or values, command/script values, registry
URLs, vulnerability findings, severity scores, compliance claims, security assurance, automatic
discovery, scanner execution, package-manager execution, shell execution, network access, or broad
recursive listings.

## Required Next Gates

- `make project-risk-summary-proposal-check`
- `make project-risk-summary-implementation-plan-check`
- `make project-risk-summary-design-review-packet`
- `make next-capability-readiness`

The design-review packet is for review only. It must not imply implementation approval.
