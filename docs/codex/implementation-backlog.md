# Implementation Backlog

## Completed Local Preview Track

| Task | Status | Spec |
| --- | --- | --- |
| 001 - Monorepo scaffold | Done | [tasks/001-monorepo-scaffold.md](tasks/001-monorepo-scaffold.md) |
| 002 - Core schemas | Done | [tasks/002-core-schemas.md](tasks/002-core-schemas.md) |
| 003 - FastAPI base service | Done | [tasks/003-fastapi-base-service.md](tasks/003-fastapi-base-service.md) |
| 004 - Tool registry | Done | [tasks/004-tool-registry.md](tasks/004-tool-registry.md) |
| 005 - Policy evaluator | Done | [tasks/005-policy-evaluator.md](tasks/005-policy-evaluator.md) |
| 006 - Audit writer | Done | [tasks/006-audit-writer.md](tasks/006-audit-writer.md) |
| 007 - Approval workflow | Done | [tasks/007-approval-workflow.md](tasks/007-approval-workflow.md) |
| 008 - MCP adapter | Done | [tasks/008-mcp-adapter.md](tasks/008-mcp-adapter.md) |
| 009 - Filesystem and git read tools | Done | [tasks/009-read-tools.md](tasks/009-read-tools.md) |
| 010 - Patch proposal and apply | Done | [tasks/010-patch-tools.md](tasks/010-patch-tools.md) |
| 011 - Approval-gated patch apply | Done | Sprint checkpoint |
| 012 - Review console | Done | Sprint checkpoint |
| 013 - Audit verification and export | Done | Sprint checkpoint |
| 014 - Policy preview | Done | Sprint checkpoint |
| 015 - Local demo deployment | Done | Sprint checkpoint |
| 016 - Local deployment verification | Done | Sprint checkpoint |
| 017 - Governed HTTP fetch | Done | Sprint checkpoint |
| 018 - Tool output redaction | Done | Sprint checkpoint |
| 019 - MCP integration flow | Done | Sprint checkpoint |
| 020 - Security regression suite | Done | Sprint checkpoint |
| 021 - Policy evidence | Done | Sprint checkpoint |
| 022 - OPA policy prototype | Done | Sprint checkpoint |
| 023 - Manifest lock verification | Done | Sprint checkpoint |
| 024 - OPA bundle verification | Done | Sprint checkpoint |
| 025 - Review console trust status | Done | Sprint checkpoint |
| 026 - Local preview release guide | Done | Sprint checkpoint |
| 027 - Local principal registry | Done | Sprint checkpoint |
| 028 - Role-aware tool visibility | Done | Sprint checkpoint |
| 029 - Ops backbone readiness | Done | Sprint checkpoint |
| 030 - Local model demo | Done | Sprint checkpoint |
| 031 - v0.1 release packaging | Done | Sprint checkpoint |
| 032 - Public boundary hardening | Done | [threat-model-and-non-goals.md](threat-model-and-non-goals.md) |
| 033 - Approval and evidence binding | Done | Sprint checkpoint |
| 034 - Executor security edge cases | Done | Sprint checkpoint |
| 035 - Public v0.1 release candidate polish | Done | [v0.1-public-preview-release-notes.md](v0.1-public-preview-release-notes.md) |
| 044 - Signed audit exports | Done | [signed-audit-exports.md](signed-audit-exports.md) |
| 045 - Signed manifest locks | Done | [signed-manifest-locks.md](signed-manifest-locks.md) |
| 046 - Policy test harness | Done | `policies/tests/default.yaml`, `scripts/policy_test.py` |
| 047 - Named workspace model | Done | `workspaces/local.yaml`, `/workspaces` |
| 048 - Policy impact preview | Done | `/policy/impact-preview`, `scripts/policy_impact.py` |
| 049 - Approval review UX v2 | Done | `/approvals/review`, review console evidence checks |
| 050 - Local admin auth ergonomics | Done | `make admin-token-generate`, `/system/status` token posture |
| 051 - Audit diagnostics | Done | `/audit-events/diagnostics`, `make audit-diagnostics` |
| 052 - MCP Inspector recipes | Done | [mcp-inspector-recipes.md](mcp-inspector-recipes.md) |
| 053 - Redaction evidence UX | Done | `/system/status`, review console audit table |
| 054 - Policy decision evidence | Done | `decision_evidence.py`, `/policy/preview` |
| 055 - Evidence contracts | Done | [evidence-contracts.md](evidence-contracts.md) |
| 056 - Approval drift regressions | Done | `tests/test_governed_tool_calls.py` |
| 057 - Path ambiguity hardening | Done | `tests/test_read_tools.py`, `tests/test_patch_proposals.py` |
| 058 - HTTP proxy regression coverage | Done | `tests/test_http_tools.py` |
| 059 - v0.2 roadmap refresh | Done | [v0.2-planning-seed.md](v0.2-planning-seed.md) |
| 060 - Release packet evidence | Done | `make release-packet`, `scripts/release_packet.py` |
| 061 - v0.2 review packet | Done | [v0.2-review-packet.md](v0.2-review-packet.md) |
| 062 - Review response cleanup | Done | [v0.2-review-response-and-rc-cleanup.md](v0.2-review-response-and-rc-cleanup.md) |
| 063 - v0.2 external review prompt | Done | [v0.2-external-review-prompt.md](v0.2-external-review-prompt.md) |
| 064 - v0.2 review bundle command | Done | `make review-packet-bundle`, `scripts/review_packet_bundle.py` |
| 065 - v0.2 handoff polish | Done | README/release packet handoff sequence |
| 066 - v0.2 label clarity | Done | v0.2 review candidate / v0.1 runtime boundary wording |
| 067 - Release evidence metadata | Done | review-doc hashes and release-check transcript metadata |
| 068 - Signed evidence demo fixtures | Done | `make signed-evidence-demo` |
| 069 - Negative review recipes | Done | [negative-review-recipes.md](negative-review-recipes.md) |
| 070 - Review packet regeneration | Done | refreshed review bundle and consolidated staging |
| 071 - Release evidence hashes | Done | renamed release-check fields and `artifact-hashes.json` |
| 072 - Reviewer reproduction map | Done | [reviewer-reproduction-map.md](reviewer-reproduction-map.md) |
| 073 - Final v0.2 packet regeneration | Done | final bundle and consolidated review staging |
| 074 - Consolidated attachment hashes | Done | `make review-packet-consolidated` |
| 075 - Source review closure matrix | Done | [source-review-closure-matrix.md](source-review-closure-matrix.md) |
| 076 - Reviewer finding template | Done | [reviewer-finding-template.md](reviewer-finding-template.md) |
| 077 - Negative review transcripts | Done | `make negative-review-transcripts` |
| 078 - Internal source review pass 1 | Done | [internal-source-review-pass-1.md](internal-source-review-pass-1.md) |
| 079 - Patch apply recovery evidence | Done | `/patch-apply-diagnostics`, patch apply attempt records |
| 080 - Filesystem executor contract | Done | [filesystem-executor-contract.md](filesystem-executor-contract.md), `make filesystem-contract-check` |
| 081 - Filesystem evidence artifact | Done | `filesystem-contract-check.txt` in review bundles |
| 082 - Review candidate command | Done | `make review-candidate` |
| 083 - Internal AI review workflow | Done | [internal-ai-review-workflow.md](internal-ai-review-workflow.md), `make internal-review-packet` |
| 084 - Autonomous sprint guardrails | Done | [autonomous-sprint-guardrails.md](autonomous-sprint-guardrails.md) |

## v0.3-Prep Assurance Track

| Task | Status | Spec |
| --- | --- | --- |
| 085 - External-review readiness freeze | Done | [v0.3-milestone-manifest.md](v0.3-milestone-manifest.md) |
| 086 - Source-review closure matrix v2 | Done | [source-review-closure-matrix.md](source-review-closure-matrix.md) |
| 087 - Reviewer finding intake automation | Done | [reviewer-finding-intake.md](reviewer-finding-intake.md), `make reviewer-findings-check` |
| 088 - Patch-apply crash/failure simulation | Done | `tests/test_governed_tool_calls.py` |
| 089 - Patch-apply state-machine contract | Done | [patch-apply-state-machine.md](patch-apply-state-machine.md) |
| 090 - Filesystem adversarial race harness | Done | `tests/test_read_tools.py`, `tests/test_security_regressions.py` |
| 091 - Filesystem contract enforcement | Done | `make release-check`, `make filesystem-contract-check` |
| 092 - HTTP canonicalization adversarial suite | Done | `tests/test_http_tools.py` |
| 093 - HTTP executor contract | Done | [http-executor-contract.md](http-executor-contract.md) |
| 094 - Signed-evidence replay/substitution tests | Done | `tests/test_audit_writer.py`, `tests/test_tool_registry.py` |
| 095 - Evidence contract versioning | Done | [evidence-contracts.md](evidence-contracts.md) |
| 096 - Policy preview/runtime parity harness | Done | [policy-parity-harness.md](policy-parity-harness.md), `make policy-parity` |
| 097 - OPA parity decision point | Done | [opa-parity-decision.md](opa-parity-decision.md) |
| 098 - MCP ingress bypass audit | Done | [mcp-ingress-bypass-audit.md](mcp-ingress-bypass-audit.md), `tests/test_mcp_adapter.py` |
| 099 - Review-console approval evidence clarity | Done | [review-console-assurance.md](review-console-assurance.md), `apps/ui/src/App.tsx` |
| 100 - Review-console failure-state and trust-status UX | Done | [review-console-assurance.md](review-console-assurance.md), `/patch-apply-diagnostics` UI |
| 101 - Negative transcript expansion | Done | `make negative-review-transcripts`, [negative-review-recipes.md](negative-review-recipes.md) |
| 102 - Release evidence schema hardening | Done | [release-evidence-schema.md](release-evidence-schema.md), `make release-evidence-validate` |
| 103 - Review packet diff command | Done | [review-packet-diff.md](review-packet-diff.md), `make review-packet-diff` |
| 104 - Executor contract set | Done | [executor-contract-set.md](executor-contract-set.md) |
| 105 - Tool manifest negative validation suite | Done | [manifest-validation-suite.md](manifest-validation-suite.md), `tests/test_tool_registry.py` |
| 106 - Principal/workspace registry fail-closed suite | Done | [registry-fail-closed-suite.md](registry-fail-closed-suite.md), `tests/test_identity.py`, `tests/test_workspaces.py` |
| 107 - Audit integrity adversarial suite | Done | [audit-integrity-adversarial-suite.md](audit-integrity-adversarial-suite.md), `tests/test_audit_writer.py` |
| 108 - Release guardrail expansion | Done | [release-guardrail-expansion.md](release-guardrail-expansion.md), `scripts/release_guardrails.py` |
| 109 - Internal AI review packet v2 | Done | [internal-review-packet-v2.md](internal-review-packet-v2.md), `make internal-review-packet` |
| 110 - External review packet v3 | Done | [v0.3-review-packet.md](v0.3-review-packet.md), [v0.3-external-review-prompt.md](v0.3-external-review-prompt.md) |
| 111 - External review intake and closure | Done | [external-review-intake-and-closure.md](external-review-intake-and-closure.md), `make reviewer-findings-check` |
| 112 - v0.3 boundary decision memo | Done | [v0.3-boundary-decision.md](v0.3-boundary-decision.md) |
| 113 - v0.4 boundary charter | Done | [v0.4-boundary-charter.md](v0.4-boundary-charter.md) |
| 114 - Review run manifest | Done | [review-run-manifest-schema.md](review-run-manifest-schema.md), `make review-run-manifest-check` |
| 115 - Review findings aggregator | Done | [v0.3-review-findings-summary.md](v0.3-review-findings-summary.md), `make review-findings-summary` |
| 116 - Source-review closure matrix v3 | Done | [source-review-closure-matrix.md](source-review-closure-matrix.md), `make release-guardrails` |
| 117 - Patch apply failure evidence v2 | Done | `PatchApplyFaultHook`, `tests/test_governed_tool_calls.py` |
| 118 - Patch apply state-machine formalization v2 | Done | [patch-apply-state-machine.md](patch-apply-state-machine.md), transition tests |
| 119 - Filesystem adversarial race harness v2 | Done | bounded read/proposal target-swap tests in `tests/test_read_tools.py` and `tests/test_patch_proposals.py` |
| 120 - Filesystem platform support gate v2 | Done | `/system/status`, release evidence, UI warning surface, `make filesystem-contract-check` |
| 121 - HTTP canonicalization corpus v2 | Done | `tests/fixtures/http_canonicalization_corpus.json`, `tests/test_http_tools.py` |
| 122 - HTTP fetch executor contract v2 | Done | [http-executor-contract.md](http-executor-contract.md), corpus-linked review pointers |

## v0.4 Remaining Roadmap

These tasks are planned in [v0.4-milestone-manifest.md](v0.4-milestone-manifest.md). They are not
implemented until each receives its own checkpoint commit and gate output.

| Task | Status | Spec |
| --- | --- | --- |
| 123 - v0.4 gating overlay | Done | [v0.4-gating-overlay.md](v0.4-gating-overlay.md), [v0.4-milestone-manifest.md](v0.4-milestone-manifest.md) |
| 124 - Release evidence schema gate v2 | Done | `make release-evidence-gate` is included in `make release-check`. |
| 125 - Review packet diff gate v2 | Done | `make review-packet-diff-gate OLD=... NEW=...` requires artifact hashes and fails on removed artifacts. |
| 126 - Release guardrail expansion v2 | Done | `make release-guardrails` validates v0.4 horizontal gate status, release targets, packet diff gate, and deferred-power guardrails. |
| 127 - Secrets hygiene and packet redaction scanner | Done | [packet-redaction-scanner.md](packet-redaction-scanner.md), `make packet-redaction-scan` |
| 128 - Test isolation and determinism gate | Done | [test-determinism-gate.md](test-determinism-gate.md), `make determinism-check` |
| 129 - Signed-evidence verifier hardening | Done | `make signed-evidence-demo-verify` verifies demo audit and manifest-lock signatures. |
| 130 - Audit integrity adversarial suite v2 | Done | SQLite index/payload drift and duplicate exported event IDs fail verification. |
| 131 - Evidence contract versioning v2 | Done | `make evidence-contracts-check` validates stable evidence contracts. |
| 132 - Local audit retention and export lifecycle diagnostics | Done | [audit-export-lifecycle-diagnostics.md](audit-export-lifecycle-diagnostics.md), `make audit-diagnostics` |
| 133 - Policy preview/runtime parity harness v2 | Done | Pre-policy denial parity added to `make policy-parity`. |
| 134 - OPA boundary decision | Done | [opa-parity-decision.md](opa-parity-decision.md) reaffirms YAML canonical gates. |
| 135 - Registry fail-closed exhaustive suite | Done | [registry-fail-closed-suite.md](registry-fail-closed-suite.md), expanded manifest-lock drift tests |
| 136 - Manifest-change review workflow | Done | [manifest-change-review-workflow.md](manifest-change-review-workflow.md), `make manifest-change-review` |
| 137 - MCP ingress bypass audit v2 | Done | [mcp-ingress-bypass-audit.md](mcp-ingress-bypass-audit.md), `tests/test_mcp_adapter.py` |
| 138 - Local auth/session hardening within current boundary | Done | [local-auth-boundary.md](local-auth-boundary.md), `/system/status` |
| 139 - Review-console approval UX v3 | Done | [review-console-assurance.md](review-console-assurance.md), grouped binding evidence |
| 140 - Review-console failure and unauthorized states | Done | [review-console-assurance.md](review-console-assurance.md), locked/unavailable console states |
| 141 - Negative transcript expansion v2 | Done | [negative-review-recipes.md](negative-review-recipes.md), `make negative-review-transcripts` |
| 142 - Adversarial corpus framework | Done | [adversarial-corpus-framework.md](adversarial-corpus-framework.md), `make adversarial-corpus-check` |
| 143 - Performance and resource-limit sanity | Done | [resource-limit-sanity.md](resource-limit-sanity.md), `make resource-limit-check` |
| 144 - CI and platform planning without broad claims | Done | [ci-platform-plan.md](ci-platform-plan.md), platform claim boundaries |
| 145 - Redaction evidence and leak-boundary clarity | Done | [redaction-evidence-boundary.md](redaction-evidence-boundary.md), leak-boundary wording |
| 146 - Demo scenario pack v2 | Done | [demo-scenario-pack-v2.md](demo-scenario-pack-v2.md), `make demo-scenario-pack` |
| 147 - Documentation information architecture cleanup | Done | [review-docs-index.md](review-docs-index.md), docs navigation |
| 148 - v0.4 threat model refresh | Done | [v0.4-threat-model-refresh.md](v0.4-threat-model-refresh.md), accepted local-preview risks |
| 149 - v0.4 review packet generator | Done | [v0.4-review-packet-generator.md](v0.4-review-packet-generator.md), `make v04-review-packet` |
| 150 - External review intake and closure workflow v2 | Done | [external-review-intake-v2.md](external-review-intake-v2.md), closure guardrails |
| 151 - v0.4 external review packet and capability decision seed | Done | [v0.4-review-packet.md](v0.4-review-packet.md), [v0.4-capability-decision-seed.md](v0.4-capability-decision-seed.md) |

## v0.5 Source Review and Capability Decision Track

These tasks are planned in [v0.5-milestone-manifest.md](v0.5-milestone-manifest.md). They are source-review
closure and decision-preparation tasks, not new governed tool powers.

| Task | Status | Spec |
| --- | --- | --- |
| 152 - v0.5 roadmap from v0.4 review | Done | [v0.5-roadmap-from-v0.4-review.md](v0.5-roadmap-from-v0.4-review.md), [v0.5-milestone-manifest.md](v0.5-milestone-manifest.md) |
| 153 - Capability expansion gate v2 | Done | [capability-expansion-gate.md](capability-expansion-gate.md), `make capability-expansion-gate` |
| 154 - Tool-surface invariant gate v2 | Done | [tool-surface-invariant-gate.md](tool-surface-invariant-gate.md), `make tool-surface-invariant-gate` |
| 155 - Evidence-confusion gate v2 | Done | [evidence-confusion-gate.md](evidence-confusion-gate.md), `make evidence-confusion-gate` |
| 156 - External-review closure gate v2 | Done | [external-review-closure-gate.md](external-review-closure-gate.md), `make external-review-closure-gate` |
| 157 - Source review runbook v2 | Done | [source-review-runbook-v2.md](source-review-runbook-v2.md) |
| 158 - Source file inspection packet | Done | [source-file-inspection-packet.md](source-file-inspection-packet.md) |
| 159 - Patch apply source review checklist | Done | [patch-apply-source-review-checklist.md](patch-apply-source-review-checklist.md) |
| 160 - Filesystem source review checklist | Done | [filesystem-source-review-checklist.md](filesystem-source-review-checklist.md) |
| 161 - HTTP fetch source review checklist | Done | [http-fetch-source-review-checklist.md](http-fetch-source-review-checklist.md) |
| 162 - Signed evidence source review checklist | Done | [signed-evidence-source-review-checklist.md](signed-evidence-source-review-checklist.md) |
| 163 - Policy parity source review checklist | Done | [policy-parity-source-review-checklist.md](policy-parity-source-review-checklist.md) |
| 164 - MCP ingress source review checklist | Done | [mcp-ingress-source-review-checklist.md](mcp-ingress-source-review-checklist.md) |
| 165 - Review console source review checklist | Done | [review-console-source-review-checklist.md](review-console-source-review-checklist.md) |
| 166 - External findings intake dry run | Done | [external-findings-intake-dry-run.md](external-findings-intake-dry-run.md), `make external-findings-intake-dry-run` |
| 167 - Closure matrix evidence sync | Done | [closure-matrix-evidence-sync.md](closure-matrix-evidence-sync.md), `make closure-matrix-evidence-sync` |
| 168 - Accepted risk register | Done | [accepted-risk-register.md](accepted-risk-register.md), `make accepted-risk-register-check` |
| 169 - Capability decision report generator | Done | [capability-decision-report.md](capability-decision-report.md), `make capability-decision-report` |
| 170 - No-new-powers release guardrail v2 | Done | [no-new-powers-guardrail.md](no-new-powers-guardrail.md), `make no-new-powers-guardrail` |
| 171 - Source review transcript packet | Done | [source-review-transcript-packet.md](source-review-transcript-packet.md), `make source-review-transcript-packet` |
| 172 - Reviewer artifact manifest v2 | Done | [reviewer-artifact-manifest-v2.md](reviewer-artifact-manifest-v2.md), `make reviewer-artifact-manifest` |
| 173 - External review response intake template v2 | Done | [external-review-response-intake-template-v2.md](external-review-response-intake-template-v2.md), `make external-response-template-check` |
| 174 - Review packet source pointers | Done | [review-packet-source-pointers.md](review-packet-source-pointers.md), `make review-packet-source-pointers` |
| 175 - v0.5 threat model delta | Done | [v0.5-threat-model-delta.md](v0.5-threat-model-delta.md), `make v05-threat-model-delta-check` |
| 176 - v0.5 review candidate command | Done | [v0.5-review-candidate-command.md](v0.5-review-candidate-command.md), `make v05-review-candidate` |
| 177 - v0.5 consolidated packet update | Done | [v0.5-consolidated-packet-update.md](v0.5-consolidated-packet-update.md), `make review-packet-consolidated` |
| 178 - v0.5 external review prompt | Done | [v0.5-external-review-prompt.md](v0.5-external-review-prompt.md) |
| 179 - v0.5 boundary decision draft | Done | [v0.5-boundary-decision-draft.md](v0.5-boundary-decision-draft.md), `make v05-boundary-decision-draft-check` |
| 180 - v0.5 handoff packet and go/no-go seed | Done | [v0.5-handoff-packet.md](v0.5-handoff-packet.md), `make v05-handoff-packet-check` |

## v0.6 External Review Execution and Closure Track

These tasks are planned in [v0.6-milestone-manifest.md](v0.6-milestone-manifest.md). They execute
external/source review closure for the current local-preview boundary. They are not capability
expansion tasks.

| Task | Status | Spec |
| --- | --- | --- |
| 181 - v0.6 boundary charter and freeze | Done | [v0.6-boundary-charter.md](v0.6-boundary-charter.md), [v0.6-milestone-manifest.md](v0.6-milestone-manifest.md) |
| 182 - External reviewer assignment matrix | Done | [v0.6-external-review-assignment-matrix.md](v0.6-external-review-assignment-matrix.md) |
| 183 - External review packet dispatch set | Done | [v0.6-external-review-dispatch-packets.md](v0.6-external-review-dispatch-packets.md), `make v06-review-dispatch-packets` |
| 184 - External response normalization | Done | [v0.6-external-response-normalization.md](v0.6-external-response-normalization.md), `make external-response-normalize FILE=...` |
| 185 - Patch apply external review execution packet | Source review received; findings remediated | [v0.6-patch-apply-external-review-execution.md](v0.6-patch-apply-external-review-execution.md), `EXT-PA-001` through `EXT-PA-004`; patch-apply closure still requires post-intake gates and any reviewer follow-up. |
| 185-192 - Wave 2 internal proxy review execution | Internally remediated | [v0.6-internal-review-execution-wave-2.md](v0.6-internal-review-execution-wave-2.md); `SUB-010` through `SUB-077` are fixed; external review remains pending. |
| 193 - External finding triage wave | Done | [v0.6-lane-status-board.md](v0.6-lane-status-board.md), `make v06-lane-status`; patch apply remains external-pending until reviewer recheck/closure evidence exists. |
| 194-199 - v0.6 closure-readiness bundle | Done | [v0.6-post-review-packet.md](v0.6-post-review-packet.md), [source-review-closure-matrix-v4.md](source-review-closure-matrix-v4.md), [accepted-risk-register-v2.md](accepted-risk-register-v2.md), `make v06-closure-readiness`; external rows remain pending. |
| 193-215 - v0.6 triage, closure, decisions, and handoff | Handoff started | [v0.6-closure-handoff.md](v0.6-closure-handoff.md), [v0.6-gpt-55-pro-handoff-prompt.md](v0.6-gpt-55-pro-handoff-prompt.md); external review remains pending. |

## Future Candidate Track

| Area | Status | Notes |
| --- | --- | --- |
| Production identity | Deferred | OIDC, SAML, SCIM, hosted sessions, and multi-tenant stores. |
| Runtime Postgres | Deferred | Real Postgres stores and migrations; current support is readiness-only. |
| Hosted observability | Deferred | Production collectors and dashboards; current OpenTelemetry is opt-in preview. |
| Kubernetes and executor hardening | Deferred | Kubernetes assets and containerized execution remain outside v0.1. |
| External anchoring and hosted supply-chain signing | Deferred | Local audit export and manifest lock signing exist; external trust roots remain future work. |
| Remote MCP hosting | Deferred | Stdio-only local MCP remains the v0.1 boundary. |
| Plugin SDK and marketplace | Deferred | Requires stronger signing, review UX, executor contracts, and stable policy impact tooling. |

## v0.2 Planning Seed

Use [v0.2-review-response-and-rc-cleanup.md](v0.2-review-response-and-rc-cleanup.md) and
[v0.2-review-packet.md](v0.2-review-packet.md) as the external/code review handoff, with
[v0.2-planning-seed.md](v0.2-planning-seed.md) as the completed trust-focused v0.2 roadmap. The
current track has completed trust-evidence,
policy-confidence, workspace/approval UX, local-operations polish, evidence-clarity,
security-matrix closure items, and the first internal source review gate.

## Definition of MVP Done

- Local Docker Compose deployment exists.
- MCP client can list and call governed tools.
- Static tool manifests are validated on startup.
- Policy evaluator is deny-default.
- Committed policy fixtures pass through `make policy-test`.
- Write tools require approval.
- Audit events are stored in SQLite and hash-chained JSONL.
- Path traversal, symlink escape, SSRF, approval replay, and invalid schema cases have tests.
- Documentation explains the threat model and security limitations.
- Principal registry and role-aware tool visibility are enabled for local preview.
- Named workspace registry is enabled for scoped read, git, and patch proposal tools.
- Static docs site generation exists for handoff review.
- Public-preview warning labels, threat model links, MCP examples, and release notes are checked.
- MCP Inspector recipes document governed list/call, approval-required, denial, and audit flows.
- Evidence contracts document stable audit, policy, approval, redaction, and signed-bundle fields.
- Security matrix closure tests cover approval drift, path ambiguity, hardlinks, HTTP proxy
  inheritance, and canonical host behavior.
- v0.2 review packet and `make release-packet` exist for external review handoff.
- `make review-packet-bundle` packages the review docs and secret-free command outputs.
- `make signed-evidence-demo` generates non-production locally signed evidence fixtures for review.
- Internal source review pass 1 is recorded before external/source review handoff.
- Filesystem executor contract and capability check document macOS/Linux support and Windows/WSL
  unsupported status for workspace/race claims.
- `make review-candidate` runs the full local handoff gate and regenerates review artifacts.
- Autonomous sprint guardrails define stop conditions, wall-hit reporting, and external-review
  cadence.
- `make release-check` passes before local-preview handoff.
