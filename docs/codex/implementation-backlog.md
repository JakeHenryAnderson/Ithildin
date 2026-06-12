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
| 030a - Local prompt triage | Done | [local-prompt-triage.md](local-prompt-triage.md), `make local-prompt-triage` |
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
| 185 - Patch apply external review execution packet | Source review received; findings remediated and later rechecked | [v0.6-patch-apply-external-review-execution.md](v0.6-patch-apply-external-review-execution.md), `EXT-PA-001` through `EXT-PA-004`; final local-preview patch-apply closure is recorded in Task 219. |
| 185-192 - Wave 2 internal proxy review execution | Internally remediated | [v0.6-internal-review-execution-wave-2.md](v0.6-internal-review-execution-wave-2.md); `SUB-010` through `SUB-077` are fixed; external review remains pending. |
| 193 - External finding triage wave | Done | [v0.6-lane-status-board.md](v0.6-lane-status-board.md), `make v06-lane-status`; later Task 219 records patch-apply closure for the v0.1 local-preview lane. |
| 194-199 - v0.6 closure-readiness bundle | Done | [v0.6-post-review-packet.md](v0.6-post-review-packet.md), [source-review-closure-matrix-v4.md](source-review-closure-matrix-v4.md), [accepted-risk-register-v2.md](accepted-risk-register-v2.md), `make v06-closure-readiness`; external rows remain pending. |
| 200-215 - v0.6 final no-go handoff | Done | [v0.6-final-go-no-go-packet.md](v0.6-final-go-no-go-packet.md), [v0.6-handoff-to-user.md](v0.6-handoff-to-user.md), `make v06-final-handoff`; external handoff is go, capability expansion and public/security-product positioning remain no-go. |
| 193-215 - v0.6 triage, closure, decisions, and handoff | Done | [v0.6-closure-handoff.md](v0.6-closure-handoff.md), [v0.6-gpt-55-pro-handoff-prompt.md](v0.6-gpt-55-pro-handoff-prompt.md); patch apply is closed by Task 219 and remaining external rows remain pending. |

## v0.7 External Review Closure Track

v0.7 begins from the v0.6 final no-go state. It is external/source-review closure work only and
does not approve public preview, capability design, capability implementation, or new tool powers.

| Task | Status | Spec |
| --- | --- | --- |
| 216 - v0.7 closure charter and freeze | Done | [v0.7-external-review-closure-charter.md](v0.7-external-review-closure-charter.md), `make v07-closure-prep` |
| 217 - v0.6 final packet sanity review | Done | [v0.6-final-packet-sanity-review.md](v0.6-final-packet-sanity-review.md), `make v07-closure-prep` |
| 218 - External-review row partition | Done | [v0.7-external-review-row-partition.md](v0.7-external-review-row-partition.md), `make v07-closure-prep`; original 55 pending rows are partitioned into executable review batches. |
| 219 - Patch-apply recheck closure | Done | [v0.7-patch-apply-recheck-request.md](v0.7-patch-apply-recheck-request.md), [v0.7-patch-apply-recheck-outcome.md](v0.7-patch-apply-recheck-outcome.md), `make v07-patch-apply-recheck-prep`; patch apply is closed for the v0.1 local-preview lane only. |
| 220 - Filesystem/platform source review pass | Done | [v0.7-filesystem-platform-source-review.md](v0.7-filesystem-platform-source-review.md); the focused external/source review lane is closed for local-preview filesystem/platform posture. |
| 221 - Filesystem source-review bundle | Done | `make filesystem-source-review-bundle` builds the focused source/test/evidence handoff requested by `EXT-FS-001` under ignored `var/review-packets/v0.7/filesystem-source-review/`. |
| 222 - HTTP fetch source-review bundle | Done | `make http-fetch-source-review-bundle` builds the focused `http.fetch` source/test/evidence handoff under ignored `var/review-packets/v0.7/http-fetch-source-review/`. |
| 223 - HTTP fetch source-review closure | Done | [v0.7-http-fetch-source-review.md](v0.7-http-fetch-source-review.md); GPT 5.5 Pro source-level review recorded no new findings, and the lane is closed for local-preview `http.fetch` only. |
| 224 - Signed evidence source-review bundle | Done | `make signed-evidence-source-review-bundle` builds the focused audit/signed-evidence source/test/evidence handoff under ignored `var/review-packets/v0.7/signed-evidence-source-review/`. |
| 225 - Signed evidence source-review closure | Done | [v0.7-signed-evidence-source-review.md](v0.7-signed-evidence-source-review.md); GPT 5.5 Pro source-level review recorded no new findings, and signed evidence, audit integrity, and manifest-lock verification are closed for local-preview evidence only. |
| 226 - Policy/registry source-review bundle | Done | `make policy-registry-source-review-bundle` builds the focused policy/registry source/test/evidence handoff under ignored `var/review-packets/v0.7/policy-registry-source-review/`. |
| 227 - MCP ingress source-review bundle | Done | `make mcp-ingress-source-review-bundle` builds the focused stdio MCP ingress source/test/evidence handoff under ignored `var/review-packets/v0.7/mcp-ingress-source-review/`. |
| 228 - MCP ingress source-review closure | Done | [v0.7-mcp-ingress-source-review.md](v0.7-mcp-ingress-source-review.md); GPT 5.5 Pro source-level review recorded no new findings, and stdio MCP ingress plus the MCP ingress source-review checklist are closed for local-preview only. |
| 229 - Review console internal proxy remediation | Done | `SUB-078` and `SUB-079` fixed approval-time binding review and patch diagnostics detail; `SUB-080` is now closed by the v0.8 Vitest/React Testing Library interaction harness. GPT 5.5 Pro later closed the review-console/admin lane for local-preview only. |
| 230 - Release automation internal proxy remediation | Done | `SUB-081` through `SUB-083` fixed reviewer artifact inventory, dispatch pointer validation, and release-automation transcript coverage. GPT 5.5 Pro later closed the release/evidence automation lane for local-preview review automation only. |
| 231 - Review console source-review bundle | Done | `make review-console-source-review-bundle` builds the focused review-console/admin source/test/evidence handoff under ignored `var/review-packets/v0.7/review-console-source-review/`. |
| 232 - Release automation source-review bundle | Done | `make release-automation-source-review-bundle` builds the focused release/evidence automation source/test/evidence handoff under ignored `var/review-packets/v0.7/release-automation-source-review/`. |
| 233 - Review console proxy recheck remediation | Done | `SUB-084` fixed missing-scope patch-apply approvals so malformed patch-apply approvals cannot be approved before binding review. GPT 5.5 Pro recorded no new `EXT-UI-###` findings in the focused source review. |
| 234 - Release automation proxy recheck remediation | Done | `SUB-085` and `SUB-086` fixed release-automation source inventory and transcript documentation freshness for focused handoff packets. GPT 5.5 Pro recorded no new `EXT-REL-###` findings in the focused packet-and-source review. |
| 235 - Review console external closure intake | Done | Source-review closure matrix, lane-status board, and row-partition docs now mark review console/admin closed for the v0.1 local-preview boundary only. |
| 236 - Release automation external closure intake | Done | Source-review closure matrix, lane-status board, and row-partition docs now mark release/evidence automation closed for local-preview review automation only. |
| 237 - v0.8 roadmap prompt prep | Done | [v0.8-roadmap-prompt.md](v0.8-roadmap-prompt.md) asks GPT 5.5 Pro for strategic v0.8 sequencing after focused lane closure, while preserving no-new-powers boundaries. |

## v0.9 Capability Implementation Track

v0.9 begins from the v0.8 product-risk decision and implements only the approved bounded read-only
Git metadata additions recorded below. Broad capability implementation remains blocked.

| Task | Status | Spec |
| --- | --- | --- |
| 238 - git.show.commit_metadata proposal | Done | [capability-proposals/git-show-commit-metadata.md](capability-proposals/git-show-commit-metadata.md), `make git-commit-metadata-proposal-check` |
| 239 - git.show.commit_metadata implementation plan | Done | [capability-implementation-plans/git-show-commit-metadata.md](capability-implementation-plans/git-show-commit-metadata.md), `make git-commit-metadata-implementation-plan-check` |
| 240 - git.show.commit_metadata implementation | Done | [v0.9-git-commit-metadata-implementation.md](v0.9-git-commit-metadata-implementation.md), `make git-commit-metadata-implementation-gate` |
| 241 - git.show.commit_metadata source-review handoff | Done | [v0.9-git-commit-metadata-source-review.md](v0.9-git-commit-metadata-source-review.md), `make git-commit-metadata-source-review-bundle` |
| 242 - git.show.commit_metadata internal lane closure | Done | [v0.9-lane-closure-summary.md](v0.9-lane-closure-summary.md); internal xhigh review/remediation is sufficient to continue local-preview development for this bounded read-only lane. |
| 243 - Next read-only capability seed | Done | [v0.9-next-read-only-capability-seed.md](v0.9-next-read-only-capability-seed.md); planning only, no runtime behavior. |
| 244 - git.show.ref_summary proposal | Done | [capability-proposals/git-show-ref-summary.md](capability-proposals/git-show-ref-summary.md), [v0.9-git-ref-summary-proposal-review.md](v0.9-git-ref-summary-proposal-review.md), `make git-ref-summary-proposal-check`; historical proposal lineage for the later bounded implementation. |
| 245 - git.show.ref_summary implementation plan | Done | [capability-implementation-plans/git-show-ref-summary.md](capability-implementation-plans/git-show-ref-summary.md), `make git-ref-summary-implementation-plan-check`; historical implementation-planning lineage for the later bounded implementation. |
| 246 - Read-only metadata expansion hardening | Done | [read-only-local-metadata-contract.md](read-only-local-metadata-contract.md), [metadata-privacy-policy.md](metadata-privacy-policy.md), [read-only-metadata-capability-checklist.md](read-only-metadata-capability-checklist.md), [read-only-capability-source-review-template.md](read-only-capability-source-review-template.md), [v3-readiness-debt-register.md](v3-readiness-debt-register.md), `make read-only-metadata-capability-check`; no runtime behavior. |
| 247 - git.show.ref_summary implementation | Done | `git.show.ref_summary` is implemented as a bounded read-only local Git metadata tool with no raw ref names, no stable ref-name hashes, no file contents, no shell, no remote refs, and no broader Git mutation powers. |
| 248 - git.show.ref_summary source-review handoff | Done | [v0.9-git-ref-summary-implementation.md](v0.9-git-ref-summary-implementation.md), [v0.9-git-ref-summary-source-review.md](v0.9-git-ref-summary-source-review.md), `make git-ref-summary-implementation-gate`, and `make git-ref-summary-source-review-bundle`. |
| 249 - Read-only capability inventory | Done | [read-only-capability-inventory.md](read-only-capability-inventory.md), `make read-only-capability-inventory-gate`; validates the approved bounded metadata tool inventory and release-check wiring. |
| 250 - v3 next capability candidate evaluation | Done | [v3-next-capability-candidate-evaluation.md](v3-next-capability-candidate-evaluation.md), `make v3-next-capability-candidate-check`; selects `project.manifest.summary` as design-only candidate with implementation blocked. |
| 251 - project.manifest.summary proposal | Done | [capability-proposals/project-manifest-summary.md](capability-proposals/project-manifest-summary.md), `make project-manifest-summary-proposal-check`; design-only, no runtime behavior. |
| 252 - project.manifest.summary implementation plan | Done | [capability-implementation-plans/project-manifest-summary.md](capability-implementation-plans/project-manifest-summary.md), `make project-manifest-summary-implementation-plan-check`; implementation-planning only, no runtime behavior. |
| 253 - project.manifest.summary implementation gate | Done | [v3-project-manifest-summary-implementation.md](v3-project-manifest-summary-implementation.md), `make project-manifest-summary-implementation-gate`; records and validates the bounded read-only implementation boundary. |
| 254 - project.manifest.summary implementation | Done | `project.manifest.summary` is implemented as a bounded read-only local project manifest metadata tool with no file contents, dependency names, script values, package-manager execution, registry/network access, recursive discovery, or broad filesystem powers. |
| 255 - project.manifest.summary source-review handoff | Done | [v3-project-manifest-summary-source-review.md](v3-project-manifest-summary-source-review.md), `make project-manifest-summary-source-review-bundle`; prepares the focused source/test/evidence handoff for review. |
| 256 - project.manifest.summary local lane closure | Done | [v3-project-manifest-summary-source-review.md](v3-project-manifest-summary-source-review.md); local Codex source inspection and focused gates found no blocking issues for continued local-preview development. |
| 257 - Agent Run model contract | Done | [agent-run-model-contract.md](agent-run-model-contract.md); defines read-only run/session observability boundaries and non-claims. |
| 258 - Agent Run records and admin APIs | Done | `AgentRunStore`, `GET /runs`, and `GET /runs/{run_id}` add durable local run correlation without new execution controls or tool powers. |
| 259 - Agent Run review-console panel | Done | Review console shows recent runs and a safe correlated audit timeline; UI tests cover the panel through the existing interaction harness. |
| 260 - Next capability readiness gate | Done | [next-capability-readiness.md](next-capability-readiness.md), `make next-capability-readiness`; validates the current bounded metadata inventory and preflight requirements before selecting or implementing another capability. |
| 261 - Agent Run evidence contract | Done | [agent-run-evidence-contract.md](agent-run-evidence-contract.md), `make agent-run-evidence-contract-check`; defines secret-free run timeline evidence fields without new runtime behavior. |
| 262 - Sandbox workspace boundary contract | Done | [sandbox-workspace-boundary-contract.md](sandbox-workspace-boundary-contract.md); defines operator-managed sandbox/workspace posture evidence without sandbox orchestration. |
| 263 - SIEM-shaped evidence design | Done | [siem-shaped-evidence-design.md](siem-shaped-evidence-design.md), `make siem-evidence-design-check`; defines future JSONL/SIEM-shaped evidence categories without adapters or hosted telemetry. |
| 264 - Observability readiness gate | Done | [observability-readiness-gate.md](observability-readiness-gate.md), `make observability-readiness`; composes Agent Run, sandbox/workspace, SIEM-shaped evidence, next-capability, and no-new-powers checks. |
| 265 - Data classification proposal | Done | [data-classification-design.md](data-classification-design.md), `make data-classification-design-check`; defines trusted local labels as future policy inputs/UI warnings without discovery or runtime behavior. |
| 266 - Control mapping design | Done | [control-mapping-design.md](control-mapping-design.md), `make control-mapping-design-check`; defines control mapping support without compliance automation or new runtime behavior. |
| 267 - Incident reconstruction guide | Done | [incident-reconstruction-guide.md](incident-reconstruction-guide.md), `make incident-reconstruction-check`; documents how to reconstruct Ithildin-mediated actions without claiming proof outside Ithildin. |
| 268 - Observability control packet | Done | `make observability-control-packet`; generates an ignored design-review packet for Agent Run, sandbox/workspace, SIEM-shaped evidence, data classification, control mapping, and incident reconstruction artifacts. |
| 269 - Control mapping readiness gate | Done | [control-mapping-readiness-gate.md](control-mapping-readiness-gate.md), `make control-mapping-readiness`; composes observability, classification, mapping, reconstruction, no-new-powers, and tool-surface checks into `release-check`. |
| 270 - Agent Run timeline packet | Done | `make agent-run-timeline-packet`; generates an ignored source/evidence review packet for Agent Run store/API, governed-call correlation, MCP wiring, UI panel, tests, and contracts. |
| 271 - Agent Run timeline readiness gate | Done | [agent-run-timeline-readiness-gate.md](agent-run-timeline-readiness-gate.md), `make agent-run-timeline-readiness`; validates run store/API/UI timeline evidence and release-check wiring without run-control behavior. |
| 272 - Operator action states design | Done | [operator-action-states-design.md](operator-action-states-design.md), `make operator-action-states-check`; defines future pause/abort/disable vocabulary without runtime controls. |
| 273 - Dashboard evidence review checklist | Done | [dashboard-evidence-review-checklist.md](dashboard-evidence-review-checklist.md), `make dashboard-evidence-checklist-check`; defines operator-facing Agent Run/timeline/approval/diagnostic evidence review expectations without UI behavior changes. |
| 274 - Agent Run dashboard readiness wiring | Done | `make agent-run-timeline-readiness` and `make release-check`; composes operator-action and dashboard-evidence checks into the Agent Run timeline readiness gate. |
| 275 - Agent Run evidence export design | Done | [agent-run-evidence-export-design.md](agent-run-evidence-export-design.md), `make agent-run-evidence-export-check`; defines a future secret-free run export bundle without runtime export behavior. |
| 276 - Agent Run evidence review packet | Done | `make agent-run-evidence-packet`; generates an ignored source/test/contract/evidence packet for the design-only run export surface. |
| 277 - Agent Run evidence readiness gate | Done | [agent-run-evidence-readiness-gate.md](agent-run-evidence-readiness-gate.md), `make agent-run-evidence-readiness`; composes Agent Run evidence/export, timeline, incident reconstruction, dashboard evidence, and no-new-powers checks. |
| 278 - Agent Run evidence export implementation plan | Done | [agent-run-evidence-export-implementation-plan.md](agent-run-evidence-export-implementation-plan.md), `make agent-run-evidence-export-plan-check`; plans endpoint/schema/fixtures/negative cases without approving runtime implementation. |
| 279 - Agent Run evidence export endpoint | Done | [agent-run-evidence-export-implementation.md](agent-run-evidence-export-implementation.md), `make agent-run-evidence-export-implementation-gate`; adds bounded admin-only read export for one secret-free Agent Run evidence bundle. |
| 280 - Agent Run operations dashboard | Done | [agent-run-operations-readiness-gate.md](agent-run-operations-readiness-gate.md), `make agent-run-operations-readiness`; adds bounded read-only `/runs` filters/summaries and review-console operations evidence without run controls. |
| 281 - Operator-managed sandbox demo guide | Done | [operator-managed-sandbox-demo-guide.md](operator-managed-sandbox-demo-guide.md); documents the workbench demo flow around operator-managed workspace/sandbox posture without sandbox lifecycle control. |
| 282 - Operator sandbox demo readiness gate | Done | `make operator-sandbox-demo-readiness`; validates the operator-managed sandbox/workbench demo guide, demo scenario pack, no-new-powers, and tool-surface wiring without sandbox orchestration. |
| 283 - Operator sandbox demo packet | Done | `make operator-sandbox-demo-packet`; generates an ignored guide/contract/scenario/evidence review packet for the operator-managed sandbox/workbench demo boundary. |
| 284 - Operator sandbox demo smoke evidence | Done | `make operator-sandbox-demo-smoke` and `make operator-sandbox-dashboard-checklist`; generate secret-free smoke/checklist artifacts that are copied into the operator sandbox demo packet. |
| 285 - Agent Run correlation smoke | Done | `make agent-run-correlation-smoke`; generates a secret-free transcript mapping mediated actions across run, tool-call, policy, approval, audit, diagnostics, and export evidence. |
| 286 - Agent Run correlation packet | Done | `make agent-run-correlation-packet`; bundles Agent Run contracts, source pointers, smoke evidence, and command evidence for correlation review. |
| 287 - Live demo preflight | Done | `make live-demo-preflight`; validates secret-free local demo posture, loopback Compose bindings, no Docker socket mount, tool count, and no-new-powers evidence without starting services. |
| 288 - Live demo packet | Done | [live-demo-runbook.md](live-demo-runbook.md), `make live-demo-packet`; bundles preflight, operator sandbox demo, Agent Run correlation, and no-new-powers evidence for local demo handoff. |
| 289 - Live demo smoke evidence | Done | `make live-demo-smoke`; generates a secret-free live-demo smoke transcript copied into the live-demo packet without starting services. |
| 290 - Live demo operator status | Done | `make live-demo-status`; prints read-only demo status and writes `LIVE_DEMO_INDEX.md` with artifact paths, localhost reachability, next actions, and cleanup reminders. |
| 291 - Live demo evidence summary | Done | `make live-demo-evidence-summary`; generates a secret-free digest of live-demo status, smoke evidence, signed fixture evidence, negative transcripts, Agent Run correlation, operator sandbox packet, and consolidated handoff artifact presence. |
| 292 - Operator workbench readiness | Done | [operator-workbench-readiness.md](operator-workbench-readiness.md), `make workbench-readiness`; validates the read-only local operator workbench surface, docs, evidence packet wiring, and no-new-powers posture. |
| 293 - Operator workbench evidence packet | Done | `make workbench-evidence-packet`; generates a focused ignored operator workbench packet tying Agent Runs, approval evidence, audit status, live-demo artifacts, sandbox/workspace posture, and handoff pointers together. |
| 294 - Evidence-only workbench wrapper | Done | `make demo-workbench`; runs the read-only/ignored-output workbench evidence sequence without starting services, calling governed tools, approving actions, or adding run/sandbox controls. |
| 295 - Workbench demo smoke v2 | Done | `make demo-workbench-smoke`; generates a deterministic secret-free operator-flow transcript with preflight, optional Compose/MCP/demo-flow steps, evidence export, and cleanup guidance. |
| 296 - Workbench demo index v2 | Done | `WORKBENCH_DEMO_INDEX.md`; generated by `make workbench-evidence-packet` as the first file to open, with reading order and artifact hashes. |
| 297 - Workbench demo UX polish | Done | Review console Agent Runs now include a `Demo Path` guide and grouped run evidence overview while preserving read-only, no-run-control behavior. |
| 298 - Demo readiness summary | Done | `make demo-readiness-summary`; generates a secret-free ready/missing/optional/deferred operator demo digest without starting services or calling governed tools. |
| 299 - Workbench happy path story | Done | `07_WORKBENCH_DEMO_STORY.md`; generated in the workbench packet as a preflight-to-cleanup narrative without runtime fixture loading. |
| 300 - Operator demo guide | Done | `make operator-demo-guide`; generates a secret-free preflight-to-cleanup operator stage table and bundles it into the workbench packet without starting services or adding runtime controls. |
| 301 - Guided demo state report | Done | `make demo-state-report`; generates `DEMO_STATE_REPORT.md` with seed status, localhost reachability, warnings, artifact paths, and next demo commands without governed tool calls. |
| 302 - Guided demo wrapper | Done | `make guided-demo` and `make guided-demo-readiness`; refresh the non-service-starting local demo evidence path, transcript, packet wiring, and no-new-powers gate. |
| 303 - Demo flow result summary | Done | `make demo-flow`; writes `DEMO_FLOW_RESULT.md` with proposal, approval, candidate run ID, audit verification, export pointer, and reset guidance after the optional mediated local demo. |
| 304 - Demo reset guide | Done | `make demo-reset-guide`; writes `DEMO_RESET_GUIDE.md` with read-only repeat/recovery guidance and no automatic repair, rollback, cleanup, or sandbox control. |
| 305 - Demo flow readiness gate | Done | [demo-flow-readiness.md](demo-flow-readiness.md), `make demo-flow-readiness`; validates demo result/reset artifacts, UI demo labels, workbench packet wiring, and no-new-powers posture. |
| 306 - Demo flow result checker | Done | `make demo-flow-result-check`; validates `DEMO_FLOW_RESULT.md` when present and passes with `not_run` status when the optional mediated local demo has not been executed. |
| 307 - Demo evidence closure packet | Done | [demo-evidence-closure.md](demo-evidence-closure.md), `make demo-evidence-packet`; bundles demo readiness, state, reset, artifact pointers, result-check output, and hashes. |
| 308 - Demo evidence readiness gate | Done | `make demo-evidence-readiness`; validates demo evidence packet/docs/review-candidate/release-check wiring while preserving the no-new-powers boundary. |
| 309 - Operator demo walkthrough | Done | [operator-demo-walkthrough.md](operator-demo-walkthrough.md), `make demo-operator-walkthrough`; generates the front-door expected screens, evidence files, next human steps, and reset guidance without starting services or adding runtime controls. |
| 310 - Read-only project intelligence consolidation | Done | [read-only-project-intelligence.md](read-only-project-intelligence.md), `make read-only-project-intelligence`; records the four-tool project intelligence slice, selects `project.structure.summary` for design-only review, and preserves no-new-powers boundaries. |
| 311 - project.structure.summary design selection | Done | [v3-project-structure-summary-selection.md](v3-project-structure-summary-selection.md), [capability-proposals/project-structure-summary.md](capability-proposals/project-structure-summary.md), `make project-structure-summary-proposal-check`; design-only, implementation blocked. |
| 312 - project.structure.summary implementation plan | Done | [capability-implementation-plans/project-structure-summary.md](capability-implementation-plans/project-structure-summary.md), `make project-structure-summary-implementation-plan-check`; implementation-planning only, runtime blocked. |

## Future Candidate Track

| Area | Status | Notes |
| --- | --- | --- |
| Agent run observability | Operations dashboard done | [agent-run-model-contract.md](agent-run-model-contract.md) records the implemented run/session evidence, bounded run filters/summaries, timeline dashboard, and run evidence export foundation. |
| Sandbox boundary and SIEM-shaped evidence | Roadmap | [agent-run-observability-and-sandbox-roadmap.md](agent-run-observability-and-sandbox-roadmap.md) records the next strategic direction: operator-managed sandbox contracts, SIEM-shaped export design, data classification, and control mapping without claiming current sandbox/SIEM/compliance behavior. |
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
