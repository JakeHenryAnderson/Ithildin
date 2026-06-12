# v3 project.test.summary Source Review Handoff

Status: source-review handoff prepared. This document records the focused review lane for the
bounded read-only `project.test.summary` implementation.

## Review Question

Can the `project.test.summary` lane close for continued local-preview development as one count-only,
workspace-confined, read-only project test-layout metadata capability?

## Review Focus

- Manifest remains `risk: read`, category `project`, and MCP read-only through the governed
  pipeline.
- Inputs remain limited to `workspace_id`, `root`, `max_depth`, `limit`, and
  `include_categories`.
- Runtime output contains test-layout counts, allowlisted framework/location/language labels,
  skipped counts, truncation, limits, root labels, and output-policy booleans only.
- Runtime output and audit metadata contain no file contents, raw recursive listing, raw paths,
  raw file names, test file names, test case names, coverage data, dependency names, package names,
  package script values, command output, package-manager output, raw filesystem errors, registry
  URLs, network data, or test execution results.
- Preview/runtime policy parity uses resource type `project_tests`.
- Source-review findings should use namespace `EXT-PTS-###`.

## Command

```bash
make project-test-summary-source-review-bundle
```

Broader capability expansion remains blocked.
