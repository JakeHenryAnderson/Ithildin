# v3 project.config.summary Source Review Handoff

Status: focused source-review handoff. This document does not add runtime behavior beyond the
bounded read-only `project.config.summary` implementation.

## Review Question

Can the `project.config.summary` lane close for continued local-preview development as one
bounded, count-only project-intelligence tool?

## Scope To Review

- manifest: `tool-manifests/project-config-summary.yaml`;
- executor path: in-process read executor dispatch for `project.config.summary`;
- normalized resource type: `project_config`;
- policy preview/runtime parity fixture;
- audit metadata for safe counts and section keys;
- source-review bundle: `make project-config-summary-source-review-bundle`.

## Required Boundary

The implementation must remain:

- read-only;
- workspace-confined;
- policy/audit/MCP mediated;
- count-only config posture metadata and allowlisted labels only;
- free of config file names, raw paths, raw recursive listings, file contents, config contents,
  config values, dependency names, package names, package script names or values, environment names
  or values, command output, package-manager execution, config parser execution, registry/network
  access, shell, broad filesystem writes, deployment-readiness claims, and public/security-product
  positioning.

## Handoff Command

Run:

```bash
make project-config-summary-source-review-bundle
```

The generated bundle uses finding namespace `EXT-CONFIG-###` and includes implementation source,
tests, contracts, policy parity evidence, implementation-gate output, focused test output, and
artifact hashes.
