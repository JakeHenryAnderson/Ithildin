COMPOSE ?= docker compose
COMPOSE_FILE ?= deploy/docker-compose.yml
COMPOSE_ENV_FILE ?= $(shell if [ -f .env ]; then echo .env; else echo .env.example; fi)

.PHONY: accepted-risk-register-check admin-token-generate adversarial-corpus-check audit-diagnostics audit-export-verify audit-keygen capability-decision-report capability-expansion-gate clean closure-matrix-evidence-sync compose-config compose-down compose-logs compose-smoke compose-up demo-flow demo-scenario-pack demo-seed determinism-check docs-site evidence-confusion-gate evidence-contracts-check external-findings-intake-dry-run external-response-template-check external-review-closure-gate filesystem-contract-check internal-review-packet lint local-model-demo mcp-inspector-recipes manifest-change-review manifest-lock manifest-lock-check manifest-lock-keygen manifest-lock-sign manifest-lock-signature-check negative-review-transcripts no-new-powers-guardrail ollama-smoke packet-redaction-scan policy-parity policy-test release-check release-context release-evidence release-evidence-gate release-evidence-validate release-guardrails release-packet resource-limit-check review-candidate review-findings-summary review-packet-bundle review-packet-consolidated review-packet-diff review-packet-diff-gate review-packet-source-pointers review-run-manifest-check reviewer-artifact-manifest reviewer-findings-check signed-evidence-demo signed-evidence-demo-verify source-review-transcript-packet test tool-surface-invariant-gate typecheck ui-dev v04-review-packet v05-threat-model-delta-check

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

typecheck:
	uv run mypy
	npm run typecheck --prefix apps/ui

release-guardrails:
	uv run python scripts/release_guardrails.py

reviewer-findings-check:
	uv run python scripts/reviewer_findings.py

external-findings-intake-dry-run:
	uv run python scripts/external_findings_intake_dry_run.py

external-response-template-check:
	uv run python scripts/external_response_template_check.py

v05-threat-model-delta-check:
	uv run python scripts/v05_threat_model_delta_check.py

review-run-manifest-check:
	uv run python scripts/review_run_manifest.py

reviewer-artifact-manifest:
	uv run python scripts/reviewer_artifact_manifest.py

review-findings-summary:
	uv run python scripts/review_findings_collect.py

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
	$(MAKE) review-packet-bundle
	$(MAKE) review-packet-consolidated
	$(MAKE) packet-redaction-scan
	$(MAKE) docs-site
	@echo "Review candidate ready: var/review-packets/v0.2/GPT-5.5-Pro-consolidated"

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

release-check: release-context manifest-lock-check release-guardrails release-evidence-gate reviewer-findings-check review-findings-summary review-run-manifest-check filesystem-contract-check external-findings-intake-dry-run tool-surface-invariant-gate no-new-powers-guardrail evidence-confusion-gate external-review-closure-gate closure-matrix-evidence-sync accepted-risk-register-check capability-decision-report v05-threat-model-delta-check manifest-change-review determinism-check adversarial-corpus-check resource-limit-check demo-scenario-pack evidence-contracts-check policy-test policy-parity test lint typecheck docs-site
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
