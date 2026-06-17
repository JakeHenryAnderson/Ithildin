# Project Risk Summary Capability Proposal

Status: design-only proposal.

`project.risk.summary` is a proposed bounded read-only project-intelligence capability. It would
summarize risk-signal posture from workspace-local files using count-only risk signal metadata and
allowlisted labels only.

This proposal does not add a manifest, executor, policy rule, MCP exposure, API behavior,
UI runtime behavior, audit behavior, approval behavior, or any runtime implementation.

Stable boundary phrases: count-only risk signal metadata and allowlisted labels only; no filenames;
no raw paths; no file contents; no dependency names; no package names; no CVE IDs; no secret
values; no secret names; no environment names or values; no command/script values; no registry
URLs; no vulnerability findings; no scanner execution; no package-manager execution; no registry or
network access; no shell; no compliance claims; no security assurance; no broad recursive listings.

## Intended Behavior

The future tool would inspect only workspace-confined metadata signals and return safe aggregate
metadata:

- risk area counts such as `secrets_adjacent`, `identity_metadata`, `network_config_label`,
  `deployment_label`, `release_label`, `dependency_label`, `test_gap_label`, `docs_gap_label`,
  `ci_gap_label`, and `unknown_signal`;
- signal-source category counts such as `manifest_signal`, `config_signal`, `ci_signal`,
  `release_signal`, `docs_signal`, `test_signal`, `filesystem_signal`, and `unknown_source`;
- location buckets such as `root_level`, `config_directory`, `ci_directory`, `docs_directory`,
  `source_adjacent`, and `unknown_location`;
- skipped counts for hidden/sensitive paths, `.git`, symlink, hardlink, unsupported type, depth
  limit, item limit, malformed metadata, and safe errors;
- truncation, limit, and output-policy metadata.

The future tool would not make vulnerability findings. It would only report bounded local
risk-signal counts that can help an operator decide where human review might be useful.

## Proposed Input Shape

The future input schema should be explicit and closed with `additionalProperties: false`.

```json
{
  "workspace_id": "default",
  "root": ".",
  "max_depth": 4,
  "limit": 100,
  "include_categories": ["risk_area", "source", "location", "skip"]
}
```

Inputs are design-only until a later implementation gate approves the runtime schema.

## Proposed Output Shape

The future output should be count-only and label-only:

```json
{
  "workspace_id": "default",
  "root_label": "workspace_root",
  "risk_areas": {"secrets_adjacent": 1, "ci_gap_label": 1},
  "signal_sources": {"config_signal": 1, "ci_signal": 1},
  "location_buckets": {"root_level": 1, "config_directory": 1},
  "skipped": {"hidden_or_sensitive": 0, "symlink": 0, "depth_limit": 0},
  "limits": {"max_depth": 4, "limit": 100, "truncated": false},
  "output_policy": {
    "raw_paths": false,
    "file_contents": false,
    "dependency_names": false,
    "secret_values": false,
    "vulnerability_findings": false,
    "compliance_claims": false
  }
}
```

## Policy And Audit Evidence

The future resource type is `project_risk`. Policy preview and runtime execution must construct the
same normalized resource before any implementation is accepted.

Audit metadata must stay count-only and secret-free. It may include safe category counts, skip
counts, truncation state, selected categories, `workspace_id`, resource type, policy hash, manifest
hash, and output-policy flags. It must not include filenames, raw paths, file contents, dependency
names, package names, CVE IDs, secret names, secret values, environment names or values,
command/script values, registry URLs, raw parser errors, scanner output, vulnerability findings, or
compliance conclusions.

## UI/Review Evidence

Any future UI display should present aggregate risk-signal posture only. Review surfaces should show
the selected workspace, safe category labels, counts, skip reasons, truncation state, and
output-policy flags.

UI/review surfaces must not present this as vulnerability scanning, compliance status, production
security assurance, or a replacement for human review.

## Negative Transcripts

Future negative transcripts must cover:

- traversal or absolute root attempts;
- hidden/sensitive path denial;
- `.git` denial;
- symlink and hardlink denial;
- malformed/oversized input denial;
- depth and item-limit truncation;
- files containing dependency names, package names, CVE-like strings, secret-like strings,
  command/script/env-like values, or registry URLs that are not emitted;
- unsupported signal shapes returning safe unknown labels;
- unauthorized principal denial.

## Resource Limits

Future implementation must define bounded defaults for `max_depth`, `limit`, file size,
candidate-file count, parse/inspection budget, and output size. It must fail closed or truncate
safely without returning filenames, raw paths, file contents, dependency names, package names, CVE
IDs, secret names/values, command values, environment values, raw parser exceptions, scanner output,
or filesystem errors.

## Accepted-risk impact

This proposal does not change the accepted-risk register because it is design-only. If later
implemented, the capability should be evaluated as the existing bounded read-only metadata power
class, not as vulnerability scanning, dependency analysis, compliance automation, shell access,
network access, or security assurance.

## No-new-powers analysis

The proposed capability remains within the existing project metadata family if it only reads local
workspace files through the same confined traversal pattern and returns count-only labels. It must
not run scanners, execute shell commands, contact registries, fetch remote vulnerability data,
evaluate secrets, parse dependency names for output, or expose raw sensitive details.

## External/source Review Requirement

Implementation remains blocked until a later implementation-boundary sprint adds a source-review
handoff. External/source review must confirm that the future implementation is local-only,
count-only, closed-schema, policy-parity covered, audit-safe, and free of filenames, raw paths,
file contents, dependency names, package names, CVE IDs, secret names/values, command values,
environment names/values, registry URLs, vulnerability findings, scanner execution, and compliance
claims.

Strict non-goals: no filenames, no raw paths, no file contents, no dependency names, no package
names, no CVE IDs, no secret values, no secret names, no environment names or values, no
command/script values, no registry URLs, no vulnerability findings, no scanner execution, no
package-manager execution, no registry or network access, no shell, no compliance claims, no
security assurance, and no broad recursive listings.
