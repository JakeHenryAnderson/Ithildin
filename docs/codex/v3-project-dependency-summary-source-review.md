# v3 project.dependency.summary Source Review Handoff

Status: source-review handoff for the bounded read-only dependency count lane.

This handoff packages the implementation, tests, policy parity fixture, manifest, audit evidence,
and no-new-powers checks for `project.dependency.summary`.

- Finding namespace: `EXT-PDS-###`.
- Default ignored bundle: `var/review-packets/v0.9/project-dependency-summary-source-review/`.

## Review Scope

Reviewers should inspect:

- `tool-manifests/project-dependency-summary.yaml`;
- `apps/api/src/ithildin_api/read_tools.py`;
- resource derivation and policy preview/runtime parity for `project_dependencies`;
- governed call audit metadata for `project.dependency.summary`;
- MCP list/call behavior;
- parser output privacy and safe malformed-manifest behavior;
- no-new-powers and tool-surface gates.

## Closure Question

Can the `project.dependency.summary` lane close for continued local-preview development as one
bounded read-only metadata tool?

This handoff does not approve shell, package-manager execution, registry/network access, recursive
discovery, arbitrary manifest filenames, dependency names, package names, version constraints,
package script names or values, lockfile contents, SBOM/vulnerability/compliance claims, public
security-product positioning, or new powerful governed tool classes.

## Commands

- `make project-dependency-summary-implementation-gate`
- `make project-dependency-summary-source-review-bundle`
- `make policy-parity`
- `make release-check`
