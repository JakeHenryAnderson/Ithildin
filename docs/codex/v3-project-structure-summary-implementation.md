# v3 project.structure.summary Implementation Decision

Status: approved_limited_read_only runtime implementation.

This record approves the narrow runtime implementation boundary for `project.structure.summary`.
It adds one tool manifest and adds one executor dispatch path through the existing governed read
tool pipeline. runtime behavior is bounded read-only. It adds no policy rule class, no new API
endpoint, no new MCP transport, no approval behavior, no shell, no package-manager execution, no
registry/network access, no broad filesystem writes, and no new power class.

## Approved Future Surface

- tool name: `project.structure.summary`;
- risk `read`;
- category `project`;
- MCP exposure: read-only through the existing governed pipeline only after runtime implementation;
- inputs: `workspace_id`, `root`, `max_depth`, `limit`, and `include_categories`;
- output: structural counts and allowlisted labels only;
- implementation status: implemented as one bounded read-only runtime tool.

## Output Boundary

The tool may return total visible directory/file counts, safe directory category counts,
safe file-kind category counts, skipped count keys, truncation evidence, limit evidence, and output
policy booleans.

It must return no file contents, no raw recursive listing, no raw sensitive paths, no raw file
names, no stable cross-response path identifiers, no dependency names, no package names, no package
version constraints, no package script names or values, no lockfile contents, no code search, no
symbol extraction, no registry URLs, no package-manager stdout/stderr, no sandbox/SIEM/compliance
claims, no package-manager execution, and no network access.

## Runtime Boundary

The implementation uses the existing workspace registry and filesystem path-safety
rules. It must perform no shell, no package-manager execution, no registry or network access, no
arbitrary recursive listing disclosure, no symlink traversal, no hardlink ambiguity, no hidden or
sensitive path disclosure, no `.git` internals exposure, no caller-controlled glob or regex
execution, and no broad filesystem writes.

The implementation specifically preserves no raw recursive listing and no raw file names.

## Evidence Required For Runtime Commit

- Manifest remains limited to `risk: read` and category `project`.
- Executor source must be reviewed against the filesystem traversal contract.
- Resource type: `project_structure`.
- Policy parity case: preview/runtime resource construction must match.
- Negative transcripts: traversal, hidden/sensitive path, `.git`, symlink, hardlink, glob/regex,
  broad listing request, file-content request, package-manager request, network request, and
  unknown principal.
- Implementation gate: `make project-structure-summary-implementation-gate`.
- Source-review handoff: `make project-structure-summary-source-review-bundle` prepares the focused
  source/test/evidence packet before local lane closure.

Broader capability expansion remains blocked.
