# v3 project.release.summary Implementation Decision

Status: approved limited read-only implementation boundary, but runtime not yet implemented.
This decision records the narrow future boundary for `project.release.summary`; it does not add a
tool manifest, executor, policy rule, API/MCP behavior, UI behavior, approval behavior, audit
behavior, or runtime behavior in this sprint. Tool count remains `21` until a future
implementation commit.

`project.release.summary` is approved only as a count-oriented local project release metadata
capability. It remains a narrow continuation of the read-only local metadata lane, not a new
powerful tool class.

## Approved Boundary

The approved boundary is limited to a future bounded read-only runtime implementation that may add
exactly one manifest and executor only if all listed constraints continue to hold:

- tool name: `project.release.summary`;
- risk: `read`;
- category: `project`;
- proposed resource type: `project_release`;
- input schema: closed object with `workspace_id`, `root`, `max_depth`, `limit`, and optional safe
  category filters;
- output schema: count-only release posture labels, skipped counts, limit metadata, and
  output-policy flags;
- workspace confinement: local workspace only and read-only;
- policy preview/runtime resource parity;
- policy parity: preview/runtime resource parity must remain aligned;
- release-check: later runtime evidence must pass release/readiness gates before activation.

## Required Non-Goals

Future runtime work must preserve these non-goals:

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

If the later bounded runtime sprint is approved, it must provide:

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

Implementation state: blocked in this sprint.

This decision approves only the limited read-only boundary above. Runtime changes outside this
fixed surface are not allowed without a later explicit implementation sprint and source review.

Current gate behavior: preimplementation guard remains active. While
`make project-release-summary-preimplementation-check` and
`make project-release-summary-implementation-gate` are wired into `make release-check`, the gate
must fail closed if a `project.release.summary` manifest, manifest-lock entry, or runtime helper is
added. The next runtime sprint must explicitly retire or replace this preimplementation guard as
part of the implementation checkpoint before adding runtime source. Do not delegate
`project.release.summary` runtime source to a low implementer while this gate is active.
