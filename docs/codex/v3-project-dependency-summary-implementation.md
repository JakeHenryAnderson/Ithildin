# v3 project.dependency.summary Implementation Decision

Status: approved_limited_read_only bounded read-only runtime implementation.

This record approves and documents the narrow implementation boundary for
`project.dependency.summary`. It adds one tool manifest and one executor dispatch path for local
direct dependency count metadata only.

## Approved Surface

- tool name: `project.dependency.summary`;
- risk `read`;
- category `project`;
- MCP exposure: read-only through the existing governed pipeline;
- inputs: `workspace_id`, `root`, `manifest_kinds`, and `limit`;
- manifest kinds: the same fixed allowlist used by `project.manifest.summary`;
- limit: bounded to 20 root manifest files.

## Output Boundary

The tool may return manifest count, dependency section counts, direct dependency totals, ecosystem
counts, manifest-kind counts, parse status, truncation status, and output-policy booleans.

It must return no file contents, no dependency names, no package names, no package version
constraints, no package script names or values, no lockfile contents, no registry URLs, no
repository URLs, no transitive dependency resolution, and no license, vulnerability, SBOM, or
compliance claims.

## Runtime Boundary

The implementation uses existing workspace path safety and parser helpers. It performs no shell,
no package-manager execution, no registry or network access, no recursive discovery, no arbitrary
manifest filenames, and no broad filesystem writes.

The implementation specifically preserves no arbitrary manifest filenames.

## Evidence

- Manifest: `tool-manifests/project-dependency-summary.yaml`.
- Executor: `FilesystemReadTools.project_dependency_summary`.
- Resource type: `project_dependencies`.
- Policy parity case: `project_dependency_summary_preview_matches_runtime`.
- Implementation gate: `make project-dependency-summary-implementation-gate`.
- Source-review bundle: `make project-dependency-summary-source-review-bundle`.

Broader capability expansion remains blocked.
