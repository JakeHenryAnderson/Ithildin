# v3 project.release.summary Selection

Status: design-only candidate selection.

`project.release.summary` is selected as the next bounded read-only project-intelligence candidate.
The current governed tool count remains `21`, and implementation remains blocked until a later
explicit implementation-boundary sprint approves a manifest, executor, policy/runtime resource
wiring, MCP exposure, audit coverage, negative transcripts, and source-review handoff.
Selected candidate status: design-only selected.

## Selection Rationale

`project.release.summary` is the safest useful continuation of the project metadata family. It
keeps release posture orientation bounded to count-only metadata and coarse labels rather than
release names, version strings, tag names, branch names, changelog contents, package names,
dependency names, or file contents.

That makes it useful for recognizing whether release-shaped artifacts exist without exposing the
human-facing release narrative or any execution surface.

## Boundary

This selection does not add a manifest, executor, policy rule, API/MCP behavior, UI runtime
behavior, approval behavior, audit behavior, or governed tool power.

Future implementation must remain:

- local workspace only;
- read-only;
- count-only and label-only;
- bounded by `workspace_id`, `root`, `max_depth`, `limit`, and optional safe category filters;
- resource-normalized as `project_release`;
- subject to policy preview/runtime parity before execution;
- covered by negative transcripts and source review before release readiness.

## Strict Non-Goals

The future proposal must not expose release names, release version strings when they reveal
product/customer cadence, changelog contents, tag names, branch names, package names, dependency
names, author or maintainer names, raw paths, file contents, shell access, Git execution,
package-manager execution, CI execution, registry or network access, deployment-readiness claims,
legal claims, compliance claims, or broad recursive listings.

## Required Next Gates

- `make project-release-summary-proposal-check`
- `make project-release-summary-implementation-plan-check`
- `make project-release-summary-design-review-packet`
- `make next-capability-readiness`

The design-review packet is for review only. It must not imply implementation approval.
