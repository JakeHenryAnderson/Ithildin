COMPOSE ?= docker compose
COMPOSE_FILE ?= deploy/docker-compose.yml
COMPOSE_ENV_FILE ?= $(shell if [ -f .env ]; then echo .env; else echo .env.example; fi)

.PHONY: accepted-risk-register-check admin-token-generate adversarial-corpus-check agent-run-correlation-packet agent-run-correlation-smoke agent-run-evidence-contract-check agent-run-evidence-export-check agent-run-evidence-export-implementation-gate agent-run-evidence-export-plan-check agent-run-evidence-packet agent-run-evidence-readiness agent-run-operations-readiness agent-run-timeline-packet agent-run-timeline-readiness agent-workflow-check audit-diagnostics audit-export-verify audit-keygen capability-decision-report capability-expansion-gate clean closure-matrix-evidence-sync compose-config compose-down compose-logs compose-smoke compose-up control-mapping-design-check control-mapping-readiness dashboard-evidence-checklist-check data-classification-design-check demo-evidence-packet demo-evidence-readiness demo-flow demo-flow-readiness demo-flow-result-check demo-observed-summary demo-operator-walkthrough demo-readiness-summary demo-reset-guide demo-scenario-pack demo-seed demo-workbench demo-workbench-smoke determinism-check docs-site enterprise-readiness-runway-check evidence-confusion-gate evidence-contracts-check external-findings-intake-dry-run external-response-normalize external-response-template-check external-review-closure-gate filesystem-contract-check filesystem-source-review-bundle git-commit-metadata-implementation-gate git-commit-metadata-implementation-plan-check git-commit-metadata-proposal-check git-commit-metadata-source-review-bundle git-ref-summary-implementation-gate git-ref-summary-implementation-plan-check git-ref-summary-proposal-check git-ref-summary-source-review-bundle http-fetch-source-review-bundle incident-reconstruction-check internal-review-packet lint live-demo-evidence-summary live-demo-packet live-demo-preflight live-demo-smoke live-demo-status local-model-demo local-prompt-triage low-implementer-delegation-check low-implementer-delegation-packet low-implementer-ticket-catalog-check mcp-ingress-source-review-bundle mcp-inspector-recipes manifest-change-review manifest-lock manifest-lock-check manifest-lock-keygen manifest-lock-sign manifest-lock-signature-check negative-review-transcripts next-capability-candidate-evaluation-2-check next-capability-readiness no-new-powers-guardrail observability-control-packet observability-readiness ollama-smoke operator-action-states-check operator-sandbox-dashboard-checklist operator-sandbox-demo-packet operator-sandbox-demo-readiness operator-sandbox-demo-smoke packet-redaction-scan policy-parity policy-registry-source-review-bundle policy-test project-ci-summary-design-review-packet project-ci-summary-implementation-gate project-ci-summary-implementation-plan-check project-ci-summary-proposal-check project-ci-summary-source-review-bundle project-config-summary-implementation-gate project-config-summary-implementation-plan-check project-config-summary-proposal-check project-config-summary-source-review-bundle project-dependency-summary-design-review-packet project-dependency-summary-implementation-gate project-dependency-summary-implementation-plan-check project-dependency-summary-proposal-check project-dependency-summary-source-review-bundle project-docs-summary-design-review-packet project-docs-summary-implementation-gate project-docs-summary-implementation-plan-check project-docs-summary-proposal-check project-docs-summary-source-review-bundle project-language-summary-design-review-packet project-language-summary-implementation-gate project-language-summary-implementation-plan-check project-language-summary-proposal-check project-language-summary-source-review-bundle project-manifest-summary-implementation-gate project-manifest-summary-implementation-plan-check project-manifest-summary-proposal-check project-manifest-summary-source-review-bundle project-release-summary-design-review-packet project-release-summary-implementation-gate project-release-summary-implementation-plan-check project-release-summary-preimplementation-check project-release-summary-proposal-check project-release-summary-transition-check project-structure-summary-design-review-packet project-structure-summary-implementation-gate project-structure-summary-implementation-plan-check project-structure-summary-proposal-check project-structure-summary-source-review-bundle project-test-summary-design-review-packet project-test-summary-implementation-gate project-test-summary-implementation-plan-check project-test-summary-proposal-check project-test-summary-source-review-bundle read-only-capability-inventory-gate read-only-metadata-capability-check read-only-project-intelligence release-automation-source-review-bundle release-check release-context release-evidence release-evidence-gate release-evidence-validate release-guardrails release-packet resource-limit-check review-candidate review-console-source-review-bundle review-findings-summary review-findings-summary-write review-packet-bundle review-packet-consolidated review-packet-diff review-packet-diff-gate review-packet-source-pointers review-run-manifest-check review-run-manifest-refresh reviewer-artifact-manifest reviewer-findings-check siem-evidence-design-check signed-evidence-demo signed-evidence-demo-verify signed-evidence-source-review-bundle source-review-transcript-packet test tool-surface-invariant-gate typecheck ui-dev ui-test v04-review-packet v05-boundary-decision-draft-check v05-handoff-packet-check v05-review-candidate v05-threat-model-delta-check v06-closure-readiness v06-final-handoff v06-lane-status v06-lane-status-write v06-patch-apply-review-packet v06-review-dispatch-packets v07-closure-prep v07-patch-apply-recheck-prep v08-capability-design-gate v08-final-decision-packet v08-public-preview-decision v08-status-reconciliation v09-design-only-gate v09-design-review-packet v1-rc-roadmap-check v1-rc-status-check v1-operator-quickstart-check v1-workbench-evidence-check v1-assurance-closure-check v1-rc-readiness v1-rc-packet v3-next-capability-candidate-check workbench-evidence-packet workbench-readiness
.PHONY: governed-artifact-transfer-lab governed-artifact-transfer-lab-check governed-artifact-transfer-stage2 governed-artifact-transfer-stage2-check hello-world-sandbox-demo-packet hello-world-sandbox-demo-packet-check hello-world-sandbox-demo-check hello-world-sandbox-observed-demo hello-world-sandbox-observed-demo-check hello-world-mission-control-handoff hello-world-mission-control-handoff-check sandbox-promotion-evidence-contract-check sandbox-artifact-observed-demo sandbox-artifact-observed-demo-check sandbox-artifact-write-text-preimplementation-check sandbox-artifact-write-text-implementation-gate sandbox-artifact-write-text-negative-transcripts sandbox-artifact-write-text-source-review-bundle

test:
	uv run pytest

determinism-check:
	uv run python scripts/test_determinism_gate.py

adversarial-corpus-check:
	uv run python scripts/adversarial_corpus_check.py

resource-limit-check:
	uv run python scripts/resource_limit_check.py

capability-expansion-gate:
	uv run python scripts/capability_expansion_gate.py

capability-decision-report:
	uv run python scripts/capability_decision_report.py

no-new-powers-guardrail:
	uv run python scripts/no_new_powers_guardrail.py

read-only-metadata-capability-check:
	uv run python scripts/read_only_metadata_capability_check.py

read-only-capability-inventory-gate:
	uv run python scripts/read_only_capability_inventory_gate.py

read-only-project-intelligence:
	uv run python scripts/project_intelligence_readiness.py

v3-next-capability-candidate-check:
	uv run python scripts/v3_next_capability_candidate_check.py

next-capability-readiness:
	uv run python scripts/next_capability_readiness.py

next-capability-candidate-evaluation-2-check:
	uv run python scripts/next_capability_candidate_evaluation_2_check.py

v1-rc-roadmap-check:
	uv run python scripts/v1_rc_roadmap_check.py

v1-rc-status-check:
	uv run python scripts/v1_rc_status_check.py

v1-operator-quickstart-check:
	uv run python scripts/v1_operator_quickstart_check.py

v1-workbench-evidence-check:
	uv run python scripts/v1_workbench_evidence_check.py

v1-assurance-closure-check:
	uv run python scripts/v1_assurance_closure_check.py

v1-rc-readiness:
	uv run python scripts/v1_rc_readiness_check.py

v1-rc-packet:
	uv run python scripts/v1_rc_packet.py

enterprise-readiness-runway-check:
	uv run python scripts/enterprise_readiness_runway_check.py

agent-run-correlation-smoke:
	uv run python scripts/agent_run_correlation_smoke.py

agent-run-correlation-packet:
	uv run python scripts/agent_run_correlation_packet.py

agent-run-evidence-contract-check:
	uv run python scripts/agent_run_evidence_contract_check.py

agent-run-evidence-export-check:
	uv run python scripts/agent_run_evidence_export_check.py

agent-run-evidence-export-plan-check:
	uv run python scripts/agent_run_evidence_export_plan_check.py

agent-run-evidence-export-implementation-gate:
	uv run python scripts/agent_run_evidence_export_implementation_gate.py

agent-run-evidence-packet:
	uv run python scripts/agent_run_evidence_packet.py

agent-run-evidence-readiness:
	uv run python scripts/agent_run_evidence_readiness.py

agent-run-operations-readiness:
	uv run python scripts/agent_run_operations_readiness.py

agent-run-timeline-packet:
	uv run python scripts/agent_run_timeline_packet.py

agent-run-timeline-readiness:
	uv run python scripts/agent_run_timeline_readiness.py

agent-workflow-check:
	uv run python scripts/agent_workflow_check.py

low-implementer-delegation-packet:
	uv run python scripts/low_implementer_delegation_packet.py

low-implementer-delegation-check:
	uv run python scripts/low_implementer_delegation_packet.py --check

low-implementer-ticket-catalog-check:
	uv run python scripts/low_implementer_delegation_packet.py --check

workbench-readiness:
	uv run python scripts/workbench_readiness.py

workbench-evidence-packet:
	uv run python scripts/workbench_evidence_packet.py

demo-workbench-smoke:
	uv run python scripts/workbench_demo_smoke.py

demo-readiness-summary:
	uv run python scripts/demo_readiness_summary.py

demo-operator-walkthrough:
	uv run python scripts/operator_demo_walkthrough.py

operator-demo-guide:
	uv run python scripts/operator_demo_guide.py

demo-state-report:
	uv run python scripts/demo_state_report.py

guided-demo:
	uv run python scripts/guided_demo.py

guided-demo-readiness:
	uv run python scripts/guided_demo_readiness.py

demo-reset-guide:
	uv run python scripts/demo_reset_guide.py

demo-flow-readiness:
	uv run python scripts/demo_flow_readiness.py

demo-flow-result-check:
	uv run python scripts/demo_flow_result_check.py

demo-observed-summary:
	uv run python scripts/demo_observed_summary.py

demo-evidence-packet:
	uv run python scripts/demo_evidence_packet.py

demo-evidence-readiness:
	uv run python scripts/demo_evidence_readiness.py

governed-artifact-transfer-lab:
	uv run python scripts/governed_artifact_transfer_lab.py

governed-artifact-transfer-lab-check:
	uv run python scripts/governed_artifact_transfer_lab_check.py

governed-artifact-transfer-stage2:
	uv run python scripts/governed_artifact_transfer_lab.py

governed-artifact-transfer-stage2-check:
	uv run python scripts/governed_artifact_transfer_lab_check.py

hello-world-sandbox-demo-packet:
	uv run python scripts/hello_world_sandbox_demo_packet.py --allow-dirty

hello-world-sandbox-demo-packet-check:
	uv run python scripts/hello_world_sandbox_demo_packet_check.py

hello-world-sandbox-demo-check:
	uv run python scripts/hello_world_sandbox_demo_check.py

hello-world-sandbox-observed-demo:
	uv run python scripts/hello_world_sandbox_observed_demo.py

hello-world-sandbox-observed-demo-check:
	uv run python scripts/hello_world_sandbox_observed_demo_check.py

hello-world-mission-control-handoff:
	uv run python scripts/hello_world_mission_control_handoff.py

hello-world-mission-control-handoff-check:
	uv run python scripts/hello_world_mission_control_handoff_check.py

sandbox-promotion-evidence-contract-check:
	uv run python scripts/sandbox_promotion_evidence_contract_check.py

sandbox-artifact-observed-demo:
	uv run python scripts/sandbox_artifact_observed_demo.py

sandbox-artifact-observed-demo-check:
	uv run python scripts/sandbox_artifact_observed_demo_check.py

sandbox-artifact-write-text-preimplementation-check:
	uv run python scripts/sandbox_artifact_write_text_preimplementation_check.py

sandbox-artifact-write-text-implementation-gate:
	uv run python scripts/sandbox_artifact_write_text_implementation_gate.py

sandbox-artifact-write-text-negative-transcripts:
	uv run python scripts/sandbox_artifact_write_text_negative_transcripts.py

sandbox-artifact-write-text-source-review-bundle:
	uv run python scripts/sandbox_artifact_write_text_source_review_bundle.py

demo-workbench:
	$(MAKE) live-demo-preflight
	$(MAKE) live-demo-status
	$(MAKE) live-demo-smoke
	$(MAKE) sandbox-artifact-observed-demo
	$(MAKE) hello-world-sandbox-observed-demo
	$(MAKE) hello-world-mission-control-handoff
	$(MAKE) sandbox-promotion-evidence-contract-check
	$(MAKE) live-demo-evidence-summary
	$(MAKE) demo-state-report
	$(MAKE) demo-observed-summary
	$(MAKE) demo-operator-walkthrough
	$(MAKE) operator-demo-guide
	$(MAKE) demo-reset-guide
	$(MAKE) demo-workbench-smoke
	$(MAKE) demo-readiness-summary
	$(MAKE) operator-sandbox-demo-packet
	$(MAKE) agent-run-correlation-packet
	$(MAKE) workbench-evidence-packet
	$(MAKE) demo-evidence-packet

operator-action-states-check:
	uv run python scripts/operator_action_states_check.py

dashboard-evidence-checklist-check:
	uv run python scripts/dashboard_evidence_checklist_check.py

siem-evidence-design-check:
	uv run python scripts/siem_evidence_design_check.py

data-classification-design-check:
	uv run python scripts/data_classification_design_check.py

control-mapping-design-check:
	uv run python scripts/control_mapping_design_check.py

incident-reconstruction-check:
	uv run python scripts/incident_reconstruction_check.py

observability-control-packet:
	uv run python scripts/observability_control_packet.py

observability-readiness:
	uv run python scripts/observability_readiness.py

control-mapping-readiness:
	uv run python scripts/control_mapping_readiness.py

operator-sandbox-demo-readiness:
	uv run python scripts/operator_sandbox_demo_readiness.py

operator-sandbox-demo-smoke:
	uv run python scripts/operator_sandbox_demo_smoke.py

operator-sandbox-dashboard-checklist:
	uv run python scripts/operator_sandbox_dashboard_checklist.py

operator-sandbox-demo-packet:
	uv run python scripts/operator_sandbox_demo_packet.py

live-demo-preflight:
	uv run python scripts/live_demo_preflight.py

live-demo-status:
	uv run python scripts/live_demo_status.py

live-demo-smoke:
	uv run python scripts/live_demo_smoke.py

live-demo-evidence-summary:
	uv run python scripts/live_demo_evidence_summary.py

live-demo-packet:
	uv run python scripts/live_demo_packet.py

project-manifest-summary-proposal-check:
	uv run python scripts/project_manifest_summary_proposal_check.py

project-manifest-summary-implementation-plan-check:
	uv run python scripts/project_manifest_summary_implementation_plan_check.py

project-manifest-summary-implementation-gate:
	uv run python scripts/project_manifest_summary_implementation_gate.py

project-manifest-summary-source-review-bundle:
	uv run python scripts/project_manifest_summary_source_review_bundle.py

project-dependency-summary-proposal-check:
	uv run python scripts/project_dependency_summary_proposal_check.py

project-dependency-summary-implementation-plan-check:
	uv run python scripts/project_dependency_summary_implementation_plan_check.py

project-dependency-summary-design-review-packet:
	uv run python scripts/project_dependency_summary_design_review_packet.py

project-dependency-summary-implementation-gate:
	uv run python scripts/project_dependency_summary_implementation_gate.py

project-dependency-summary-source-review-bundle:
	uv run python scripts/project_dependency_summary_source_review_bundle.py

project-structure-summary-proposal-check:
	uv run python scripts/project_structure_summary_proposal_check.py

project-structure-summary-implementation-plan-check:
	uv run python scripts/project_structure_summary_implementation_plan_check.py

project-structure-summary-implementation-gate:
	uv run python scripts/project_structure_summary_implementation_gate.py

project-structure-summary-source-review-bundle:
	uv run python scripts/project_structure_summary_source_review_bundle.py

project-structure-summary-design-review-packet:
	uv run python scripts/project_structure_summary_design_review_packet.py

project-test-summary-proposal-check:
	uv run python scripts/project_test_summary_proposal_check.py

project-test-summary-implementation-plan-check:
	uv run python scripts/project_test_summary_implementation_plan_check.py

project-test-summary-implementation-gate:
	uv run python scripts/project_test_summary_implementation_gate.py

project-test-summary-source-review-bundle:
	uv run python scripts/project_test_summary_source_review_bundle.py

project-test-summary-design-review-packet:
	uv run python scripts/project_test_summary_design_review_packet.py

project-docs-summary-proposal-check:
	uv run python scripts/project_docs_summary_proposal_check.py

project-docs-summary-implementation-plan-check:
	uv run python scripts/project_docs_summary_implementation_plan_check.py

project-docs-summary-implementation-gate:
	uv run python scripts/project_docs_summary_implementation_gate.py

project-docs-summary-design-review-packet:
	uv run python scripts/project_docs_summary_design_review_packet.py

project-docs-summary-source-review-bundle:
	uv run python scripts/project_docs_summary_source_review_bundle.py

project-language-summary-proposal-check:
	uv run python scripts/project_language_summary_proposal_check.py

project-language-summary-implementation-plan-check:
	uv run python scripts/project_language_summary_implementation_plan_check.py

project-language-summary-implementation-gate:
	uv run python scripts/project_language_summary_implementation_gate.py

project-language-summary-design-review-packet:
	uv run python scripts/project_language_summary_design_review_packet.py

project-language-summary-source-review-bundle:
	uv run python scripts/project_language_summary_source_review_bundle.py

project-config-summary-proposal-check:
	uv run python scripts/project_config_summary_proposal_check.py

project-config-summary-implementation-plan-check:
	uv run python scripts/project_config_summary_implementation_plan_check.py

project-config-summary-implementation-gate:
	uv run python scripts/project_config_summary_implementation_gate.py

project-config-summary-source-review-bundle:
	uv run python scripts/project_config_summary_source_review_bundle.py

project-ci-summary-proposal-check:
	uv run python scripts/project_ci_summary_proposal_check.py

project-ci-summary-implementation-plan-check:
	uv run python scripts/project_ci_summary_implementation_plan_check.py

project-ci-summary-implementation-gate:
	uv run python scripts/project_ci_summary_implementation_gate.py

project-ci-summary-design-review-packet:
	uv run python scripts/project_ci_summary_design_review_packet.py

project-ci-summary-source-review-bundle:
	uv run python scripts/project_ci_summary_source_review_bundle.py

project-release-summary-proposal-check:
	uv run python scripts/project_release_summary_proposal_check.py

project-release-summary-implementation-plan-check:
	uv run python scripts/project_release_summary_implementation_plan_check.py

project-release-summary-preimplementation-check:
	uv run python scripts/project_release_summary_preimplementation_check.py

project-release-summary-implementation-gate:
	uv run python scripts/project_release_summary_implementation_gate.py

project-release-summary-transition-check:
	uv run python scripts/project_release_summary_transition_check.py

project-release-summary-review-handoff-check:
	uv run python scripts/project_release_summary_review_handoff_check.py

project-release-summary-design-review-packet:
	uv run python scripts/project_release_summary_design_review_packet.py --allow-dirty

project-release-summary-source-review-bundle:
	uv run python scripts/project_release_summary_source_review_bundle.py --allow-dirty

project-risk-summary-proposal-check:
	uv run python scripts/project_risk_summary_proposal_check.py

project-risk-summary-implementation-plan-check:
	uv run python scripts/project_risk_summary_implementation_plan_check.py

project-risk-summary-implementation-gate:
	uv run python scripts/project_risk_summary_implementation_gate.py

project-risk-summary-preimplementation-check:
	uv run python scripts/project_risk_summary_preimplementation_check.py

project-risk-summary-review-handoff-check:
	uv run python scripts/project_risk_summary_review_handoff_check.py

project-risk-summary-design-review-packet:
	uv run python scripts/project_risk_summary_design_review_packet.py --allow-dirty

project-risk-summary-source-review-bundle:
	uv run python scripts/project_risk_summary_source_review_bundle.py --allow-dirty

tool-surface-invariant-gate:
	uv run python scripts/tool_surface_invariant_gate.py

evidence-confusion-gate:
	uv run python scripts/evidence_confusion_gate.py

external-review-closure-gate:
	uv run python scripts/external_review_closure_gate.py

closure-matrix-evidence-sync:
	uv run python scripts/closure_matrix_evidence_sync.py

accepted-risk-register-check:
	uv run python scripts/accepted_risk_register.py

evidence-contracts-check:
	uv run python scripts/evidence_contracts_check.py

lint:
	uv run ruff check .

manifest-lock:
	uv run python scripts/manifest_lock.py

manifest-lock-check:
	uv run python scripts/manifest_lock.py --check

manifest-change-review:
	uv run python scripts/manifest_change_review.py

manifest-lock-keygen:
	uv run python scripts/manifest_lock_signing.py keygen

manifest-lock-sign:
	uv run python scripts/manifest_lock_signing.py sign

manifest-lock-signature-check:
	uv run python scripts/manifest_lock_signing.py verify

admin-token-generate:
	uv run python scripts/admin_token.py

audit-keygen:
	uv run python scripts/audit_signing.py keygen

audit-diagnostics:
	uv run python scripts/audit_diagnostics.py

audit-export-verify:
	@test -n "$(FILE)" || (echo "FILE is required, e.g. make audit-export-verify FILE=ithildin-audit-export-signed.json" >&2; exit 1)
	uv run python scripts/audit_signing.py verify "$(FILE)" $(if $(PUBLIC_KEY),--public-key "$(PUBLIC_KEY)",)

filesystem-contract-check:
	uv run python scripts/filesystem_contract_check.py

filesystem-source-review-bundle:
	uv run python scripts/filesystem_source_review_bundle.py

http-fetch-source-review-bundle:
	uv run python scripts/http_fetch_source_review_bundle.py

signed-evidence-source-review-bundle:
	uv run python scripts/signed_evidence_source_review_bundle.py

policy-registry-source-review-bundle:
	uv run python scripts/policy_registry_source_review_bundle.py

mcp-ingress-source-review-bundle:
	uv run python scripts/mcp_ingress_source_review_bundle.py

review-console-source-review-bundle:
	uv run python scripts/review_console_source_review_bundle.py

release-automation-source-review-bundle:
	uv run python scripts/release_automation_source_review_bundle.py

typecheck:
	uv run mypy
	npm run typecheck --prefix apps/ui

ui-test:
	npm run test --prefix apps/ui

release-guardrails:
	uv run python scripts/release_guardrails.py

reviewer-findings-check:
	uv run python scripts/reviewer_findings.py

external-findings-intake-dry-run:
	uv run python scripts/external_findings_intake_dry_run.py

external-response-template-check:
	uv run python scripts/external_response_template_check.py

external-response-normalize:
	@test -n "$(FILE)" || (echo "FILE is required, e.g. make external-response-normalize FILE=raw-response.md REVIEWER='GPT 5.5 Pro' REVIEWER_TYPE=external-model SOURCE_ACCESS=source-level REVIEWED_COMMIT=$$(git rev-parse HEAD) REVIEWED_PACKET_HASH=sha256:... AREA=http-fetch" >&2; exit 1)
	@test -n "$(REVIEWER)" || (echo "REVIEWER is required" >&2; exit 1)
	@test -n "$(REVIEWER_TYPE)" || (echo "REVIEWER_TYPE is required" >&2; exit 1)
	@test -n "$(SOURCE_ACCESS)" || (echo "SOURCE_ACCESS is required" >&2; exit 1)
	@test -n "$(REVIEWED_COMMIT)" || (echo "REVIEWED_COMMIT is required" >&2; exit 1)
	@test -n "$(REVIEWED_PACKET_HASH)" || (echo "REVIEWED_PACKET_HASH is required" >&2; exit 1)
	@test -n "$(AREA)" || (echo "AREA is required" >&2; exit 1)
	uv run python scripts/external_response_normalize.py "$(FILE)" --reviewer "$(REVIEWER)" --reviewer-type "$(REVIEWER_TYPE)" --source-access "$(SOURCE_ACCESS)" --reviewed-commit "$(REVIEWED_COMMIT)" --reviewed-packet-hash "$(REVIEWED_PACKET_HASH)" --area "$(AREA)" $(if $(OUTPUT),--output "$(OUTPUT)",)

v05-threat-model-delta-check:
	uv run python scripts/v05_threat_model_delta_check.py

v05-boundary-decision-draft-check:
	uv run python scripts/v05_boundary_decision_draft_check.py

v05-handoff-packet-check:
	uv run python scripts/v05_handoff_packet_check.py

review-run-manifest-check:
	uv run python scripts/review_run_manifest.py

review-run-manifest-refresh:
	uv run python scripts/review_run_manifest_refresh.py --write
	uv run python scripts/review_run_manifest.py

reviewer-artifact-manifest:
	uv run python scripts/reviewer_artifact_manifest.py

review-findings-summary:
	uv run python scripts/review_findings_collect.py --check

review-findings-summary-write:
	uv run python scripts/review_findings_collect.py

v06-lane-status:
	uv run python scripts/v06_lane_status.py --check

v06-lane-status-write:
	uv run python scripts/v06_lane_status.py

v06-closure-readiness:
	uv run python scripts/v06_closure_readiness.py

v06-final-handoff:
	uv run python scripts/v06_final_handoff.py

v07-closure-prep:
	uv run python scripts/v07_closure_prep.py

v07-patch-apply-recheck-prep:
	uv run python scripts/v07_patch_apply_recheck.py

v08-status-reconciliation:
	uv run python scripts/v08_status_reconciliation.py

v08-public-preview-decision:
	uv run python scripts/v08_public_preview_decision.py

v08-capability-design-gate:
	uv run python scripts/v08_capability_design_gate.py

v08-final-decision-packet:
	uv run python scripts/v08_final_decision_packet.py

v09-design-only-gate:
	uv run python scripts/v09_design_only_gate.py

git-commit-metadata-proposal-check:
	uv run python scripts/git_commit_metadata_proposal_check.py

git-ref-summary-proposal-check:
	uv run python scripts/git_ref_summary_proposal_check.py

git-ref-summary-implementation-plan-check:
	uv run python scripts/git_ref_summary_implementation_plan_check.py

git-ref-summary-implementation-gate:
	uv run python scripts/git_ref_summary_implementation_gate.py

git-ref-summary-source-review-bundle:
	uv run python scripts/git_ref_summary_source_review_bundle.py

git-tag-metadata-proposal-check:
	uv run python scripts/git_tag_metadata_proposal_check.py

git-tag-metadata-implementation-plan-check:
	uv run python scripts/git_tag_metadata_implementation_plan_check.py

git-tag-metadata-implementation-gate:
	uv run python scripts/git_tag_metadata_implementation_gate.py

git-tag-metadata-source-review-bundle:
	uv run python scripts/git_tag_metadata_source_review_bundle.py

git-commit-metadata-implementation-plan-check:
	uv run python scripts/git_commit_metadata_implementation_plan_check.py

git-commit-metadata-implementation-gate:
	uv run python scripts/git_commit_metadata_implementation_gate.py

git-commit-metadata-source-review-bundle:
	uv run python scripts/git_commit_metadata_source_review_bundle.py

v09-design-review-packet:
	uv run python scripts/v09_design_review_packet.py

policy-test:
	uv run python scripts/policy_test.py

policy-parity:
	uv run python scripts/policy_parity.py

release-evidence:
	uv run python scripts/release_evidence.py

release-evidence-gate:
	@TMP_DIR=$$(mktemp -d); \
	TMP_FILE="$$TMP_DIR/release-evidence.json"; \
	trap 'rm -rf "$$TMP_DIR"' EXIT; \
	uv run python scripts/release_evidence.py > "$$TMP_FILE"; \
	uv run python scripts/release_evidence.py --validate-file "$$TMP_FILE"

release-evidence-validate:
	@test -n "$(FILE)" || (echo "FILE is required, e.g. make release-evidence-validate FILE=release-evidence.json" >&2; exit 1)
	uv run python scripts/release_evidence.py --validate-file "$(FILE)"

release-packet:
	uv run python scripts/release_packet.py

v04-review-packet:
	uv run python scripts/v04_review_packet.py

review-packet-bundle:
	uv run python scripts/review_packet_bundle.py

review-packet-consolidated:
	uv run python scripts/consolidate_review_packet.py

review-packet-source-pointers:
	uv run python scripts/review_packet_source_pointers.py

v06-review-dispatch-packets:
	uv run python scripts/external_review_dispatch_packets.py

v06-patch-apply-review-packet:
	uv run python scripts/patch_apply_external_review_packet.py

packet-redaction-scan:
	uv run python scripts/packet_redaction_scan.py

review-packet-diff:
	@test -n "$(OLD)" || (echo "OLD is required, e.g. make review-packet-diff OLD=old-bundle NEW=new-bundle" >&2; exit 1)
	@test -n "$(NEW)" || (echo "NEW is required, e.g. make review-packet-diff OLD=old-bundle NEW=new-bundle" >&2; exit 1)
	uv run python scripts/review_packet_diff.py --old "$(OLD)" --new "$(NEW)"

review-packet-diff-gate:
	@test -n "$(OLD)" || (echo "OLD is required, e.g. make review-packet-diff-gate OLD=old-bundle NEW=new-bundle" >&2; exit 1)
	@test -n "$(NEW)" || (echo "NEW is required, e.g. make review-packet-diff-gate OLD=old-bundle NEW=new-bundle" >&2; exit 1)
	uv run python scripts/review_packet_diff.py --old "$(OLD)" --new "$(NEW)" --gate

review-candidate:
	$(MAKE) release-check
	$(MAKE) filesystem-contract-check
	$(MAKE) signed-evidence-demo
	$(MAKE) signed-evidence-demo-verify
	$(MAKE) negative-review-transcripts
	$(MAKE) operator-sandbox-demo-packet
	$(MAKE) agent-run-correlation-packet
	$(MAKE) live-demo-status
	$(MAKE) live-demo-smoke
	$(MAKE) sandbox-artifact-observed-demo
	$(MAKE) hello-world-sandbox-observed-demo
	$(MAKE) hello-world-mission-control-handoff
	$(MAKE) live-demo-evidence-summary
	$(MAKE) live-demo-packet
	$(MAKE) guided-demo
	$(MAKE) workbench-evidence-packet
	$(MAKE) demo-flow-readiness
	$(MAKE) demo-evidence-packet
	$(MAKE) demo-evidence-readiness
	$(MAKE) governed-artifact-transfer-lab
	$(MAKE) governed-artifact-transfer-lab-check
	$(MAKE) governed-artifact-transfer-stage2
	$(MAKE) governed-artifact-transfer-stage2-check
	$(MAKE) v1-rc-packet
	$(MAKE) v06-review-dispatch-packets
	$(MAKE) review-packet-bundle
	$(MAKE) review-packet-consolidated
	$(MAKE) packet-redaction-scan
	$(MAKE) docs-site
	@echo "Review candidate ready: var/review-packets/v0.2/GPT-5.5-Pro-consolidated"

v05-review-candidate:
	$(MAKE) review-candidate
	$(MAKE) v05-threat-model-delta-check
	$(MAKE) review-packet-source-pointers
	$(MAKE) external-response-template-check
	$(MAKE) v05-boundary-decision-draft-check
	$(MAKE) v05-handoff-packet-check
	$(MAKE) source-review-transcript-packet
	$(MAKE) reviewer-artifact-manifest
	@echo "v0.5 review candidate ready: var/review-packets/v0.2/GPT-5.5-Pro-consolidated and var/review-packets/v0.5"

internal-review-packet:
	uv run python scripts/internal_review_packet.py

source-review-transcript-packet:
	uv run python scripts/source_review_transcript_packet.py

signed-evidence-demo:
	uv run python scripts/signed_evidence_demo.py

signed-evidence-demo-verify:
	uv run python scripts/signed_evidence_demo_verify.py

negative-review-transcripts:
	uv run python scripts/negative_review_transcripts.py

demo-scenario-pack:
	uv run python scripts/demo_scenario_pack.py

release-context:
	@echo "repo_root=$$(pwd)"
	@echo "git_commit=$$(git rev-parse HEAD)"
	@echo "git_dirty=$$(test -z "$$(git status --short)" && echo false || echo true)"

release-check: release-context manifest-lock-check release-guardrails release-evidence-gate reviewer-findings-check review-findings-summary review-run-manifest-check filesystem-contract-check external-findings-intake-dry-run tool-surface-invariant-gate no-new-powers-guardrail read-only-metadata-capability-check read-only-capability-inventory-gate read-only-project-intelligence v3-next-capability-candidate-check next-capability-readiness next-capability-candidate-evaluation-2-check v1-rc-roadmap-check v1-rc-status-check v1-operator-quickstart-check v1-workbench-evidence-check v1-assurance-closure-check v1-rc-readiness enterprise-readiness-runway-check agent-workflow-check low-implementer-delegation-packet low-implementer-delegation-check low-implementer-ticket-catalog-check agent-run-evidence-contract-check agent-run-evidence-export-check agent-run-evidence-export-plan-check agent-run-evidence-export-implementation-gate operator-action-states-check dashboard-evidence-checklist-check agent-run-timeline-readiness agent-run-evidence-readiness agent-run-operations-readiness workbench-readiness guided-demo-readiness demo-flow-readiness demo-flow-result-check demo-evidence-readiness governed-artifact-transfer-lab-check governed-artifact-transfer-stage2-check hello-world-sandbox-demo-packet-check hello-world-sandbox-demo-check hello-world-sandbox-observed-demo-check hello-world-mission-control-handoff-check sandbox-promotion-evidence-contract-check sandbox-artifact-observed-demo-check sandbox-artifact-write-text-implementation-gate sandbox-artifact-write-text-negative-transcripts siem-evidence-design-check data-classification-design-check control-mapping-design-check incident-reconstruction-check observability-readiness control-mapping-readiness operator-sandbox-demo-readiness project-manifest-summary-proposal-check project-manifest-summary-implementation-plan-check project-manifest-summary-implementation-gate project-release-summary-proposal-check project-release-summary-implementation-plan-check project-release-summary-preimplementation-check project-release-summary-implementation-gate project-release-summary-transition-check project-release-summary-review-handoff-check project-risk-summary-proposal-check project-risk-summary-implementation-plan-check project-risk-summary-implementation-gate project-risk-summary-preimplementation-check project-risk-summary-review-handoff-check project-dependency-summary-proposal-check project-dependency-summary-implementation-plan-check project-dependency-summary-implementation-gate project-structure-summary-proposal-check project-structure-summary-implementation-plan-check project-structure-summary-implementation-gate project-test-summary-proposal-check project-test-summary-implementation-plan-check project-test-summary-implementation-gate project-docs-summary-proposal-check project-docs-summary-implementation-plan-check project-docs-summary-implementation-gate project-language-summary-proposal-check project-language-summary-implementation-plan-check project-language-summary-implementation-gate project-config-summary-proposal-check project-config-summary-implementation-plan-check project-config-summary-implementation-gate project-ci-summary-proposal-check project-ci-summary-implementation-plan-check project-ci-summary-implementation-gate evidence-confusion-gate external-review-closure-gate closure-matrix-evidence-sync accepted-risk-register-check capability-decision-report v08-status-reconciliation v08-public-preview-decision v08-capability-design-gate v08-final-decision-packet v09-design-only-gate git-commit-metadata-proposal-check git-ref-summary-proposal-check git-ref-summary-implementation-plan-check git-ref-summary-implementation-gate git-tag-metadata-proposal-check git-tag-metadata-implementation-plan-check git-tag-metadata-implementation-gate git-commit-metadata-implementation-plan-check git-commit-metadata-implementation-gate v06-lane-status v06-closure-readiness v06-final-handoff v07-closure-prep v07-patch-apply-recheck-prep v05-threat-model-delta-check v05-boundary-decision-draft-check v05-handoff-packet-check manifest-change-review determinism-check adversarial-corpus-check resource-limit-check demo-scenario-pack evidence-contracts-check policy-test policy-parity test lint typecheck ui-test docs-site
	npm run build --prefix apps/ui

ui-dev:
	npm run dev --prefix apps/ui

demo-seed:
	mkdir -p workspaces/demo
	cp -R deploy/demo/workspace/. workspaces/demo/
	@echo "Seeded workspaces/demo"

compose-config:
	$(COMPOSE) --env-file $(COMPOSE_ENV_FILE) -f $(COMPOSE_FILE) config

compose-up: demo-seed
	$(COMPOSE) --env-file $(COMPOSE_ENV_FILE) -f $(COMPOSE_FILE) up --build -d

compose-down:
	$(COMPOSE) --env-file $(COMPOSE_ENV_FILE) -f $(COMPOSE_FILE) down

compose-logs:
	$(COMPOSE) --env-file $(COMPOSE_ENV_FILE) -f $(COMPOSE_FILE) logs -f

compose-smoke:
	@TOKEN=$$(sed -n 's/^ITHILDIN_ADMIN_TOKEN=//p' $(COMPOSE_ENV_FILE) | tail -n 1); \
	test -n "$$TOKEN"; \
	curl -fsS http://127.0.0.1:8000/healthz >/dev/null; \
	curl -fsS -H "Authorization: Bearer $$TOKEN" http://127.0.0.1:8000/tools >/dev/null; \
	curl -fsS http://127.0.0.1:5173/ >/dev/null; \
	echo "Compose smoke passed."

demo-flow: demo-seed
	uv run python scripts/demo_flow.py --env-file $(COMPOSE_ENV_FILE)

ollama-smoke:
	uv run python scripts/ollama_demo.py smoke

local-model-demo: ollama-smoke
	uv run python scripts/ollama_demo.py local-demo

local-prompt-triage:
	uv run python scripts/local_prompt_triage.py --file docs/codex/v0.8-roadmap-prompt.md

mcp-inspector-recipes:
	uv run python scripts/mcp_inspector_recipes.py

docs-site:
	uv run python scripts/build_docs_site.py

clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache
	rm -rf apps/ui/dist apps/ui/node_modules
	rm -rf site
