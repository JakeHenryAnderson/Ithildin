# v3 project.release.summary Implementation Decision

Status: approved limited read-only implementation boundary; runtime is implemented.
This decision records the narrow implemented boundary for `project.release.summary`. It approves
exactly one bounded read-only manifest and executor path, with governed MCP exposure, policy
preview/runtime resource parity, and count-only audit metadata. It does not approve additional
policy rules, API behavior, UI behavior, approval behavior, broad traversal, execution behavior, or
future runtime changes outside this fixed surface. Tool count is `22`.

`project.release.summary` is approved only as a count-oriented local project release metadata
capability. It remains a narrow continuation of the read-only local metadata lane, not a new
powerful tool class.

## Approved Boundary

The approved boundary is limited to the bounded read-only runtime implementation that added exactly
one manifest and executor while all listed constraints continue to hold:

- tool name: `project.release.summary`;
- risk: `read`;
- category: `project`;
- resource type: `project_release`;
- input schema: closed object with `workspace_id`, `root`, `max_depth`, `limit`, and optional safe
  category filters;
- output schema: count-only release posture labels, skipped counts, limit metadata, and
  output-policy flags;
- workspace confinement: local workspace only and read-only;
- policy preview/runtime resource parity;
- policy parity: preview/runtime resource parity must remain aligned;
- release-check: later runtime evidence must pass release/readiness gates before activation.

## Required Non-Goals

Runtime behavior must preserve these non-goals:

- no release names;
- no version strings that reveal cadence;
- no changelog contents;
- no tag names;
- no branch names;
- no raw paths;
- no file contents;
- no package names;
- no dependency names;
- no author or maintainer names;
- no shell;
- no Git execution;
- no package-manager execution;
- no CI execution;
- no registry or network access;
- no deployment-readiness claims;
- no legal claims;
- no compliance claims;
- no broad recursive listing;
- no new powerful tool class.

## Future Implementation Evidence

The bounded runtime implementation provides:

- closed input schema evidence;
- workspace confinement evidence;
- traversal contract evidence;
- category allowlist evidence;
- skipped-count evidence;
- resource-limit evidence;
- policy preview/runtime parity evidence;
- count-only audit metadata evidence;
- negative transcripts;
- MCP governed path coverage;
- source-review bundle;
- no-new-powers evidence.

## Implementation State

Implementation state: implemented under this boundary.

This decision approves only the limited read-only boundary above. Future runtime changes outside
this fixed surface are not allowed without a later explicit implementation sprint and source review.

Current gate behavior: implementation-aware guard is active. While
`make project-release-summary-preimplementation-check` and
`make project-release-summary-implementation-gate` are wired into `make release-check`, the gate
must require the `project.release.summary` manifest, manifest-lock entry, runtime helper, resource
parity, and no-new-powers evidence. A low implementer must not alter this runtime surface.
