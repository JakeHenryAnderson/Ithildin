# v3 project.test.summary Implementation Decision

Status: approved_limited_read_only runtime implementation.

This record approves the narrow runtime implementation boundary for `project.test.summary`. It
adds one tool manifest and adds one executor dispatch path through the existing governed read tool
pipeline. runtime behavior is bounded read-only. It adds no policy rule class, no new API endpoint,
no new MCP transport, no approval behavior, no shell, no package-manager execution, no test
execution, no registry/network access, no broad filesystem writes, and no new power class.

## Approved Future Surface

- tool name: `project.test.summary`;
- risk `read`;
- category `project`;
- MCP exposure: read-only through the existing governed pipeline only after runtime implementation;
- inputs: `workspace_id`, `root`, `max_depth`, `limit`, and `include_categories`;
- output: count-only test metadata and allowlisted labels only;
- implementation status: approved for one bounded read-only runtime tool.

## Output Boundary

The tool may return visible test-like directory/file counts, safe framework hint counts, safe
test-location counts, safe language-family counts, skipped count keys, truncation evidence, limit
evidence, and output policy booleans.

It must return no test file names, no raw paths, no raw recursive listing, no raw sensitive paths,
no stable cross-response path identifiers, no file contents, no test case names, no source
snippets, no dependency names, no package names, no package script names or values, no coverage
data, no test pass/fail claims, no command output, no registry URLs, no package-manager
stdout/stderr, no sandbox/SIEM/compliance claims, no package-manager execution, no test execution,
and no network access.

## Runtime Boundary

The implementation uses the existing workspace registry and filesystem path-safety rules. It must
perform no shell, no package-manager execution, no test execution, no registry or network access,
no arbitrary recursive listing disclosure, no symlink traversal, no hardlink ambiguity, no hidden
or sensitive path disclosure, no `.git` internals exposure, no caller-controlled glob or regex
execution, no coverage collection, and no broad filesystem writes.

The implementation specifically preserves no raw paths, no raw recursive listing, no raw file
names, no test file names, and no test names.

## Evidence Required For Runtime Commit

- Manifest remains limited to `risk: read` and category `project`.
- Executor source must be reviewed against the filesystem traversal contract.
- Resource type: `project_tests`.
- Policy parity case: preview/runtime resource construction must match.
- Negative transcripts: traversal, hidden/sensitive path, `.git`, symlink, hardlink, glob/regex,
  broad listing request, file-content request, test-name request, package-manager request, test
  execution request, coverage request, network request, and unknown principal.
- Implementation gate: `make project-test-summary-implementation-gate`.
- Source-review handoff: `make project-test-summary-source-review-bundle` prepares the focused
  source/test/evidence packet before local lane closure.

Broader capability expansion remains blocked.
