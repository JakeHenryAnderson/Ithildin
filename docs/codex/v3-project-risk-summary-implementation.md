# project.risk.summary Implementation Boundary

Status: approved boundary for a later limited read-only implementation.

This document records the implementation boundary for the proposed `project.risk.summary`
capability. It does not add runtime behavior in this sprint. A later explicit implementation sprint
may add one bounded read-only tool only if it preserves this boundary, updates the manifest lock, and
passes the source-review handoff and release gates.

## Decision

`project.risk.summary` may be implemented later as one governed read-only project metadata tool.

Approved shape:

- tool name: `project.risk.summary`;
- risk `read`;
- category `project`;
- resource type `project_risk`;
- MCP exposed only through the existing governed read-only path;
- fixed workspace-confined traversal;
- count-only risk signal metadata and allowlisted labels only;
- no scanner execution, no vulnerability finding generation, and no compliance or security
  assurance claims.

Current state:

- tool count remains `22`;
- no tool manifest is added by this boundary sprint;
- runtime behavior is not changed by this boundary sprint;
- implementation remains blocked until a later explicit runtime implementation task.

## Future Input Contract

A later implementation may use only the bounded input sketch from the implementation plan:

- `workspace_id`;
- `root`;
- `max_depth`;
- `limit`;
- `include_categories`.

Inputs must remain closed-schema and bounded. The future tool must reject traversal, absolute paths,
encoded ambiguity, control characters, oversized values, unsupported fields, and malformed argument
types with safe errors.

## Future Output Contract

A later implementation may return only safe counts and coarse labels, such as:

- risk-signal category counts;
- posture bucket counts;
- location-bucket counts;
- skipped counts;
- limit and truncation metadata;
- output-policy flags;
- resource/audit evidence keys.

The output must not include raw evidence items, filenames, raw paths, file contents, dependency
names, package names, CVE IDs, advisory IDs, secret names or values, environment names or values,
command/script values, registry URLs, scanner output, vulnerability findings, compliance findings,
security findings, or raw filesystem errors.

For gate clarity, the exact strict non-leak phrases are:

- no filenames;
- no raw paths;
- no file contents;
- no dependency names;
- no package names;
- no CVE IDs;
- no advisory IDs;
- no secret names or values;
- no command/script values;
- no registry URLs;
- no scanner output;
- no vulnerability findings;
- no compliance findings;
- no compliance or security assurance claims.

## Explicit Non-Goals

The future tool must not become any of these:

- vulnerability scanning;
- dependency vulnerability analysis;
- static application security testing;
- secret scanning;
- compliance automation;
- security assurance;
- scanner orchestration;
- registry/network lookup;
- package-manager execution;
- shell execution;
- CI execution;
- Docker, Kubernetes, browser, or sandbox orchestration;
- broad recursive listing;
- broad filesystem write/read expansion;
- production identity, hosted telemetry, runtime Postgres, remote MCP, plugin SDK, or SIEM adapter
  behavior.

## Evidence Required Before Runtime

Before any runtime implementation is merged, the following must exist and pass:

- `make project-risk-summary-implementation-gate`;
- `make project-risk-summary-preimplementation-check`;
- source-review handoff docs and negative transcript plan;
- future runtime tests for executor, governed call, policy parity, MCP list/call, audit metadata, and
  safe denial behavior;
- manifest lock update and tool-surface invariant update;
- `make release-check`;
- source-review bundle for `project.risk.summary`.

Broader capability expansion remains blocked. This boundary approves only the possibility of a later
single bounded read-only metadata tool.
