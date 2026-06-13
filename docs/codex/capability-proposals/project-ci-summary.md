# Project CI Summary Capability Proposal

Status: design-only proposal.

`project.ci.summary` is a proposed bounded read-only project-intelligence capability. It would summarize CI posture from workspace-local files using count-only CI posture metadata and allowlisted labels only.

This proposal does not add a manifest, executor, policy rule, MCP exposure, API behavior, UI runtime behavior, audit behavior, approval behavior, or any runtime implementation.

## Intended Behavior

The future tool would inspect only workspace-confined CI configuration locations and return safe aggregate metadata:

- provider labels such as `github_actions`, `gitlab_ci`, `circleci`, `azure_pipelines`, `buildkite`, `jenkins`, `travis`, and `unknown_ci`;
- workflow/config counts;
- trigger-category counts such as `push`, `pull_request`, `schedule`, `manual`, `release`, `tag`, and `unknown_trigger`;
- job-category counts such as `build`, `test`, `lint`, `security_scan_label`, `deploy_label`, `release_label`, and `unknown_job`;
- location buckets such as `root_level`, `ci_directory`, `github_workflows`, `config_directory`, `source_adjacent`, and `unknown_location`;
- skipped counts for hidden/sensitive paths, `.git`, symlink, hardlink, unsupported type, depth limit, item limit, malformed config, and safe errors;
- truncation, limit, and output-policy metadata.

## Proposed Input Shape

The future input schema should be explicit and closed with `additionalProperties: false`.

```json
{
  "workspace_id": "default",
  "root": ".",
  "max_depth": 4,
  "limit": 100,
  "include_categories": ["provider", "trigger", "job", "location"]
}
```

Inputs are design-only until a later implementation gate approves the runtime schema.

## Proposed Output Shape

The future output should be count-only and label-only:

```json
{
  "workspace_id": "default",
  "root_label": "workspace_root",
  "providers": {"github_actions": 2, "unknown_ci": 1},
  "workflow_count": 3,
  "trigger_categories": {"push": 2, "manual": 1},
  "job_categories": {"build": 1, "test": 2, "unknown_job": 1},
  "location_buckets": {"github_workflows": 2, "root_level": 1},
  "skipped": {"hidden_or_sensitive": 0, "symlink": 0, "depth_limit": 0},
  "limits": {"max_depth": 4, "limit": 100, "truncated": false},
  "output_policy": {
    "raw_paths": false,
    "workflow_names": false,
    "file_contents": false,
    "command_values": false,
    "environment_values": false
  }
}
```

## Policy And Audit Evidence

The future resource type is `project_ci`. Policy preview and runtime execution must construct the same normalized resource before any implementation is accepted.

Audit metadata must stay count-only and secret-free. It may include provider/category counts, skip counts, truncation state, selected categories, `workspace_id`, resource type, policy hash, manifest hash, and output-policy flags. It must not include raw workflow names, paths, file contents, command/script values, environment names or values, dependency names, registry URLs, raw parser errors, or CI output.

## UI/Review Evidence

Any future UI display should present aggregate CI posture only. Review surfaces should show the selected workspace, safe category labels, counts, skip reasons, truncation state, and output-policy flags.

UI/review surfaces must not present this as deployment readiness, compliance status, CI correctness, or security assurance.

## Negative Transcripts

Future negative transcripts must cover:

- traversal or absolute root attempts;
- hidden/sensitive path denial;
- `.git` denial;
- symlink and hardlink denial;
- malformed/oversized input denial;
- depth and item-limit truncation;
- config files with command/script/env-like values that are not emitted;
- unsupported provider/config shapes returning safe unknown labels;
- unauthorized principal denial.

## Resource Limits

Future implementation must define bounded defaults for `max_depth`, `limit`, file size, candidate-file count, parse/inspection budget, and output size. It must fail closed or truncate safely without returning raw paths, config contents, command values, environment names/values, or raw parser exceptions.

## Accepted-Risk Impact

This proposal does not change the accepted-risk register because it is design-only. If later implemented, the capability should be evaluated as the existing bounded read-only metadata power class, not as CI execution, deployment analysis, compliance automation, or shell access.

## No-New-Powers Analysis

The proposed capability remains within the existing project metadata family if it only reads local workspace files through the same confined traversal pattern and returns count-only labels. It must not run CI, execute shell commands, contact registries, fetch remote configuration, evaluate secrets, parse dependency names, or expose raw automation details.

## External/source Review Requirement

Implementation remains blocked until a later implementation-boundary sprint adds a source-review handoff. External/source review must confirm that the future implementation is local-only, count-only, closed-schema, policy-parity covered, audit-safe, and free of workflow names, raw paths, command values, environment names/values, secrets, file contents, and CI execution.

Strict non-goals: no workflow names, no raw paths, no file contents, no command/script values, no environment names or values, no secrets, no dependency names, no registry or network access, no CI execution, no shell, no deployment-readiness claims, no compliance claims, or no broad recursive listings.
