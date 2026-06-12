# v3 project.docs.summary Source Review Handoff

Status: source-review handoff prepared. This document records the focused review lane for the
bounded read-only `project.docs.summary` implementation.

## Review Question

Can the `project.docs.summary` lane close for continued local-preview development as one
count-only, workspace-confined, read-only project documentation-layout metadata capability?

## Review Focus

- Manifest remains `risk: read`, category `project`, and MCP read-only through the governed
  pipeline.
- Inputs remain limited to `workspace_id`, `root`, `max_depth`, `limit`, and
  `include_categories`.
- Runtime output contains documentation-layout counts, allowlisted documentation type/location and
  language labels, skipped counts, truncation, limits, root labels, and output-policy booleans
  only.
- Runtime output and audit metadata contain no file contents, raw recursive listing, raw paths,
  raw file names, documentation file names, documentation headings, documentation bodies, coverage
  data, dependency names, package names, package script values, command output, package-manager
  output, raw filesystem errors, registry URLs, network data, or documentation build results.
- Preview/runtime policy parity uses resource type `project_docs`.
- Source-review findings should use namespace `EXT-PDS-###`.

## Command

```bash
make project-docs-summary-source-review-bundle
```

Broader capability expansion remains blocked.
