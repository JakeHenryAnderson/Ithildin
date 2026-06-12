# v3 project.language.summary Selection

Status: design-only candidate selection. This document does not add a tool manifest, executor,
policy rule, MCP exposure, API behavior, UI behavior, or runtime behavior.

`project.language.summary` is selected as the next bounded read-only project-intelligence candidate.
It is selected for proposal review only; implementation remains blocked.

Implementation remains blocked until a later implementation-planning packet and explicit
implementation decision exist.

tool count remains `17`.

## Rationale

The current read-only project-intelligence slice can describe commits, refs, manifests,
dependencies, coarse structure, tests, and documentation layout. A bounded language-summary
capability would help an agent orient to the broad implementation mix in a workspace without
executing language detectors, exposing filenames, exposing raw extensions, reading source files,
discovering package scripts, contacting registries, or running package managers.

## Boundary

The selected candidate may propose count-only metadata and allowlisted language-family labels. It
must not propose runtime behavior that exposes raw paths, raw filenames, file contents, raw
extensions, dependency names, package names, script names or values, coverage data, pass/fail
status, shell output, package-manager output, registry/network data, or broad filesystem behavior.

## Gate

Run:

```bash
make project-language-summary-proposal-check
make next-capability-readiness
```

These commands validate design-only selection readiness. They do not approve implementation.
