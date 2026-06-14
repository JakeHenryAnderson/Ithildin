# v3 project.ci.summary Source Review Handoff

Status: focused source-review handoff. This document does not add runtime behavior beyond the
bounded read-only `project.ci.summary` implementation.

Latest internal refresh: `make project-ci-summary-source-review-bundle` was regenerated at commit
`ea344a1f3cd4ac7058e4b40579b424609bc9a429` with a clean working tree. The generated packet records
passing `make project-ci-summary-implementation-gate`, `make policy-parity`, and focused
`project.ci.summary` test output. This is local handoff evidence only; source-review closure still
requires reviewer intake under the `EXT-CI-###` namespace.

## Review Question

Can the `project.ci.summary` lane close for continued local-preview development as one bounded,
count-only project-intelligence tool?

## Scope To Review

- manifest: `tool-manifests/project-ci-summary.yaml`;
- executor path: in-process read executor dispatch for `project.ci.summary`;
- normalized resource type: `project_ci`;
- policy preview/runtime parity fixture;
- audit metadata for safe counts and section keys;
- MCP list/call path through governed execution;
- source-review bundle: `make project-ci-summary-source-review-bundle`.

## Required Boundary

The implementation must remain:

- read-only;
- workspace-confined;
- policy/audit/MCP mediated;
- count-only CI posture metadata and allowlisted labels only;
- free of workflow names, job names, raw paths, raw recursive listings, file contents, command or
  script values, environment names or values, secrets, dependency names, registry URLs, CI output,
  CI execution, shell, package-manager execution, Docker/Kubernetes/browser behavior, deployment
  readiness claims, compliance claims, broad filesystem writes, and public/security-product
  positioning.

## Handoff Command

Run:

```bash
make project-ci-summary-source-review-bundle
```

The generated bundle uses finding namespace `EXT-CI-###` and includes implementation source, tests,
contracts, policy parity evidence, implementation-gate output, focused test output, and artifact
hashes.
