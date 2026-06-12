# v3 project.language.summary Source Review Handoff

Status: source-review handoff prepared. This document records the focused review lane for the
bounded read-only `project.language.summary` implementation.

## Review Question

Can the `project.language.summary` lane close for continued local-preview development as one
count-only, workspace-confined, read-only project language-family metadata capability?

## Review Focus

- Manifest remains `risk: read`, category `project`, and MCP read-only through the governed
  pipeline.
- Inputs remain limited to `workspace_id`, `root`, `max_depth`, `limit`, and
  `include_categories`.
- Runtime output contains source-like file and directory counts, allowlisted language-family,
  extension-family, and source-location labels, skipped counts, truncation, limits, root labels,
  and output-policy booleans only.
- Runtime output and audit metadata contain no file contents, raw recursive listing, raw paths,
  raw file names, language file names, raw extensions, source snippets, coverage data, dependency
  names, package names, package script values, command discovery, command output, package-manager
  output, raw filesystem errors, registry URLs, network data, language detector results, or
  language detector execution.
- Preview/runtime policy parity uses resource type `project_language`.
- Source-review findings should use namespace `EXT-PLS-###`.

## Command

```bash
make project-language-summary-source-review-bundle
```

Broader capability expansion remains blocked.
