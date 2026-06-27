COMPOSE ?= docker compose
COMPOSE_FILE ?= deploy/docker-compose.yml
COMPOSE_ENV_FILE ?= $(shell if [ -f .env ]; then echo .env; else echo .env.example; fi)

.PHONY: accepted-risk-register-check admin-token-generate adversarial-corpus-check agent-run-correlation-packet agent-run-correlation-smoke agent-run-evidence-contract-check agent-run-evidence-export-check agent-run-evidence-export-implementation-gate agent-run-evidence-export-plan-check agent-run-evidence-packet agent-run-evidence-readiness agent-run-operations-readiness agent-run-timeline-packet agent-run-timeline-readiness agent-workflow-check audit-diagnostics audit-export-verify audit-keygen capability-decision-report capability-expansion-gate clean closure-matrix-evidence-sync compose-config compose-down compose-logs compose-smoke compose-up compliance-mapping-architecture-check compliance-mapping-disposition-packet compliance-mapping-disposition-packet-check control-mapping-design-check control-mapping-readiness dashboard-evidence-checklist-check data-classification-design-check demo-evidence-packet demo-evidence-readiness demo-flow demo-flow-readiness demo-flow-result-check demo-observed-summary demo-operator-walkthrough demo-readiness-summary demo-reset-guide demo-scenario-pack demo-seed demo-workbench demo-workbench-smoke determinism-check docs-site enterprise-readiness-gap-matrix-check enterprise-readiness-runway-check enterprise-dual-response-readiness enterprise-dual-review-handoff enterprise-dual-review-handoff-check enterprise-next-review-handoff enterprise-next-review-handoff-check enterprise-next-review-ready-check enterprise-response-status-board post-rc-decision-gate post-rc-decision-record-template-check post-rc-decision-record-examples-check post-rc-decision-register-check mission-control-display-importer-plan-check mission-control-display-integration-proposal-check mission-control-display-review-packet mission-control-display-review-packet-check mission-control-side-handoff-plan-check mission-control-handoff-schema-contract-check mission-control-handoff-negative-fixtures-check mission-control-handoff-fixture-pack mission-control-handoff-fixture-pack-check mission-control-importer-acceptance-matrix-check evidence-confusion-gate evidence-contracts-check external-findings-intake-dry-run external-response-normalize external-response-template-check external-review-closure-gate filesystem-contract-check filesystem-source-review-bundle git-commit-metadata-implementation-gate git-commit-metadata-implementation-plan-check git-commit-metadata-proposal-check git-commit-metadata-source-review-bundle git-ref-summary-implementation-gate git-ref-summary-implementation-plan-check git-ref-summary-proposal-check git-ref-summary-source-review-bundle http-fetch-source-review-bundle incident-reconstruction-check internal-review-packet lint live-demo-evidence-summary live-demo-packet live-demo-preflight live-demo-smoke live-demo-status local-model-demo local-prompt-triage low-implementer-delegation-check low-implementer-delegation-packet low-implementer-ticket-catalog-check mcp-ingress-source-review-bundle mcp-inspector-recipes manifest-change-review manifest-lock manifest-lock-check manifest-lock-keygen manifest-lock-sign manifest-lock-signature-check negative-review-transcripts next-capability-candidate-evaluation-2-check next-capability-readiness no-new-powers-guardrail observability-control-packet observability-readiness ollama-smoke operator-action-states-check operator-sandbox-dashboard-checklist operator-sandbox-demo-packet operator-sandbox-demo-readiness operator-sandbox-demo-smoke packet-redaction-scan policy-parity policy-registry-source-review-bundle policy-test project-ci-summary-design-review-packet project-ci-summary-implementation-gate project-ci-summary-implementation-plan-check project-ci-summary-proposal-check project-ci-summary-source-review-bundle project-config-summary-implementation-gate project-config-summary-implementation-plan-check project-config-summary-proposal-check project-config-summary-source-review-bundle project-dependency-summary-design-review-packet project-dependency-summary-implementation-gate project-dependency-summary-implementation-plan-check project-dependency-summary-proposal-check project-dependency-summary-source-review-bundle project-docs-summary-design-review-packet project-docs-summary-implementation-gate project-docs-summary-implementation-plan-check project-docs-summary-proposal-check project-docs-summary-source-review-bundle project-language-summary-design-review-packet project-language-summary-implementation-gate project-language-summary-implementation-plan-check project-language-summary-proposal-check project-language-summary-source-review-bundle project-manifest-summary-implementation-gate project-manifest-summary-implementation-plan-check project-manifest-summary-proposal-check project-manifest-summary-source-review-bundle project-release-summary-design-review-packet project-release-summary-implementation-gate project-release-summary-implementation-plan-check project-release-summary-preimplementation-check project-release-summary-proposal-check project-release-summary-transition-check project-structure-summary-design-review-packet project-structure-summary-implementation-gate project-structure-summary-implementation-plan-check project-structure-summary-proposal-check project-structure-summary-source-review-bundle project-test-summary-design-review-packet project-test-summary-implementation-gate project-test-summary-implementation-plan-check project-test-summary-proposal-check project-test-summary-source-review-bundle read-only-capability-inventory-gate read-only-metadata-capability-check read-only-project-intelligence release-automation-source-review-bundle release-check release-context release-evidence release-evidence-gate release-evidence-validate release-guardrails release-packet resource-limit-check review-candidate review-console-source-review-bundle review-findings-summary review-findings-summary-write review-packet-bundle review-packet-consolidated review-packet-diff review-packet-diff-gate review-packet-source-pointers review-run-manifest-check review-run-manifest-refresh reviewer-artifact-manifest reviewer-findings-check sandbox-vm-worker-boundary-charter-check sandbox-vm-profile-contract-check sandbox-vm-preflight-contract-check sandbox-vm-poc-review-packet sandbox-vm-poc-review-packet-check sandbox-vm-static-profile-fixture-contract-check sandbox-vm-static-profile-negative-fixtures-check sandbox-vm-static-preflight sandbox-vm-static-preflight-disposition-packet sandbox-vm-static-preflight-disposition-packet-check sandbox-vm-static-preflight-external-review-bundle-check sandbox-vm-static-preflight-disposition-plan-check sandbox-vm-static-preflight-disposition-closure-check sandbox-vm-static-preflight-negative-transcripts sandbox-vm-static-preflight-implementation-gate sandbox-vm-static-preflight-source-review-packet sandbox-vm-static-preflight-source-review-packet-check sandbox-vm-static-profile-preflight-plan-check siem-evidence-design-check signed-evidence-demo signed-evidence-demo-verify signed-evidence-source-review-bundle source-review-transcript-packet test tool-surface-invariant-gate typecheck ui-dev ui-test v04-review-packet v05-boundary-decision-draft-check v05-handoff-packet-check v05-review-candidate v05-threat-model-delta-check v06-closure-readiness v06-final-handoff v06-lane-status v06-lane-status-write v06-patch-apply-review-packet v06-review-dispatch-packets v07-closure-prep v07-patch-apply-recheck-prep v08-capability-design-gate v08-final-decision-packet v08-public-preview-decision v08-status-reconciliation v09-design-only-gate v09-design-review-packet v1-progress-assessment v1-rc-roadmap-check v1-rc-status-check v1-rc-feature-freeze v1-rc-external-review-prompt-check v1-rc-final-handoff-check v1-rc-post-review-triage-check v1-operator-quickstart-check v1-operator-trial-checklist-check v1-workbench-evidence-check v1-assurance-closure-check v1-rc-readiness v1-rc-packet v3-next-capability-candidate-check workbench-evidence-packet workbench-readiness
.PHONY: governed-artifact-transfer-lab governed-artifact-transfer-lab-check governed-artifact-transfer-stage2 governed-artifact-transfer-stage2-check hello-world-sandbox-demo-packet hello-world-sandbox-demo-packet-check hello-world-sandbox-demo-check hello-world-sandbox-observed-demo hello-world-sandbox-observed-demo-check hello-world-mission-control-handoff hello-world-mission-control-handoff-check sandbox-promotion-evidence-contract-check trusted-host-promotion-decision-intake-check trusted-host-promotion-state-machine-check trusted-host-promotion-negative-fixtures-check trusted-host-promotion-zone-contract-check trusted-host-promotion-implementation-plan-check trusted-host-promotion-source-review-packet trusted-host-promotion-source-review-packet-check trusted-host-promotion-disposition-packet trusted-host-promotion-disposition-packet-check trusted-host-promotion-external-review-bundle trusted-host-promotion-external-review-bundle-check trusted-host-promotion-disposition-closure-check trusted-host-promotion-external-response-intake-check trusted-host-promotion-internal-review-check mission-control-display-disposition-closure-check production-identity-storage-architecture-check production-identity-storage-disposition-closure-check production-identity-storage-response-dry-run production-identity-storage-external-response-intake-check production-identity-storage-external-review-bundle production-identity-storage-external-review-bundle-check siem-export-adapter-architecture-check siem-export-adapter-disposition-closure-check siem-export-adapter-response-dry-run siem-export-adapter-external-response-intake-check siem-export-adapter-external-review-bundle siem-export-adapter-external-review-bundle-check compliance-mapping-disposition-closure-check compliance-mapping-response-dry-run compliance-mapping-external-review-bundle compliance-mapping-external-review-bundle-check public-positioning-external-review-bundle public-positioning-external-review-bundle-check sandbox-vm-static-preflight-reviewed-packet-hash sandbox-vm-static-preflight-response-kit sandbox-vm-static-preflight-response-kit-check sandbox-artifact-observed-demo sandbox-artifact-observed-demo-check sandbox-artifact-write-text-preimplementation-check sandbox-artifact-write-text-implementation-gate sandbox-artifact-write-text-negative-transcripts sandbox-artifact-write-text-source-review-bundle
.PHONY: mission-control-handoff-reference-validator

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

v1-progress-assessment:
	uv run python scripts/v1_progress_assessment.py

v1-rc-feature-freeze:
	uv run python scripts/v1_rc_feature_freeze_check.py

v1-rc-external-review-prompt-check:
	uv run python scripts/v1_rc_external_review_prompt_check.py

v1-rc-final-handoff-check:
	uv run python scripts/v1_rc_final_handoff_check.py

v1-rc-post-review-triage-check:
	uv run python scripts/v1_rc_post_review_triage_check.py

v1-operator-quickstart-check:
	uv run python scripts/v1_operator_quickstart_check.py

v1-operator-trial-checklist-check:
	uv run python scripts/v1_operator_trial_checklist_check.py

v1-operator-trial-record:
	uv run python scripts/v1_operator_trial_record.py

v1-operator-trial-record-check:
	uv run python scripts/v1_operator_trial_record.py --check

v1-workbench-evidence-check:
	uv run python scripts/v1_workbench_evidence_check.py

v1-assurance-closure-check:
	uv run python scripts/v1_assurance_closure_check.py

v1-rc-readiness:
	uv run python scripts/v1_rc_readiness_check.py

v1-rc-packet:
	uv run python scripts/v1_rc_packet.py

mission-control-display-integration-proposal-check:
	uv run python scripts/mission_control_display_integration_proposal_check.py

mission-control-display-importer-plan-check:
	uv run python scripts/mission_control_display_importer_plan_check.py

mission-control-display-decision-intake-check:
	uv run python scripts/mission_control_display_decision_intake_check.py

mission-control-display-decision-record-skeleton-check:
	uv run python scripts/mission_control_display_decision_record_skeleton_check.py

mission-control-display-review-packet:
	uv run python scripts/mission_control_display_review_packet.py

mission-control-display-review-packet-check:
	uv run python scripts/mission_control_display_review_packet.py --check

mission-control-display-disposition-packet:
	uv run python scripts/mission_control_display_disposition_packet.py

mission-control-display-disposition-packet-check:
	uv run python scripts/mission_control_display_disposition_packet.py --check

mission-control-display-external-review-bundle:
	uv run python scripts/mission_control_display_external_review_bundle.py

mission-control-display-external-review-bundle-check:
	uv run python scripts/mission_control_display_external_review_bundle.py --check

mission-control-display-response-kit:
	uv run python scripts/mission_control_display_response_kit.py

mission-control-display-response-kit-check:
	uv run python scripts/mission_control_display_response_kit.py --check

mission-control-display-next-review-ready-check:
	uv run python scripts/mission_control_display_next_review_ready_check.py

mission-control-display-external-response-intake-check:
	uv run python scripts/mission_control_display_external_response_intake_check.py

mission-control-display-disposition-closure-check:
	uv run python scripts/mission_control_display_disposition_closure_check.py

mission-control-display-response-dry-run:
	uv run python scripts/mission_control_display_response_dry_run.py

mission-control-integration-readiness-packet:
	uv run python scripts/mission_control_integration_readiness_packet.py

mission-control-integration-readiness-packet-check:
	uv run python scripts/mission_control_integration_readiness_packet.py --check

mission-control-side-handoff-plan-check:
	uv run python scripts/mission_control_side_handoff_plan_check.py

mission-control-integration-implementation-ticket-check:
	uv run python scripts/mission_control_integration_implementation_ticket_check.py

sandbox-vm-worker-boundary-charter-check:
	uv run python scripts/sandbox_vm_worker_boundary_charter_check.py

sandbox-vm-profile-contract-check:
	uv run python scripts/sandbox_vm_profile_contract_check.py

sandbox-vm-preflight-contract-check:
	uv run python scripts/sandbox_vm_preflight_contract_check.py

sandbox-vm-poc-review-packet:
	uv run python scripts/sandbox_vm_poc_review_packet.py

sandbox-vm-poc-review-packet-check:
	uv run python scripts/sandbox_vm_poc_review_packet.py --check

sandbox-vm-static-profile-preflight-plan-check:
	uv run python scripts/sandbox_vm_static_profile_preflight_plan_check.py

sandbox-vm-static-profile-fixture-contract-check:
	uv run python scripts/sandbox_vm_static_profile_fixture_contract_check.py

sandbox-vm-static-profile-negative-fixtures-check:
	uv run python scripts/sandbox_vm_static_profile_negative_fixtures_check.py

sandbox-vm-static-preflight:
	uv run python scripts/sandbox_vm_static_preflight.py

sandbox-vm-static-preflight-negative-transcripts:
	uv run python scripts/sandbox_vm_static_preflight_negative_transcripts.py

sandbox-vm-static-preflight-implementation-gate:
	uv run python scripts/sandbox_vm_static_preflight_implementation_gate.py

sandbox-vm-static-preflight-source-review-packet:
	uv run python scripts/sandbox_vm_static_preflight_source_review_packet.py

sandbox-vm-static-preflight-source-review-packet-check:
	uv run python scripts/sandbox_vm_static_preflight_source_review_packet.py --check

sandbox-vm-static-preflight-disposition-packet:
	uv run python scripts/sandbox_vm_static_preflight_disposition_packet.py

sandbox-vm-static-preflight-disposition-packet-check:
	uv run python scripts/sandbox_vm_static_preflight_disposition_packet.py --check

sandbox-vm-static-preflight-external-review-bundle:
	uv run python scripts/sandbox_vm_static_preflight_external_review_bundle.py

sandbox-vm-static-preflight-external-review-bundle-check:
	uv run python scripts/sandbox_vm_static_preflight_external_review_bundle.py --check

sandbox-vm-static-preflight-reviewed-packet-hash:
	uv run python scripts/sandbox_vm_static_preflight_reviewed_packet_hash.py

sandbox-vm-static-preflight-response-kit:
	uv run python scripts/sandbox_vm_static_preflight_response_kit.py

sandbox-vm-static-preflight-response-kit-check:
	uv run python scripts/sandbox_vm_static_preflight_response_kit.py --check

sandbox-vm-static-preflight-disposition-plan-check:
	uv run python scripts/sandbox_vm_static_preflight_disposition_plan_check.py

sandbox-vm-static-preflight-disposition-closure-check:
	uv run python scripts/sandbox_vm_static_preflight_disposition_closure_check.py

sandbox-vm-static-preflight-disposition-record-skeleton-check:
	uv run python scripts/sandbox_vm_static_preflight_disposition_record_skeleton_check.py

sandbox-vm-static-preflight-external-response-intake-check:
	uv run python scripts/sandbox_vm_static_preflight_external_response_intake_check.py

sandbox-vm-static-preflight-response-dry-run:
	uv run python scripts/sandbox_vm_static_preflight_response_dry_run.py

sandbox-vm-static-preflight-triage-update-check:
	uv run python scripts/sandbox_vm_static_preflight_triage_update_check.py

sandbox-vm-static-preflight-response-application-record-check:
	uv run python scripts/sandbox_vm_static_preflight_response_application_record_check.py

sandbox-vm-static-preflight-response-application-playbook-check:
	uv run python scripts/sandbox_vm_static_preflight_response_application_playbook_check.py

.PHONY: sandbox-vm-static-preflight-response-dry-run sandbox-vm-static-preflight-triage-update-check sandbox-vm-static-preflight-response-application-record-check sandbox-vm-static-preflight-response-application-playbook-check sandbox-vm-static-preflight-disposition-record-skeleton-check sandbox-vm-static-preflight-external-review-bundle sandbox-vm-static-preflight-external-review-bundle-check

sandbox-vm-static-preflight-reviewer-reproduction-map-check:
	uv run python scripts/sandbox_vm_static_preflight_reviewer_reproduction_map_check.py

sandbox-vm-live-poc-decision-intake-check:
	uv run python scripts/sandbox_vm_live_poc_decision_intake_check.py

sandbox-vm-live-poc-evidence-contract-check:
	uv run python scripts/sandbox_vm_live_poc_evidence_contract_check.py

sandbox-vm-live-poc-preconditions-map-check:
	uv run python scripts/sandbox_vm_live_poc_preconditions_map_check.py

sandbox-vm-live-poc-preconditions-ready-check:
	uv run python scripts/sandbox_vm_live_poc_preconditions_ready_check.py

sandbox-vm-live-poc-external-response-intake-check:
	uv run python scripts/sandbox_vm_live_poc_external_response_intake_check.py

sandbox-vm-live-poc-decision-closure-check:
	uv run python scripts/sandbox_vm_live_poc_decision_closure_check.py

sandbox-vm-live-poc-decision-record-skeleton-check:
	uv run python scripts/sandbox_vm_live_poc_decision_record_skeleton_check.py

sandbox-vm-live-poc-response-dry-run:
	uv run python scripts/sandbox_vm_live_poc_response_dry_run.py

sandbox-vm-live-poc-prerequisite-disposition-dry-run:
	uv run python scripts/sandbox_vm_live_poc_prerequisite_disposition_dry_run.py

sandbox-vm-live-poc-response-kit:
	uv run python scripts/sandbox_vm_live_poc_response_kit.py

sandbox-vm-live-poc-response-kit-check:
	uv run python scripts/sandbox_vm_live_poc_response_kit.py --check

sandbox-vm-live-poc-external-review-bundle:
	uv run python scripts/sandbox_vm_live_poc_external_review_bundle.py

sandbox-vm-live-poc-external-review-bundle-check:
	uv run python scripts/sandbox_vm_live_poc_external_review_bundle.py --check

.PHONY: sandbox-vm-live-poc-preconditions-ready-check sandbox-vm-live-poc-decision-closure-check sandbox-vm-live-poc-decision-record-skeleton-check sandbox-vm-live-poc-response-dry-run sandbox-vm-live-poc-prerequisite-disposition-dry-run sandbox-vm-live-poc-response-kit sandbox-vm-live-poc-response-kit-check sandbox-vm-live-poc-external-review-bundle sandbox-vm-live-poc-external-review-bundle-check

enterprise-sandbox-control-plane-readiness-check:
	uv run python scripts/enterprise_sandbox_control_plane_readiness_check.py

enterprise-next-review-handoff:
	uv run python scripts/enterprise_next_review_handoff.py

enterprise-next-review-handoff-check:
	uv run python scripts/enterprise_next_review_handoff.py --check

enterprise-next-review-ready-check:
	uv run python scripts/enterprise_next_review_ready_check.py

enterprise-review-send-readiness:
	uv run python scripts/enterprise_review_send_readiness.py

enterprise-dual-review-handoff:
	uv run python scripts/enterprise_dual_review_handoff.py

enterprise-dual-review-handoff-check:
	uv run python scripts/enterprise_dual_review_handoff.py --check

enterprise-dual-review-outbox:
	uv run python scripts/enterprise_dual_review_outbox.py

enterprise-dual-review-outbox-check:
	uv run python scripts/enterprise_dual_review_outbox.py --check

enterprise-review-send-manifest:
	uv run python scripts/enterprise_review_send_manifest.py

enterprise-review-send-manifest-check:
	uv run python scripts/enterprise_review_send_manifest.py --check

enterprise-review-submission-prompt:
	uv run python scripts/enterprise_review_submission_prompt.py

enterprise-review-submission-prompt-check:
	uv run python scripts/enterprise_review_submission_prompt.py --check

enterprise-review-handoff-drill:
	uv run python scripts/enterprise_review_handoff_drill.py

enterprise-review-handoff-drill-check:
	uv run python scripts/enterprise_review_handoff_drill.py --check

enterprise-dual-response-inbox:
	uv run python scripts/enterprise_dual_response_inbox.py

enterprise-dual-response-inbox-check:
	uv run python scripts/enterprise_dual_response_inbox.py --check

enterprise-dual-response-readiness:
	uv run python scripts/enterprise_dual_response_readiness.py

enterprise-response-status-board:
	uv run python scripts/enterprise_response_status_board.py

enterprise-response-status-board-snapshot:
	uv run python scripts/enterprise_response_status_board.py --write

enterprise-response-normalization-coverage:
	uv run python scripts/enterprise_response_normalization_coverage.py

enterprise-response-inbox:
	uv run python scripts/enterprise_response_inbox.py

enterprise-response-inbox-check:
	uv run python scripts/enterprise_response_inbox.py --check

enterprise-response-intake-drill:
	uv run python scripts/enterprise_response_intake_drill.py

.PHONY: enterprise-dual-review-outbox enterprise-dual-review-outbox-check enterprise-review-send-manifest enterprise-review-send-manifest-check enterprise-review-submission-prompt enterprise-review-submission-prompt-check enterprise-review-handoff-drill enterprise-review-handoff-drill-check enterprise-dual-response-inbox enterprise-dual-response-inbox-check enterprise-response-normalization-coverage enterprise-response-inbox enterprise-response-inbox-check enterprise-response-intake-drill

sandbox-vm-live-poc-decision-packet:
	uv run python scripts/sandbox_vm_live_poc_decision_packet.py

sandbox-vm-live-poc-decision-packet-check:
	uv run python scripts/sandbox_vm_live_poc_decision_packet.py --check

enterprise-readiness-runway-check:
	uv run python scripts/enterprise_readiness_runway_check.py

enterprise-readiness-gap-matrix-check:
	uv run python scripts/enterprise_readiness_gap_matrix_check.py

enterprise-external-review-queue-check:
	uv run python scripts/enterprise_external_review_queue_check.py

post-rc-decision-gate:
	uv run python scripts/post_rc_decision_gate.py

post-rc-decision-record-template-check:
	uv run python scripts/post_rc_decision_record_template_check.py

post-rc-decision-record-examples-check:
	uv run python scripts/post_rc_decision_record_examples_check.py

post-rc-decision-register-check:
	uv run python scripts/post_rc_decision_register_check.py

public-security-product-positioning-decision-intake-check:
	uv run python scripts/public_security_product_positioning_decision_intake_check.py

public-security-product-positioning-decision-closure-check:
	uv run python scripts/public_security_product_positioning_decision_closure_check.py

docs-claims-public-preview-disposition-closure-check:
	uv run python scripts/docs_claims_public_preview_disposition_closure_check.py

public-positioning-external-review-bundle:
	uv run python scripts/public_security_product_positioning_external_review_bundle.py

public-positioning-external-review-bundle-check:
	uv run python scripts/public_security_product_positioning_external_review_bundle.py --check

public-security-product-positioning-response-kit:
	uv run python scripts/public_security_product_positioning_response_kit.py

public-security-product-positioning-response-kit-check:
	uv run python scripts/public_security_product_positioning_response_kit.py --check

production-identity-storage-architecture-check:
	uv run python scripts/production_identity_storage_architecture_check.py

production-identity-storage-disposition-packet:
	uv run python scripts/production_identity_storage_disposition_packet.py

production-identity-storage-disposition-packet-check:
	uv run python scripts/production_identity_storage_disposition_packet.py --check

production-identity-storage-disposition-closure-check:
	uv run python scripts/production_identity_storage_disposition_closure_check.py

production-identity-storage-response-dry-run:
	uv run python scripts/production_identity_storage_response_dry_run.py

production-identity-storage-response-kit:
	uv run python scripts/production_identity_storage_response_kit.py

production-identity-storage-response-kit-check:
	uv run python scripts/production_identity_storage_response_kit.py --check

production-identity-storage-external-response-intake-check:
	uv run python scripts/production_identity_storage_external_response_intake_check.py

production-identity-storage-external-review-bundle:
	uv run python scripts/production_identity_storage_external_review_bundle.py

production-identity-storage-external-review-bundle-check:
	uv run python scripts/production_identity_storage_external_review_bundle.py --check

siem-export-adapter-architecture-check:
	uv run python scripts/siem_export_adapter_architecture_check.py

siem-export-adapter-disposition-packet:
	uv run python scripts/siem_export_adapter_disposition_packet.py

siem-export-adapter-disposition-packet-check:
	uv run python scripts/siem_export_adapter_disposition_packet.py --check

siem-export-adapter-external-review-bundle:
	uv run python scripts/siem_export_adapter_external_review_bundle.py

siem-export-adapter-external-review-bundle-check:
	uv run python scripts/siem_export_adapter_external_review_bundle.py --check

siem-export-adapter-disposition-closure-check:
	uv run python scripts/siem_export_adapter_disposition_closure_check.py

siem-export-adapter-response-dry-run:
	uv run python scripts/siem_export_adapter_response_dry_run.py

siem-export-adapter-response-kit:
	uv run python scripts/siem_export_adapter_response_kit.py

siem-export-adapter-response-kit-check:
	uv run python scripts/siem_export_adapter_response_kit.py --check

siem-export-adapter-external-response-intake-check:
	uv run python scripts/siem_export_adapter_external_response_intake_check.py

compliance-mapping-architecture-check:
	uv run python scripts/compliance_mapping_architecture_check.py

compliance-mapping-disposition-packet:
	uv run python scripts/compliance_mapping_disposition_packet.py

compliance-mapping-disposition-packet-check:
	uv run python scripts/compliance_mapping_disposition_packet.py --check

compliance-mapping-external-review-bundle:
	uv run python scripts/compliance_mapping_external_review_bundle.py

compliance-mapping-external-review-bundle-check:
	uv run python scripts/compliance_mapping_external_review_bundle.py --check

compliance-mapping-disposition-closure-check:
	uv run python scripts/compliance_mapping_disposition_closure_check.py

compliance-mapping-response-dry-run:
	uv run python scripts/compliance_mapping_response_dry_run.py

compliance-mapping-response-kit:
	uv run python scripts/compliance_mapping_response_kit.py

compliance-mapping-response-kit-check:
	uv run python scripts/compliance_mapping_response_kit.py --check

compliance-mapping-external-response-intake-check:
	uv run python scripts/compliance_mapping_external_response_intake_check.py

mission-control-handoff-schema-contract-check:
	uv run python scripts/mission_control_handoff_schema_contract_check.py

mission-control-handoff-negative-fixtures-check:
	uv run python scripts/mission_control_handoff_negative_fixtures_check.py

mission-control-handoff-fixture-pack:
	uv run python scripts/mission_control_handoff_fixture_pack.py

mission-control-handoff-fixture-pack-check:
	uv run python scripts/mission_control_handoff_fixture_pack.py --check

mission-control-importer-acceptance-matrix-check:
	uv run python scripts/mission_control_importer_acceptance_matrix_check.py

mission-control-handoff-reference-validator:
	uv run python scripts/mission_control_handoff_reference_validator.py

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

trusted-host-promotion-decision-intake-check:
	uv run python scripts/trusted_host_promotion_decision_intake_check.py

trusted-host-promotion-state-machine-check:
	uv run python scripts/trusted_host_promotion_state_machine_check.py

trusted-host-promotion-negative-fixtures-check:
	uv run python scripts/trusted_host_promotion_negative_fixtures_check.py

trusted-host-promotion-zone-contract-check:
	uv run python scripts/trusted_host_promotion_zone_contract_check.py

trusted-host-promotion-implementation-plan-check:
	uv run python scripts/trusted_host_promotion_implementation_plan_check.py

trusted-host-promotion-source-review-packet:
	uv run python scripts/trusted_host_promotion_source_review_packet.py

trusted-host-promotion-source-review-packet-check:
	uv run python scripts/trusted_host_promotion_source_review_packet.py --check

trusted-host-promotion-disposition-packet:
	uv run python scripts/trusted_host_promotion_disposition_packet.py

trusted-host-promotion-disposition-packet-check:
	uv run python scripts/trusted_host_promotion_disposition_packet.py --check

trusted-host-promotion-external-review-bundle:
	uv run python scripts/trusted_host_promotion_external_review_bundle.py

trusted-host-promotion-external-review-bundle-check:
	uv run python scripts/trusted_host_promotion_external_review_bundle.py --check

trusted-host-promotion-disposition-closure-check:
	uv run python scripts/trusted_host_promotion_disposition_closure_check.py

trusted-host-promotion-external-response-intake-check:
	uv run python scripts/trusted_host_promotion_external_response_intake_check.py

trusted-host-promotion-response-dry-run:
	uv run python scripts/trusted_host_promotion_response_dry_run.py

trusted-host-promotion-response-kit:
	uv run python scripts/trusted_host_promotion_response_kit.py

trusted-host-promotion-response-kit-check:
	uv run python scripts/trusted_host_promotion_response_kit.py --check

trusted-host-promotion-internal-review-check:
	uv run python scripts/trusted_host_promotion_internal_review_check.py

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
	@mkdir -p var/review-packets/v3
	@echo "running release-check; transcript will be written to var/review-packets/v3/review-candidate-release-check.txt"
	@{ echo "$$ make release-check"; $(MAKE) release-check; rc=$$?; echo "returncode=$$rc"; exit $$rc; } > var/review-packets/v3/review-candidate-release-check.txt 2>&1 || (cat var/review-packets/v3/review-candidate-release-check.txt; exit 1)
	@echo "release-check transcript: var/review-packets/v3/review-candidate-release-check.txt"
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
	$(MAKE) mission-control-handoff-fixture-pack
	$(MAKE) mission-control-importer-acceptance-matrix-check
	$(MAKE) mission-control-handoff-reference-validator
	$(MAKE) mission-control-display-review-packet
	$(MAKE) mission-control-display-disposition-packet
	$(MAKE) mission-control-integration-readiness-packet
	$(MAKE) mission-control-display-external-review-bundle
	$(MAKE) mission-control-display-response-kit
	$(MAKE) production-identity-storage-disposition-packet
	$(MAKE) production-identity-storage-external-review-bundle
	$(MAKE) production-identity-storage-response-kit
	$(MAKE) siem-export-adapter-disposition-packet
	$(MAKE) siem-export-adapter-external-review-bundle
	$(MAKE) siem-export-adapter-response-kit
	$(MAKE) compliance-mapping-disposition-packet
	$(MAKE) compliance-mapping-external-review-bundle
	$(MAKE) compliance-mapping-response-kit
	$(MAKE) sandbox-vm-poc-review-packet
	$(MAKE) sandbox-vm-static-preflight-source-review-packet
	$(MAKE) sandbox-vm-static-preflight-disposition-packet
	$(MAKE) sandbox-vm-static-preflight-external-review-bundle
	$(MAKE) sandbox-vm-static-preflight-response-kit
	$(MAKE) enterprise-next-review-handoff
	$(MAKE) enterprise-review-send-readiness
	$(MAKE) enterprise-dual-review-handoff
	$(MAKE) enterprise-dual-review-outbox
	$(MAKE) enterprise-review-send-manifest
	$(MAKE) enterprise-review-submission-prompt
	$(MAKE) enterprise-review-handoff-drill
	$(MAKE) enterprise-dual-response-inbox
	$(MAKE) enterprise-dual-response-readiness
	$(MAKE) enterprise-response-status-board
	$(MAKE) enterprise-response-status-board-snapshot
	$(MAKE) enterprise-response-normalization-coverage
	$(MAKE) enterprise-response-inbox
	$(MAKE) enterprise-response-intake-drill
	$(MAKE) sandbox-vm-live-poc-decision-packet
	$(MAKE) sandbox-vm-live-poc-external-review-bundle
	$(MAKE) sandbox-vm-live-poc-response-kit
	$(MAKE) trusted-host-promotion-source-review-packet
	$(MAKE) trusted-host-promotion-disposition-packet
	$(MAKE) trusted-host-promotion-external-review-bundle
	$(MAKE) trusted-host-promotion-response-kit
	$(MAKE) public-positioning-external-review-bundle
	$(MAKE) public-security-product-positioning-response-kit
	$(MAKE) live-demo-evidence-summary
	$(MAKE) live-demo-packet
	$(MAKE) guided-demo
	$(MAKE) workbench-evidence-packet
	$(MAKE) demo-flow-readiness
	$(MAKE) demo-evidence-packet
	$(MAKE) demo-evidence-readiness
	$(MAKE) v1-operator-trial-record
	$(MAKE) governed-artifact-transfer-lab
	$(MAKE) governed-artifact-transfer-lab-check
	$(MAKE) governed-artifact-transfer-stage2
	$(MAKE) governed-artifact-transfer-stage2-check
	$(MAKE) v1-rc-packet
	$(MAKE) v06-review-dispatch-packets
	uv run python scripts/review_packet_bundle.py --release-check-transcript var/review-packets/v3/review-candidate-release-check.txt
	$(MAKE) review-packet-consolidated
	$(MAKE) packet-redaction-scan
	$(MAKE) docs-site
	@echo "v1.0 RC packet ready: var/review-packets/v1.0/rc"
	@echo "Historical consolidated packet ready: var/review-packets/v0.2/GPT-5.5-Pro-consolidated"

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

release-check: release-context manifest-lock-check release-guardrails release-evidence-gate reviewer-findings-check review-findings-summary review-run-manifest-check filesystem-contract-check external-findings-intake-dry-run tool-surface-invariant-gate no-new-powers-guardrail read-only-metadata-capability-check read-only-capability-inventory-gate read-only-project-intelligence v3-next-capability-candidate-check next-capability-readiness next-capability-candidate-evaluation-2-check v1-rc-roadmap-check v1-rc-status-check v1-progress-assessment v1-rc-feature-freeze v1-rc-external-review-prompt-check v1-rc-final-handoff-check v1-rc-post-review-triage-check v1-operator-quickstart-check v1-operator-trial-checklist-check v1-operator-trial-record-check v1-workbench-evidence-check v1-assurance-closure-check v1-rc-readiness enterprise-readiness-runway-check enterprise-readiness-gap-matrix-check enterprise-external-review-queue-check enterprise-next-review-handoff-check enterprise-next-review-ready-check enterprise-review-send-readiness enterprise-dual-review-handoff-check enterprise-dual-review-outbox-check enterprise-review-send-manifest-check enterprise-review-submission-prompt-check enterprise-dual-response-inbox-check enterprise-dual-response-readiness enterprise-response-status-board enterprise-sandbox-control-plane-readiness-check post-rc-decision-gate post-rc-decision-record-template-check post-rc-decision-record-examples-check post-rc-decision-register-check public-security-product-positioning-decision-intake-check production-identity-storage-architecture-check production-identity-storage-disposition-packet-check production-identity-storage-external-response-intake-check siem-export-adapter-architecture-check siem-export-adapter-disposition-packet-check siem-export-adapter-external-response-intake-check compliance-mapping-architecture-check compliance-mapping-disposition-packet-check compliance-mapping-external-response-intake-check mission-control-display-integration-proposal-check mission-control-display-importer-plan-check mission-control-display-decision-intake-check mission-control-display-decision-record-skeleton-check mission-control-display-review-packet-check mission-control-display-disposition-packet-check mission-control-display-external-response-intake-check mission-control-display-next-review-ready-check mission-control-integration-readiness-packet-check mission-control-side-handoff-plan-check mission-control-integration-implementation-ticket-check mission-control-handoff-schema-contract-check mission-control-handoff-negative-fixtures-check mission-control-handoff-fixture-pack-check mission-control-importer-acceptance-matrix-check sandbox-vm-worker-boundary-charter-check sandbox-vm-profile-contract-check sandbox-vm-preflight-contract-check sandbox-vm-poc-review-packet-check sandbox-vm-static-profile-preflight-plan-check sandbox-vm-static-profile-fixture-contract-check sandbox-vm-static-profile-negative-fixtures-check sandbox-vm-static-preflight sandbox-vm-static-preflight-negative-transcripts sandbox-vm-static-preflight-implementation-gate sandbox-vm-static-preflight-source-review-packet-check sandbox-vm-static-preflight-disposition-packet-check sandbox-vm-static-preflight-external-review-bundle-check sandbox-vm-static-preflight-response-kit-check sandbox-vm-static-preflight-disposition-plan-check sandbox-vm-static-preflight-disposition-closure-check sandbox-vm-static-preflight-disposition-record-skeleton-check sandbox-vm-static-preflight-external-response-intake-check sandbox-vm-static-preflight-response-dry-run sandbox-vm-static-preflight-triage-update-check sandbox-vm-static-preflight-response-application-record-check sandbox-vm-static-preflight-response-application-playbook-check sandbox-vm-static-preflight-reviewer-reproduction-map-check sandbox-vm-live-poc-decision-intake-check sandbox-vm-live-poc-evidence-contract-check sandbox-vm-live-poc-preconditions-map-check sandbox-vm-live-poc-preconditions-ready-check sandbox-vm-live-poc-external-response-intake-check sandbox-vm-live-poc-decision-closure-check sandbox-vm-live-poc-decision-record-skeleton-check sandbox-vm-live-poc-prerequisite-disposition-dry-run sandbox-vm-live-poc-decision-packet-check agent-workflow-check low-implementer-delegation-packet low-implementer-delegation-check low-implementer-ticket-catalog-check agent-run-evidence-contract-check agent-run-evidence-export-check agent-run-evidence-export-plan-check agent-run-evidence-export-implementation-gate operator-action-states-check dashboard-evidence-checklist-check agent-run-timeline-readiness agent-run-evidence-readiness agent-run-operations-readiness workbench-readiness guided-demo-readiness demo-flow-readiness demo-flow-result-check demo-evidence-readiness governed-artifact-transfer-lab-check governed-artifact-transfer-stage2-check hello-world-sandbox-demo-packet-check hello-world-sandbox-demo-check hello-world-sandbox-observed-demo-check hello-world-mission-control-handoff-check sandbox-promotion-evidence-contract-check trusted-host-promotion-decision-intake-check trusted-host-promotion-state-machine-check trusted-host-promotion-negative-fixtures-check trusted-host-promotion-zone-contract-check trusted-host-promotion-implementation-plan-check trusted-host-promotion-source-review-packet-check trusted-host-promotion-disposition-packet-check trusted-host-promotion-external-review-bundle-check trusted-host-promotion-external-response-intake-check trusted-host-promotion-internal-review-check sandbox-artifact-observed-demo-check sandbox-artifact-write-text-implementation-gate sandbox-artifact-write-text-negative-transcripts siem-evidence-design-check data-classification-design-check control-mapping-design-check compliance-mapping-architecture-check compliance-mapping-disposition-packet-check compliance-mapping-external-response-intake-check incident-reconstruction-check observability-readiness control-mapping-readiness operator-sandbox-demo-readiness project-manifest-summary-proposal-check project-manifest-summary-implementation-plan-check project-manifest-summary-implementation-gate project-release-summary-proposal-check project-release-summary-implementation-plan-check project-release-summary-preimplementation-check project-release-summary-implementation-gate project-release-summary-transition-check project-release-summary-review-handoff-check project-risk-summary-proposal-check project-risk-summary-implementation-plan-check project-risk-summary-implementation-gate project-risk-summary-preimplementation-check project-risk-summary-review-handoff-check project-dependency-summary-proposal-check project-dependency-summary-implementation-plan-check project-dependency-summary-implementation-gate project-structure-summary-proposal-check project-structure-summary-implementation-plan-check project-structure-summary-implementation-gate project-test-summary-proposal-check project-test-summary-implementation-plan-check project-test-summary-implementation-gate project-docs-summary-proposal-check project-docs-summary-implementation-plan-check project-docs-summary-implementation-gate project-language-summary-proposal-check project-language-summary-implementation-plan-check project-language-summary-implementation-gate project-config-summary-proposal-check project-config-summary-implementation-plan-check project-config-summary-implementation-gate project-ci-summary-proposal-check project-ci-summary-implementation-plan-check project-ci-summary-implementation-gate evidence-confusion-gate external-review-closure-gate closure-matrix-evidence-sync accepted-risk-register-check capability-decision-report v08-status-reconciliation v08-public-preview-decision v08-capability-design-gate v08-final-decision-packet v09-design-only-gate git-commit-metadata-proposal-check git-ref-summary-proposal-check git-ref-summary-implementation-plan-check git-ref-summary-implementation-gate git-tag-metadata-proposal-check git-tag-metadata-implementation-plan-check git-tag-metadata-implementation-gate git-commit-metadata-implementation-plan-check git-commit-metadata-implementation-gate v06-lane-status v06-closure-readiness v06-final-handoff v07-closure-prep v07-patch-apply-recheck-prep v05-threat-model-delta-check v05-boundary-decision-draft-check v05-handoff-packet-check manifest-change-review determinism-check adversarial-corpus-check resource-limit-check demo-scenario-pack evidence-contracts-check policy-test policy-parity test lint typecheck ui-test docs-site
	npm run build --prefix apps/ui

release-check: compliance-mapping-external-review-bundle-check

release-check: sandbox-vm-static-preflight-response-kit-check
release-check: sandbox-vm-live-poc-decision-closure-check
release-check: sandbox-vm-live-poc-decision-record-skeleton-check
release-check: sandbox-vm-live-poc-response-dry-run
release-check: sandbox-vm-live-poc-response-kit-check
release-check: sandbox-vm-live-poc-external-review-bundle-check
release-check: mission-control-display-response-dry-run
release-check: mission-control-importer-acceptance-matrix-check
release-check: mission-control-handoff-reference-validator
release-check: mission-control-display-external-review-bundle-check
release-check: mission-control-display-response-kit-check

release-check: sandbox-vm-static-preflight-triage-update-check

release-check: trusted-host-promotion-disposition-closure-check
release-check: trusted-host-promotion-response-dry-run
release-check: trusted-host-promotion-response-kit-check
release-check: production-identity-storage-disposition-closure-check
release-check: production-identity-storage-response-dry-run
release-check: production-identity-storage-external-review-bundle-check
release-check: production-identity-storage-response-kit-check

release-check: siem-export-adapter-disposition-closure-check
release-check: siem-export-adapter-response-dry-run
release-check: siem-export-adapter-external-review-bundle-check
release-check: siem-export-adapter-response-kit-check

release-check: compliance-mapping-disposition-closure-check
release-check: compliance-mapping-response-dry-run
release-check: compliance-mapping-response-kit-check

release-check: public-security-product-positioning-decision-closure-check
release-check: public-positioning-external-review-bundle-check
release-check: public-security-product-positioning-response-kit-check
release-check: enterprise-response-normalization-coverage
release-check: enterprise-response-inbox-check
release-check: enterprise-response-intake-drill
release-check: enterprise-review-handoff-drill-check

release-check: docs-claims-public-preview-disposition-closure-check

release-check: mission-control-display-disposition-closure-check

.PHONY: docs-claims-public-preview-disposition-closure-check

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
