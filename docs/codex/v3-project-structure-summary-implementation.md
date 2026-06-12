# v3 project.structure.summary Implementation Decision

Status: approved_limited_read_only future implementation. Runtime implementation is not present in
this sprint.

Runtime implementation is not present in this sprint.

This record approves the narrow future implementation boundary for `project.structure.summary`. It
does not add a tool manifest, does not add an executor, does not add policy rules, does not add MCP
exposure, does not add API behavior, does not add UI behavior, and does not add runtime behavior in
this sprint. A later implementation sprint may add exactly one bounded read-only tool manifest and
one executor dispatch path if it preserves this decision record.

## Approved Future Surface

- tool name: `project.structure.summary`;
- risk `read`;
- category `project`;
- MCP exposure: read-only through the existing governed pipeline only after runtime implementation;
- inputs: `workspace_id`, `root`, `max_depth`, `limit`, and `include_categories`;
- output: structural counts and allowlisted labels only;
- implementation status: approved for a later bounded runtime sprint, not implemented here.

## Output Boundary

The future tool may return total visible directory/file counts, safe directory category counts,
safe file-kind category counts, skipped count keys, truncation evidence, limit evidence, and output
policy booleans.

It must return no file contents, no raw recursive listing, no raw sensitive paths, no raw file
names, no stable cross-response path identifiers, no dependency names, no package names, no package
version constraints, no package script names or values, no lockfile contents, no code search, no
symbol extraction, no registry URLs, no package-manager stdout/stderr, no sandbox/SIEM/compliance
claims, no package-manager execution, and no network access.

## Runtime Boundary

The future implementation must use the existing workspace registry and filesystem path-safety
rules. It must perform no shell, no package-manager execution, no registry or network access, no
arbitrary recursive listing disclosure, no symlink traversal, no hardlink ambiguity, no hidden or
sensitive path disclosure, no `.git` internals exposure, no caller-controlled glob or regex
execution, and no broad filesystem writes.

The implementation specifically preserves no raw recursive listing and no raw file names.

## Evidence Required Before Runtime Commit

- Manifest sketch remains limited to `risk: read` and category `project`.
- Executor source must be reviewed against the filesystem traversal contract.
- Resource type: `project_structure`.
- Policy parity case: future preview/runtime resource construction must match.
- Negative transcripts: traversal, hidden/sensitive path, `.git`, symlink, hardlink, glob/regex,
  broad listing request, file-content request, package-manager request, network request, and
  unknown principal.
- Implementation gate: `make project-structure-summary-implementation-gate`.
- Source-review handoff: a later `project-structure-summary-source-review-bundle` or equivalent
  focused source/test/evidence packet before local lane closure.

Broader capability expansion remains blocked.
