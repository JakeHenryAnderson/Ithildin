# v3 project.docs.summary Selection

Status: design-only candidate selection. This document does not add a tool manifest, executor,
policy rule, MCP exposure, API behavior, UI behavior, or runtime behavior.

`project.docs.summary` is selected as the next bounded read-only project-intelligence candidate.
It is selected for proposal review only; implementation remains blocked.

Implementation remains blocked until a later implementation-planning packet and explicit
implementation decision exist.

tool count remains `16`.

## Rationale

The current read-only project-intelligence slice can describe commits, refs, manifests,
dependencies, and coarse structure. A bounded documentation-summary capability would help an agent orient to
whether a workspace appears to contain documentation and which broad docs categories are present without
executing documentation, exposing filenames, reading documentation bodies, discovering package scripts, contacting
registries, or running package managers.

## Boundary

The selected candidate may propose count-only metadata and allowlisted documentation-category labels. It
must not propose runtime behavior that exposes raw paths, raw filenames, file contents,
documentation headings, dependency names, package names, script names or values, coverage data,
pass/fail status,
shell output, package-manager output, registry/network data, or broad filesystem behavior.

## Gate

Run:

```bash
make project-docs-summary-proposal-check
make project-docs-summary-design-review-packet
make next-capability-readiness
```

These commands validate design-only selection and packet readiness. They do not approve
implementation.
