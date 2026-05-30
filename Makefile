COMPOSE ?= docker compose
COMPOSE_FILE ?= deploy/docker-compose.yml
COMPOSE_ENV_FILE ?= $(shell if [ -f .env ]; then echo .env; else echo .env.example; fi)

.PHONY: admin-token-generate audit-diagnostics audit-export-verify audit-keygen clean compose-config compose-down compose-logs compose-smoke compose-up demo-flow demo-seed docs-site filesystem-contract-check internal-review-packet lint local-model-demo mcp-inspector-recipes manifest-lock manifest-lock-check manifest-lock-keygen manifest-lock-sign manifest-lock-signature-check negative-review-transcripts ollama-smoke policy-test release-check release-context release-evidence release-guardrails release-packet review-candidate review-packet-bundle review-packet-consolidated reviewer-findings-check signed-evidence-demo test typecheck ui-dev

test:
	uv run pytest

lint:
	uv run ruff check .

manifest-lock:
	uv run python scripts/manifest_lock.py

manifest-lock-check:
	uv run python scripts/manifest_lock.py --check

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

policy-test:
	uv run python scripts/policy_test.py

release-evidence:
	uv run python scripts/release_evidence.py

release-packet:
	uv run python scripts/release_packet.py

review-packet-bundle:
	uv run python scripts/review_packet_bundle.py

review-packet-consolidated:
	uv run python scripts/consolidate_review_packet.py

review-candidate:
	$(MAKE) release-check
	$(MAKE) filesystem-contract-check
	$(MAKE) signed-evidence-demo
	$(MAKE) negative-review-transcripts
	$(MAKE) review-packet-bundle
	$(MAKE) review-packet-consolidated
	$(MAKE) docs-site
	@echo "Review candidate ready: var/review-packets/v0.2/GPT-5.5-Pro-consolidated"

internal-review-packet:
	uv run python scripts/internal_review_packet.py

signed-evidence-demo:
	uv run python scripts/signed_evidence_demo.py

negative-review-transcripts:
	uv run python scripts/negative_review_transcripts.py

release-context:
	@echo "repo_root=$$(pwd)"
	@echo "git_commit=$$(git rev-parse HEAD)"
	@echo "git_dirty=$$(test -z "$$(git status --short)" && echo false || echo true)"

release-check: release-context manifest-lock-check release-guardrails reviewer-findings-check policy-test test lint typecheck docs-site
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
