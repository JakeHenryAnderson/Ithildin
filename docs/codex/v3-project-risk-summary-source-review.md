# project.risk.summary Source Review Handoff

Status: preimplementation source-review handoff skeleton.

This document defines the future source-review lane for `project.risk.summary`. It is intentionally
preimplementation-only: there is no manifest, executor, policy rule, MCP exposure, API change, UI
runtime behavior, or audit behavior yet.

## Review Boundary

- Tool candidate: `project.risk.summary`.
- Resource type: `project_risk`.
- Current tool count remains `22`.
- Runtime implementation is not present.
- Finding namespace: `EXT-RISK-SUMMARY-###`.
- This lane remains source-review pending until a future implementation exists and a focused
  reviewer disposition exists.

## Future Review Areas

A reviewer should inspect these areas only after a future runtime implementation is added:

- manifest/schema shape;
- workspace traversal and path safety;
- category allowlist and skipped-count behavior;
- policy preview/runtime resource parity;
- MCP governed path;
- audit metadata count-only behavior;
- negative transcript coverage;
- no-new-powers evidence.

## Claims To Test Later

Future source review must verify that the tool:

- returns count-only risk signal metadata and allowlisted labels only;
- never returns filenames, raw paths, file contents, dependency names, package names, CVE IDs,
  advisory IDs, secret names/values, command/script values, registry URLs, scanner output,
  vulnerability findings, compliance findings, security findings, or raw filesystem errors;
- does not execute shell, Git, package managers, CI, scanners, Docker, Kubernetes, browser tools, or
  network requests;
- remains one bounded read-only metadata capability and not a new power class.

## Required Commands Before Future Review

- `make project-risk-summary-proposal-check`;
- `make project-risk-summary-implementation-plan-check`;
- `make project-risk-summary-implementation-gate`;
- `make project-risk-summary-preimplementation-check`;
- `make project-risk-summary-review-handoff-check`;
- future runtime tests and `make release-check` after implementation.
