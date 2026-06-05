COMPOSE ?= docker compose
COMPOSE_FILE ?= deploy/docker-compose.yml
COMPOSE_ENV_FILE ?= $(shell if [ -f .env ]; then echo .env; else echo .env.example; fi)

.PHONY: accepted-risk-register-check admin-token-generate adversarial-corpus-check audit-diagnostics audit-export-verify audit-keygen capability-decision-report capability-expansion-gate clean closure-matrix-evidence-sync compose-config compose-down compose-logs compose-smoke compose-up demo-flow demo-scenario-pack demo-seed determinism-check docs-site evidence-confusion-gate evidence-contracts-check external-findings-intake-dry-run external-response-normalize external-response-template-check external-review-closure-gate filesystem-contract-check filesystem-source-review-bundle git-commit-metadata-implementation-gate git-commit-metadata-implementation-plan-check git-commit-metadata-proposal-check git-commit-metadata-source-review-bundle git-ref-summary-implementation-gate git-ref-summary-implementation-plan-check git-ref-summary-proposal-check git-ref-summary-source-review-bundle http-fetch-source-review-bundle internal-review-packet lint local-model-demo mcp-ingress-source-review-bundle mcp-inspector-recipes manifest-change-review manifest-lock manifest-lock-check manifest-lock-keygen manifest-lock-sign manifest-lock-signature-check negative-review-transcripts no-new-powers-guardrail ollama-smoke packet-redaction-scan policy-parity policy-registry-source-review-bundle policy-test read-only-capability-inventory-gate read-only-metadata-capability-check release-automation-source-review-bundle release-check release-context release-evidence release-evidence-gate release-evidence-validate release-guardrails release-packet resource-limit-check review-candidate review-console-source-review-bundle review-findings-summary review-findings-summary-write review-packet-bundle review-packet-consolidated review-packet-diff review-packet-diff-gate review-packet-source-pointers review-run-manifest-check reviewer-artifact-manifest reviewer-findings-check signed-evidence-demo signed-evidence-demo-verify signed-evidence-source-review-bundle source-review-transcript-packet test tool-surface-invariant-gate typecheck ui-dev ui-test v04-review-packet v05-boundary-decision-draft-check v05-handoff-packet-check v05-review-candidate v05-threat-model-delta-check v06-closure-readiness v06-final-handoff v06-lane-status v06-lane-status-write v06-patch-apply-review-packet v06-review-dispatch-packets v07-closure-prep v07-patch-apply-recheck-prep v08-capability-design-gate v08-final-decision-packet v08-public-preview-decision v08-status-reconciliation v09-design-only-gate v09-design-review-packet

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
	@TMP_FILE=$$(mktemp /tmp/ithildin-release-evidence.XXXXXX.json); \
	trap 'rm -f "$$TMP_FILE"' EXIT; \
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

release-check: release-context manifest-lock-check release-guardrails release-evidence-gate reviewer-findings-check review-findings-summary review-run-manifest-check filesystem-contract-check external-findings-intake-dry-run tool-surface-invariant-gate no-new-powers-guardrail read-only-metadata-capability-check read-only-capability-inventory-gate evidence-confusion-gate external-review-closure-gate closure-matrix-evidence-sync accepted-risk-register-check capability-decision-report v08-status-reconciliation v08-public-preview-decision v08-capability-design-gate v08-final-decision-packet v09-design-only-gate git-commit-metadata-proposal-check git-ref-summary-proposal-check git-ref-summary-implementation-plan-check git-ref-summary-implementation-gate git-commit-metadata-implementation-plan-check git-commit-metadata-implementation-gate v06-lane-status v06-closure-readiness v06-final-handoff v07-closure-prep v07-patch-apply-recheck-prep v05-threat-model-delta-check v05-boundary-decision-draft-check v05-handoff-packet-check manifest-change-review determinism-check adversarial-corpus-check resource-limit-check demo-scenario-pack evidence-contracts-check policy-test policy-parity test lint typecheck ui-test docs-site
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

mcp-inspector-recipes:
	uv run python scripts/mcp_inspector_recipes.py

docs-site:
	uv run python scripts/build_docs_site.py

clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache
	rm -rf apps/ui/dist apps/ui/node_modules
	rm -rf site
