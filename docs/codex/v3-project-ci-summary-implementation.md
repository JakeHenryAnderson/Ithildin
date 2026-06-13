# v3 project.ci.summary Implementation Decision

Status: approved_limited_read_only runtime implementation.

This record approves exactly one bounded read-only runtime implementation for `project.ci.summary`.
It may add one tool manifest and one executor dispatch path. Runtime behavior is bounded read-only
and must stay inside the existing project-intelligence power class.

## Approved Boundary

- tool name: `project.ci.summary`;
- risk `read`;
- category `project`;
- normalized resource type: `project_ci`;
- inputs: `workspace_id`, `root`, `max_depth`, `limit`, `include_categories`;
- output: count-only CI posture metadata and allowlisted labels only.

The implementation may summarize provider, workflow/config, trigger-category, job-category,
location-bucket, skipped-count, truncation, limit, and output-policy metadata.

## Required Suppressions

The implementation must preserve:

- no workflow names;
- no raw paths;
- no raw recursive listing;
- no file contents;
- no command/script values;
- no environment names or values;
- no secrets;
- no dependency names;
- no registry/network access;
- no CI execution;
- no command output;
- no shell;
- no package-manager execution;
- no broad filesystem writes;
- no deployment-readiness claims;
- no compliance claims.

## Required Evidence

The runtime lane must include:

- manifest-lock update;
- resource construction parity for `project_ci`;
- policy parity fixtures;
- governed-call audit metadata that is count-only;
- MCP list/call coverage through the governed path;
- focused executor regression tests for denied paths and metadata suppression;
- source-review handoff bundle;
- release/readiness updates.

## Deferred

Broader capability expansion remains blocked. This decision does not approve CI execution, workflow
name disclosure, raw path disclosure, command/script inspection, environment inspection, dependency
inspection, package-manager execution, shell execution, deployment readiness analysis, compliance
automation, or any new powerful tool class.

Run:

```bash
make project-ci-summary-implementation-gate
```
