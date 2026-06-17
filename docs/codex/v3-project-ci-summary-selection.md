# Project CI Summary Candidate Selection

Status: design-only candidate selection.

`project.ci.summary` is selected as the next bounded read-only project-intelligence candidate. The current governed tool count remains `23`, and implementation remains blocked until a later explicit implementation-boundary sprint approves a manifest, executor, policy/runtime resource wiring, MCP exposure, audit coverage, negative transcripts, and source-review handoff.

## Selection Rationale

`project.ci.summary` extends the existing project metadata family without introducing a new power class. The intended capability is count-only CI posture metadata from workspace-local files, using safe provider and category labels rather than workflow names, raw paths, command values, file contents, or CI execution.

This is useful because CI configuration posture often tells an operator whether a project has build, test, lint, release, security-scan, or deployment-shaped automation without needing to expose the automation itself.

## Boundary

This selection does not add a manifest, executor, policy rule, API/MCP behavior, UI runtime behavior, approval behavior, audit behavior, or governed tool power.

Future implementation must remain:

- local workspace only;
- read-only;
- count-only and label-only;
- bounded by `workspace_id`, `root`, `max_depth`, `limit`, and optional safe category filters;
- resource-normalized as `project_ci`;
- subject to policy preview/runtime parity before execution;
- covered by negative transcripts and source review before release readiness.

## Strict Non-Goals

The proposal must not expose workflow names, raw paths, file contents, command/script values, environment names or values, secrets, dependency names, registry or network access, CI execution, shell execution, deployment-readiness claims, compliance claims, or broad recursive listings.

## Required Next Gates

- `make project-ci-summary-proposal-check`
- `make project-ci-summary-implementation-plan-check`
- `make project-ci-summary-design-review-packet`
- `make next-capability-readiness`

The design-review packet is for review only. It must not imply implementation approval.
