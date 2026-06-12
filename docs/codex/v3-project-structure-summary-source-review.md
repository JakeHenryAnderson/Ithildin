# v3 project.structure.summary Source Review Handoff

Status: source-review handoff prepared. This document records the focused review lane for the
bounded read-only `project.structure.summary` implementation.

## Review Question

Can the `project.structure.summary` lane close for continued local-preview development as one
count-only, workspace-confined, read-only project metadata capability?

## Review Focus

- Manifest remains `risk: read`, category `project`, and MCP read-only through the governed
  pipeline.
- Inputs remain limited to `workspace_id`, `root`, `max_depth`, `limit`, and `include_categories`.
- Runtime output contains structural counts, allowlisted labels, skipped counts, truncation,
  limits, and output-policy booleans only.
- Runtime output and audit metadata contain no file contents, raw recursive listing, raw file
  names, raw sensitive paths, stable path IDs, dependency names, package names, package script
  values, package-manager output, registry URLs, raw filesystem errors, or network data.
- Preview/runtime policy parity uses resource type `project_structure`.
- Source-review findings should use namespace `EXT-PSS-###`.

## Command

```bash
make project-structure-summary-source-review-bundle
```

Broader capability expansion remains blocked.
