# Review Docs Index

Task 147 adds this information-architecture index so reviewers do not have to infer the document
map from filenames alone. It is a navigation aid, not new evidence and not a claim that review is
externally closed.

## Start Here

- [README](../../README.md) - current local-preview posture, commands, and warning labels.
- [Local Preview Release Guide](local-preview-release.md) - operator setup and handoff flow.
- [v0.4 Boundary Charter](v0.4-boundary-charter.md) - what v0.4 may change and what remains
  deferred.
- [v0.4 Milestone Manifest](v0.4-milestone-manifest.md) - task status, waves, gates, and stop
  conditions.

## Threat and Boundary

- [Threat Model and Non-Goals](threat-model-and-non-goals.md)
- [v0.4 Threat Model Refresh](v0.4-threat-model-refresh.md)
- [Filesystem Executor Contract](filesystem-executor-contract.md)
- [HTTP Executor Contract](http-executor-contract.md)
- [Executor Contract Set](executor-contract-set.md)
- [Local Auth Boundary](local-auth-boundary.md)
- [Redaction Evidence Boundary](redaction-evidence-boundary.md)

## Evidence and Gates

- [Evidence Contracts](evidence-contracts.md)
- [Release Evidence Schema](release-evidence-schema.md)
- [Review Packet Diff](review-packet-diff.md)
- [v0.4 Review Packet Generator](v0.4-review-packet-generator.md)
- [Packet Redaction Scanner](packet-redaction-scanner.md)
- [Test Determinism Gate](test-determinism-gate.md)
- [Resource Limit Sanity](resource-limit-sanity.md)
- [Demo Scenario Pack v2](demo-scenario-pack-v2.md)

## Review Closure

- [Source Review Closure Matrix](source-review-closure-matrix.md)
- [Internal Source Review Pass 1](internal-source-review-pass-1.md)
- [Reviewer Finding Template](reviewer-finding-template.md)
- [Reviewer Finding Intake](reviewer-finding-intake.md)
- [External Review Intake and Closure](external-review-intake-and-closure.md)
- [External Review Intake v2](external-review-intake-v2.md)
- [v0.3 Boundary Decision](v0.3-boundary-decision.md)

## Reproduction and Packet Handoff

- [Reviewer Reproduction Map](reviewer-reproduction-map.md)
- [Negative Review Recipes](negative-review-recipes.md)
- [MCP Inspector Recipes](mcp-inspector-recipes.md)
- [v0.3 Review Packet](v0.3-review-packet.md)
- [v0.3 External Review Prompt](v0.3-external-review-prompt.md)
- [v0.4 Review Packet](v0.4-review-packet.md)
- [v0.4 External Review Prompt](v0.4-external-review-prompt.md)
- [v0.4 Capability Decision Seed](v0.4-capability-decision-seed.md)
- [v0.5 Roadmap From v0.4 Review](v0.5-roadmap-from-v0.4-review.md)
- [v0.5 Milestone Manifest](v0.5-milestone-manifest.md)
- [Capability Expansion Gate v2](capability-expansion-gate.md)
- [Tool-Surface Invariant Gate v2](tool-surface-invariant-gate.md)
- [Evidence-Confusion Gate v2](evidence-confusion-gate.md)
- [External-Review Closure Gate v2](external-review-closure-gate.md)
- [Source Review Runbook v2](source-review-runbook-v2.md)
- [Source File Inspection Packet](source-file-inspection-packet.md)
- [Patch Apply Source Review Checklist](patch-apply-source-review-checklist.md)
- [Filesystem Source Review Checklist](filesystem-source-review-checklist.md)
- [HTTP Fetch Source Review Checklist](http-fetch-source-review-checklist.md)
- [Signed Evidence Source Review Checklist](signed-evidence-source-review-checklist.md)

## Reading Rule

If documents appear to conflict, use this order:

1. v0.4 boundary charter and milestone manifest for current scope.
2. Threat model and executor contracts for security claims.
3. Evidence contracts and release-evidence schema for machine-readable fields.
4. Source-review closure matrix for what is reviewed, pending, accepted, or deferred.
5. README and release guides for operator-facing summaries.

Do not infer production readiness, external notarization, hosted trust, remote MCP safety, or new
tool powers from any single document.
