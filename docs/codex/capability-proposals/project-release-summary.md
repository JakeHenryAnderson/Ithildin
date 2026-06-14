# Capability Proposal: project.release.summary

Status: design-only proposal. This document does not add a tool manifest. This document does not
add an executor. It does not add policy rules, does not add MCP exposure, does not add API
behavior, does not add UI behavior, and does not add runtime behavior.

This proposal does not add a manifest.

`project.release.summary` is a proposed bounded read-only project-intelligence capability. It would
summarize release posture from workspace-local files using count-only release posture metadata and allowlisted labels only.

This proposal does not add a manifest, executor, policy rule, MCP exposure, API behavior, UI runtime behavior, audit behavior, approval behavior, or any runtime implementation.

## Intended Behavior

The future tool would inspect only workspace-confined release-oriented files and return safe
aggregate metadata:

- release artifact and config counts;
- release-note and changelog file counts by coarse category only;
- version-marker counts by coarse source category only;
- release automation and config category counts;
- location buckets, not paths;
- skipped counts;
- truncation and limit metadata;
- output-policy flags.

## Proposed Input Shape

The future input schema should be explicit and closed with `additionalProperties: false`.

```json
{
  "workspace_id": "default",
  "root": ".",
  "max_depth": 4,
  "limit": 100,
  "include_categories": ["artifact", "changelog", "version_marker", "automation", "location"]
}
```

Inputs are design-only until a later implementation gate approves the runtime schema.

## Proposed Output Shape

The future output should be count-only and label-only:

```json
{
  "workspace_id": "default",
  "root_label": "workspace_root",
  "release_artifact_counts": {"release_config": 2, "unknown_release_artifact": 1},
  "changelog_category_counts": {"release_note": 3, "unknown_changelog": 1},
  "version_marker_counts": {"source_version_marker": 2, "unknown_version_marker": 1},
  "automation_category_counts": {"release_automation": 2, "release_config": 1},
  "location_buckets": {"release_directory": 2, "source_adjacent": 1},
  "skipped": {"hidden_or_sensitive": 0, "symlink": 0, "depth_limit": 0},
  "limits": {"max_depth": 4, "limit": 100, "truncated": false},
  "output_policy": {
    "raw_paths": false,
    "release_names": false,
    "version_strings": false,
    "file_contents": false,
    "command_values": false
  }
}
```

Output must be structured metadata only. It must include no release names, no release version strings when they reveal product/customer cadence, no changelog contents, no tag names, no branch names, no package names, no dependency names, no author or maintainer names, no raw paths, no file contents, no shell output, no Git output, no package-manager output, no CI output, no registry or network access, and no deployment-readiness, legal, or compliance claims.

## Policy And Audit Evidence

The future resource type is `project_release`. Policy preview and runtime execution must
construct the same normalized resource before any implementation is accepted.

Audit metadata must stay count-only and secret-free. It may include release artifact counts,
category counts, skip counts, truncation state, selected categories, `workspace_id`, resource type,
policy hash, manifest hash, and output-policy flags. It must not include release names, version
strings, changelog contents, tag names, branch names, package names, dependency names,
author/maintainer names, raw paths, file contents, or command output.

## UI/Review Evidence

Any future UI display should present aggregate release posture only. Review surfaces should show
the selected workspace, safe category labels, counts, skip reasons, truncation state, and
output-policy flags.

UI/review surfaces must not present this as release readiness, shipping readiness, compliance
status, production quality, or security assurance.

## Negative Transcripts

Future negative transcripts must cover:

- traversal or absolute root attempts;
- hidden/sensitive path denial;
- `.git` denial;
- symlink and hardlink denial;
- malformed or oversized input denial;
- depth and item-limit truncation;
- release artifacts that contain names, tag-like text, or changelog contents that are not emitted;
- unsupported shapes returning safe unknown labels;
- unauthorized principal denial.

## Resource Limits

Future implementation must define bounded defaults for `max_depth`, `limit`, file size,
candidate-file count, parse/inspection budget, and output size. It must fail closed or truncate
safely without returning raw paths, file contents, release names, version strings, changelog text,
tag names, branch names, package names, dependency names, or raw parser exceptions.

## Accepted-Risk Impact

This proposal does not change the accepted-risk register because it is design-only. If later
implemented, the capability should be evaluated as the existing bounded read-only metadata power
class, not as shipping-readiness analysis, compliance automation, Git execution, shell access, or
CI execution.

## No-New-Powers Analysis

The proposed capability remains within the existing project metadata family if it only reads local
workspace files through the same confined traversal pattern and returns count-only labels. It must
not run Git commands, execute shell commands, contact registries, fetch remote data, evaluate
package managers, execute CI, expose release names, or surface changelog contents.

## External/source Review Requirement

Implementation remains blocked until a later implementation-boundary sprint adds a source-review
handoff. External/source review must confirm that the future implementation is local-only,
count-only, closed-schema, policy-parity covered, audit-safe, and free of release names, version
strings that reveal cadence, changelog contents, tag names, branch names, raw paths, file
contents, package names, dependency names, shell execution, Git execution, package-manager
execution, CI execution, registry access, and network access.

Strict non-goals: no release names, no release version strings when they reveal product/customer cadence, no changelog contents, no tag names, no branch names, no package names, no dependency names, no author or maintainer names, no raw paths, no file contents, no shell, no Git execution, no package-manager execution, no CI execution, no registry or network access, no deployment-readiness claims, no legal claims, no compliance claims, and no broad recursive listings.
