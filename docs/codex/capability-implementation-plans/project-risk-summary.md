# Project Risk Summary Implementation Plan

Status: implementation-planning only.

Implementation state: blocked. This plan does not add a manifest, executor, policy rule, API/MCP
behavior, UI runtime behavior, audit behavior, approval behavior, or governed tool power.

Stable boundary phrases: no filenames; no raw paths; no file contents; no dependency names; no
package names; no CVE IDs; no secret values; no secret names; no environment names or values; no
command/script values; no registry URLs; no vulnerability findings; no scanner execution; no
package-manager execution; no registry or network access; no shell; no compliance claims; no
security assurance; no broad recursive listings.

`project.risk.summary` may only move to runtime implementation after a separate
implementation-boundary decision confirms the proposed contract, policy/resource parity, audit
evidence, negative transcripts, and source-review handoff.

## Future Manifest Sketch

If approved later, the manifest would define:

- name: `project.risk.summary`;
- risk: `read`;
- category: `project`;
- MCP exposure: read-only, governed path only;
- input schema: closed object with `workspace_id`, `root`, `max_depth`, `limit`, and optional safe
  category filters;
- output schema: count-only risk-signal labels, skipped counts, limit metadata, and output-policy
  flags.

No manifest is added in this planning sprint.

## Proposed Input Contract

Future inputs should be bounded:

- `workspace_id`: known enabled workspace;
- `root`: relative path only, default `.`;
- `max_depth`: small bounded integer;
- `limit`: small bounded integer;
- `include_categories`: optional allowlist of safe aggregate sections such as `risk_area`,
  `source`, `location`, and `skip`.

The schema must use `additionalProperties: false` and reject malformed, oversized, traversal,
absolute, encoded-ambiguous, hidden/sensitive, symlink, and hardlink inputs through the same
workspace-confined project metadata patterns.

## Proposed Output Contract

The future output must contain only safe counts and allowlisted labels:

- risk area counts;
- signal-source counts;
- location-bucket counts;
- skipped counts;
- limits/truncation metadata;
- output-policy flags.

It must not include filenames, raw paths, file contents, dependency names, package names, CVE IDs,
secret names, secret values, environment names or values, command/script values, registry URLs,
raw filesystem errors, raw parser errors, scanner output, vulnerability findings, severity scores,
or compliance conclusions.

## Filesystem Traversal Contract

Future traversal must stay workspace-confined and use the existing project metadata safety posture:

- relative roots only;
- no broad recursive listing output;
- deny `.git`, hidden/sensitive paths, symlinks, hardlinks, unsupported file types, binary/NUL
  content, oversized files, and unsupported encodings;
- respect `max_depth`, `limit`, and output-size caps;
- inspect only bounded local metadata signals through allowlisted location/category patterns;
- never execute files, package managers, scanners, Git, CI tools, shell commands, or network
  requests.

## Risk Signal And Category Allowlist

Risk area labels should be coarse and non-sensitive:

- `secrets_adjacent`;
- `identity_metadata`;
- `network_config_label`;
- `deployment_label`;
- `release_label`;
- `dependency_label`;
- `test_gap_label`;
- `docs_gap_label`;
- `ci_gap_label`;
- `unknown_signal`.

Source and location labels should be coarse and non-sensitive:

- signal sources: `manifest_signal`, `config_signal`, `ci_signal`, `release_signal`,
  `docs_signal`, `test_signal`, `filesystem_signal`, `unknown_source`;
- location buckets: `root_level`, `config_directory`, `ci_directory`, `docs_directory`,
  `source_adjacent`, `unknown_location`.

Any future structural parsing must avoid filenames, raw paths, dependency names, package names, CVE
IDs, secret names/values, command values, environment names/values, registry URLs, vulnerability
findings, scanner output, and raw path emission.

## Policy Fixture Plan

Policy fixtures must prove:

- read-capable principals can preview/call `project.risk.summary` on an in-scope workspace;
- unknown/disabled principals are denied safely;
- out-of-scope resources are denied safely;
- policy preview and runtime construct matching `project_risk` resources;
- dangerous/destructive/default-deny policy behavior remains unchanged.

## Audit Evidence Plan

Audit metadata must be count-only and include only:

- tool name;
- resource type `project_risk`;
- workspace ID;
- selected root label, not raw path;
- selected categories;
- risk/source/location counts;
- skipped counts;
- truncation state;
- limit metadata;
- output-policy flags;
- policy/manifest evidence already required by the governed path.

No filenames, raw paths, file contents, dependency names, package names, CVE IDs, secret names,
secret values, environment names or values, command/script values, registry URLs, raw parser errors,
scanner output, vulnerability findings, severity scores, or compliance conclusions may enter audit
metadata.

## UI And Policy Preview Plan

Policy preview must show `project_risk` as the normalized resource and must match runtime resource
construction.

Any future UI should show aggregate risk-signal posture only: counts, labels, skipped reasons,
truncation state, and output-policy flags. It must not claim vulnerability status, compliance
status, production security assurance, deployment readiness, or automated risk remediation.

## Negative Transcript Plan

Future source-review handoff must include negative transcripts for:

- traversal and absolute root denial;
- hidden/sensitive and `.git` denial;
- symlink/hardlink denial;
- malformed/oversized input denial;
- depth/item limit truncation;
- unsupported signal shapes returning safe unknown labels;
- files with dependency names, package names, CVE-like strings, secret-like strings, command values,
  environment values, or registry URLs not emitted;
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

Limit failures and truncation must be safe and must not leak filenames, raw paths, file contents,
dependency names, package names, CVE IDs, secret names/values, command values, environment values,
parser stack traces, scanner output, or filesystem errors.

## Source Review And Implementation Decision Requirement

Actual implementation remains blocked. A future implementation-boundary sprint must add an
implementation decision document, update the manifest lock, implement tests, update policy parity
fixtures, produce negative transcripts, generate a source-review bundle, and pass release/readiness
gates before the tool can be considered for local-preview runtime use.

The future implementation must preserve the strict non-goals: no filenames, no raw paths, no file
contents, no dependency names, no package names, no CVE IDs, no secret values, no secret names, no
environment names or values, no command/script values, no registry URLs, no vulnerability findings,
no scanner execution, no package-manager execution, no registry or network access, no shell, no
compliance claims, no security assurance, and no broad recursive listings.
