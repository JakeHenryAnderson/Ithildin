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
- [External Review Response Intake Template v2](external-review-response-intake-template-v2.md)
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
- [v0.5 Threat Model Delta](v0.5-threat-model-delta.md)
- [v0.5 Review Candidate Command](v0.5-review-candidate-command.md)
- [v0.5 Consolidated Packet Update](v0.5-consolidated-packet-update.md)
- [v0.5 External Review Prompt](v0.5-external-review-prompt.md)
- [v0.5 Boundary Decision Draft](v0.5-boundary-decision-draft.md)
- [v0.5 Handoff Packet](v0.5-handoff-packet.md)
- [v0.6 Preflight Transition Note](v0.6-preflight-transition.md)
- [v0.6 Boundary Charter](v0.6-boundary-charter.md)
- [v0.6 Milestone Manifest](v0.6-milestone-manifest.md)
- [v0.6 External Review Assignment Matrix](v0.6-external-review-assignment-matrix.md)
- [v0.6 External Review Dispatch Packets](v0.6-external-review-dispatch-packets.md)
- [v0.6 External Response Normalization](v0.6-external-response-normalization.md)
- [v0.6 Internal Subagent Review Wave](v0.6-internal-subagent-review-wave.md)
- [Capability Expansion Gate v2](capability-expansion-gate.md)
- [Tool-Surface Invariant Gate v2](tool-surface-invariant-gate.md)
- [No-New-Powers Guardrail v2](no-new-powers-guardrail.md)
- [Evidence-Confusion Gate v2](evidence-confusion-gate.md)
- [External-Review Closure Gate v2](external-review-closure-gate.md)
- [Source Review Runbook v2](source-review-runbook-v2.md)
- [Source Review Transcript Packet](source-review-transcript-packet.md)
- [Reviewer Artifact Manifest v2](reviewer-artifact-manifest-v2.md)
- [Source File Inspection Packet](source-file-inspection-packet.md)
- [Review Packet Source Pointers](review-packet-source-pointers.md)
- [Patch Apply Source Review Checklist](patch-apply-source-review-checklist.md)
- [Filesystem Source Review Checklist](filesystem-source-review-checklist.md)
- [HTTP Fetch Source Review Checklist](http-fetch-source-review-checklist.md)
- [Signed Evidence Source Review Checklist](signed-evidence-source-review-checklist.md)
- [Policy Parity Source Review Checklist](policy-parity-source-review-checklist.md)
- [MCP Ingress Source Review Checklist](mcp-ingress-source-review-checklist.md)
- [Review Console Source Review Checklist](review-console-source-review-checklist.md)
- [External Findings Intake Dry Run](external-findings-intake-dry-run.md)
- [Closure Matrix Evidence Sync](closure-matrix-evidence-sync.md)
- [Accepted Risk Register](accepted-risk-register.md)
- [Capability Decision Report Generator](capability-decision-report.md)

## Reading Rule

If documents appear to conflict, use this order:

1. v0.6 boundary charter, v0.6 milestone manifest, v0.5 handoff packet, and v0.6 preflight
   transition note for current handoff scope.
2. Threat model and executor contracts for security claims.
3. Evidence contracts and release-evidence schema for machine-readable fields.
4. Source-review closure matrix for what is reviewed, pending, accepted, or deferred.
5. README and release guides for operator-facing summaries.

Do not infer production readiness, external notarization, hosted trust, remote MCP safety, or new
tool powers from any single document.
