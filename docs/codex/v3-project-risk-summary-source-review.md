# project.risk.summary Source Review Handoff

Status: implemented source-review handoff.

This document defines the source-review lane for the implemented `project.risk.summary` tool. It is
ready for focused source-review disposition for the v0.1 local-preview runtime boundary only; it
does not claim production security, compliance automation, vulnerability scanning, or external
closure.

## Review Boundary

- Tool candidate: `project.risk.summary`.
- Resource type: `project_risk`.
- Current tool count is `23`.
- Runtime implementation is present.
- Finding namespace: `EXT-RISK-SUMMARY-###`.
- This lane remains source-review pending until a focused reviewer disposition exists.

## Review Areas

A reviewer should inspect these areas:

- manifest/schema shape;
- workspace traversal and path safety;
- category allowlist and skipped-count behavior;
- policy preview/runtime resource parity;
- MCP governed path;
- audit metadata count-only behavior;
- negative transcript coverage;
- no-new-powers evidence.

## Claims To Test

Source review must verify that the tool:

- returns count-only risk signal metadata and allowlisted labels only;
- never returns filenames, raw paths, file contents, dependency names, package names, CVE IDs,
  advisory IDs, secret names/values, command/script values, registry URLs, scanner output,
  vulnerability findings, compliance findings, security findings, or raw filesystem errors;
- does not execute shell, Git, package managers, CI, scanners, Docker, Kubernetes, browser tools, or
  network requests;
- remains one bounded read-only metadata capability and not a new power class.

## Required Commands

- `make project-risk-summary-proposal-check`;
- `make project-risk-summary-implementation-plan-check`;
- `make project-risk-summary-implementation-gate`;
- `make project-risk-summary-preimplementation-check`;
- `make project-risk-summary-review-handoff-check`;
- `make project-risk-summary-source-review-bundle`;
- focused runtime tests and `make release-check`.
