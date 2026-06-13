# Project CI Summary Implementation Plan

Status: implementation-planning only.

Implementation state: blocked. This plan does not add a manifest, executor, policy rule, API/MCP behavior, UI runtime behavior, audit behavior, approval behavior, or governed tool power.

`project.ci.summary` may only move to runtime implementation after a separate implementation-boundary decision confirms the proposed contract, policy/resource parity, audit evidence, negative transcripts, and source-review handoff.

## Future Manifest Sketch

If approved later, the manifest would define:

- name: `project.ci.summary`;
- risk: `read`;
- category: `project`;
- MCP exposure: read-only, governed path only;
- input schema: closed object with `workspace_id`, `root`, `max_depth`, `limit`, and optional safe category filters;
- output schema: count-only CI posture labels, skipped counts, limit metadata, and output-policy flags.

No manifest is added in this planning sprint.

## Proposed Input Contract

Future inputs should be bounded:

- `workspace_id`: known enabled workspace;
- `root`: relative path only, default `.`;
- `max_depth`: small bounded integer;
- `limit`: small bounded integer;
- `include_categories`: optional allowlist of safe aggregate sections such as `provider`, `trigger`, `job`, and `location`.

The schema must use `additionalProperties: false` and reject malformed, oversized, traversal, absolute, encoded-ambiguous, hidden/sensitive, symlink, and hardlink inputs through the same workspace-confined project metadata patterns.

## Proposed Output Contract

The future output must contain only safe counts and allowlisted labels:

- provider counts;
- workflow/config count;
- trigger-category counts;
- job-category counts;
- location-bucket counts;
- skipped counts;
- limits/truncation metadata;
- output-policy flags.

It must not include workflow names, raw paths, file contents, command/script values, environment names or values, secrets, dependency names, registry URLs, raw filesystem errors, raw parser errors, or CI output.

## Filesystem Traversal Contract

Future traversal must stay workspace-confined and use the existing project metadata safety posture:

- relative roots only;
- no broad recursive listing output;
- deny `.git`, hidden/sensitive paths, symlinks, hardlinks, unsupported file types, binary/NUL content, oversized files, and unsupported encodings;
- respect `max_depth`, `limit`, and output-size caps;
- inspect only candidate CI config files and directories by allowlisted location/name patterns;
- never execute files, package managers, CI tools, shell commands, or network requests.

## Provider And Category Allowlist

Provider labels should be coarse and non-sensitive:

- `github_actions`;
- `gitlab_ci`;
- `circleci`;
- `azure_pipelines`;
- `buildkite`;
- `jenkins`;
- `travis`;
- `unknown_ci`.

Category labels should be coarse and non-sensitive:

- trigger categories: `push`, `pull_request`, `schedule`, `manual`, `release`, `tag`, `unknown_trigger`;
- job categories: `build`, `test`, `lint`, `security_scan_label`, `deploy_label`, `release_label`, `unknown_job`;
- location buckets: `root_level`, `ci_directory`, `github_workflows`, `config_directory`, `source_adjacent`, `unknown_location`.

Any future structural parsing must avoid command/script values, environment names or values, secrets, dependency names, registry URLs, workflow names, and raw path emission.

## Policy Fixture Plan

Policy fixtures must prove:

- read-capable principals can preview/call `project.ci.summary` on an in-scope workspace;
- unknown/disabled principals are denied safely;
- out-of-scope resources are denied safely;
- policy preview and runtime construct matching `project_ci` resources;
- dangerous/destructive/default-deny policy behavior remains unchanged.

## Audit Evidence Plan

Audit metadata must be count-only and include only:

- tool name;
- resource type `project_ci`;
- workspace ID;
- selected root label, not raw path;
- selected categories;
- provider/category counts;
- skipped counts;
- truncation state;
- limit metadata;
- output-policy flags;
- policy/manifest evidence already required by the governed path.

No file contents, raw paths, workflow names, command/script values, environment names or values, secrets, dependency names, registry URLs, raw parser errors, or CI output may enter audit metadata.

## UI And Policy Preview Plan

Policy preview must show `project_ci` as the normalized resource and must match runtime resource construction.

Any future UI should show aggregate CI posture only: counts, labels, skipped reasons, truncation state, and output-policy flags. It must not claim deployment readiness, CI correctness, compliance status, production assurance, or security posture beyond local-preview metadata.

## Negative Transcript Plan

Future source-review handoff must include negative transcripts for:

- traversal and absolute root denial;
- hidden/sensitive and `.git` denial;
- symlink/hardlink denial;
- malformed/oversized input denial;
- depth/item limit truncation;
- unsupported provider/config shape returning safe unknown labels;
- config command/script/env-like values not emitted;
- unauthorized principal denial;
- MCP governed-path denial for unauthorized callers.

## Resource Limits

Future implementation must set explicit bounds for:

- maximum depth;
- maximum candidate files;
- maximum inspected bytes per candidate;
- maximum output sections;
- maximum output bytes;
- timeout or inspection budget where applicable.

Limit failures and truncation must be safe and must not leak raw paths, file contents, command values, environment values, parser stack traces, or filesystem errors.

## Source Review And Implementation Decision Requirement

Actual implementation remains blocked. A future implementation-boundary sprint must add an implementation decision document, update the manifest lock, implement tests, update policy parity fixtures, produce negative transcripts, generate a source-review bundle, and pass release/readiness gates before the tool can be considered for local-preview runtime use.

The future implementation must preserve the strict non-goals: no workflow names, no raw paths, no file contents, no command/script values, no environment names or values, no secrets, no dependency names, no registry or network access, no CI execution, no shell, no deployment-readiness claims, no compliance claims, or no broad recursive listings.
