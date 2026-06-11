# v3 project.dependency.summary Selection

Status: design-only candidate selection. This document records `project.dependency.summary` as the
next proposed read-only metadata candidate after the implemented `project.manifest.summary` lane.

The selection does not add a manifest, does not add an executor, does not add policy rules, does
not add MCP exposure, does not add API behavior, does not add UI behavior, and does not add runtime
behavior. It explicitly does not add MCP exposure and does not add runtime behavior.

## Selection Rationale

`project.dependency.summary` is the lowest-risk useful continuation of the project metadata family:
it reuses the manifest-selection boundary while narrowing output to aggregate dependency counts. It
is deliberately not dependency inspection, SBOM generation, vulnerability scanning, license review,
package-manager execution, or network-backed registry analysis.

## Boundary

- Tool count remains `13`.
- Implementation remains blocked.
- Broader capability expansion remains blocked.
- New powerful tool classes remain blocked.
- The candidate is count-only and local-preview scoped.
- The future proposal must preserve no file contents, no package script values, no dependency names,
  no registry or network access, and no shell.
- A future implementation requires an explicit implementation decision.

## Required Gates

Run:

```bash
make project-dependency-summary-proposal-check
make project-dependency-summary-implementation-plan-check
make project-dependency-summary-design-review-packet
```

The packet asks for design review only. A later implementation sprint would still need an explicit
implementation decision, source-review handoff, policy fixtures, negative transcripts, audit
evidence, and release gates.
