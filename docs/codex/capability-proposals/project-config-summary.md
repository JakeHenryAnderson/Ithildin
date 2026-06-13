# Capability Proposal: project.config.summary

Status: design-only proposal. This document does not add a tool manifest, does not add an
executor, does not add policy rules, does not add MCP exposure, does not add API behavior, does not
add UI behavior, and does not add runtime behavior.

Boundary shorthand: count-only config posture metadata and allowlisted labels only.

`project.config.summary` is the next proposed narrow read-only project-intelligence capability
after `project.language.summary`. It would summarize bounded configuration posture from a trusted
workspace without exposing config file names, raw paths, config contents, config values, dependency
names, package names, package script names or values, environment names or values, registry URLs,
command output, or network-derived metadata.

## Intended Behavior

The proposed tool would inspect a trusted workspace root or bounded workspace-relative root using
the existing filesystem safety contract. It would infer broad config posture from allowlisted
filename/category mappings only. It must not parse config values, execute config tools, invoke
package managers, inspect registries, or run shell commands.

Proposed output categories:

- total visible config directory and config-like file counts within configured depth and item
  limits;
- allowlisted config category counts such as `build_config`, `test_config`, `lint_format_config`,
  `runtime_app_config`, `container_deployment_config`, `editor_tooling_config`,
  `ci_workflow_config`, and `unknown_config`;
- allowlisted config location counts such as `root_level`, `config_directory`,
  `source_adjacent_config`, `ci_directory`, `tooling_directory`, and `unknown_location`;
- skipped counts for hidden paths, sensitive paths, `.git`, symlinks, hardlinks, binary or
  unsupported entries, depth limits, item limits, and safe errors;
- truncation, resource-limit, and output-policy evidence.

## Non-Goals

The proposal explicitly preserves:

- no config file names;
- no raw paths;
- no raw recursive listing;
- no stable cross-response path identifiers;
- no file contents;
- no config contents;
- no config values;
- no dependency names;
- no package names;
- no package script names or values;
- no environment names or values;
- no registry URLs;
- no config parser execution;
- no command discovery;
- no command output;
- no package-manager execution;
- no registry or network access;
- no shell;
- no broad filesystem writes, deletes, moves, chmod, or archive extraction;
- no sandbox, SIEM, compliance, SBOM, vulnerability, or deployment-readiness claims.

If a later review concludes raw filenames, raw paths, config contents, config values, package
scripts, dependency names, command execution, package-manager execution, or network-backed metadata
are necessary for usefulness, implementation must stop and a different proposal must be written.

## Proposed Input Shape

A future implementation plan may propose:

- `workspace_id`: optional trusted workspace selector;
- `root`: optional workspace-relative root, subject to existing path-safety rules;
- `max_depth`: bounded integer using a strict configured maximum;
- `limit`: bounded maximum entries to inspect;
- `include_categories`: optional allowlist of safe output categories.

The future schema must use `additionalProperties: false`, reject caller-controlled globs or regexes,
reject absolute paths, reject path traversal, reject URL-encoded path ambiguity, reject control
characters, reject symlink or hardlink traversal, and preserve the existing workspace-root
confinement model.

## Proposed Output Shape

A future output schema may include:

- `tool_name`;
- `workspace_id`;
- `root_label`;
- `summary`: safe counts only;
- `config_category_counts`;
- `config_location_counts`;
- `skipped_counts`;
- `limits`;
- `truncated`;
- `output_policy`.

The output must not include config file names, raw paths, config contents, config values, file
contents, dependency names, package names, script names or values, environment names or values,
registry URLs, raw exception messages, or raw filesystem errors.

## Policy And Audit Evidence

The proposed resource type is `project_config`, with read risk and project category. Runtime and
policy preview must construct the same normalized resource shape before policy evaluation.

Audit evidence must be safe count-only metadata: workspace ID, normalized resource, requested root
label, max depth, limit, config-category keys, config-location keys, skipped count keys, truncation
state, output-policy booleans, policy hash, manifest hash, and request hash. It must not include
raw paths, filenames, file contents, config contents, config values, dependency names, package
names, package scripts, environment names or values, command output, registry URLs, or raw
filesystem errors.

## UI/review evidence

If implemented later, the review console may show compact config-summary counts and
skipped/truncated warnings. It must not render raw paths, filenames, config contents, config
values, file contents, dependency names, package names, package script values, environment names or
values, command output, or deployment claims.

## Negative Transcripts

A later implementation packet must include denial or safe-output transcripts for:

- traversal and absolute paths;
- hidden/sensitive paths and `.git`;
- symlink and hardlink entries;
- control-character and Unicode-normalization path ambiguity;
- binary or unsupported entries;
- oversized/deep directory trees;
- broad recursive listing requests;
- caller-provided globs or regexes;
- attempts to request file names, file contents, config contents, config values, package names,
  dependency names, scripts, environment variables, command execution, or network metadata.

## Resource limits

A future implementation must define hard limits for:

- maximum depth;
- maximum inspected entries;
- maximum output categories;
- maximum output bytes;
- timeout;
- skipped-entry evidence.

The executor must fail closed or return truncated safe counts without leaking raw paths, filenames,
file contents, config contents, config values, command output, or raw sensitive paths.

## Accepted-risk impact

This proposal does not close accepted deferred risks and does not approve public/security-product
positioning. It adds planning pressure to the metadata privacy policy because even count-only
config posture can reveal project purpose, deployment style, or operational maturity. A future
implementation decision must explicitly record that residual local-preview risk.

## No-new-powers analysis

The proposal remains inside the read-only local metadata contract. It does not add shell execution,
Docker socket access, Kubernetes tools, browser automation, arbitrary HTTP, broad filesystem
writes, package-manager execution, registry/network access, remote MCP, production identity,
runtime Postgres, hosted telemetry, plugin SDK work, sandbox orchestration, config parser
execution, or deployment validation.

## Review Requirements

Before implementation, this capability needs:

- implementation-planning packet;
- filesystem traversal and output-category contract;
- policy fixtures and parity evidence;
- audit fields;
- UI/review evidence;
- negative transcripts;
- resource limits;
- accepted-risk impact;
- no-new-powers analysis;
- focused source-review handoff;
- explicit implementation decision.

External/source Review Requirement: a source reviewer must verify that any future implementation is
still count-only, local, read-only, workspace-confined, safe-error-only, and free of shell,
package-manager execution, network access, config parser execution, file contents, config
contents, config values, raw paths, raw filenames, and raw recursive listing exposure before the
lane can close.
