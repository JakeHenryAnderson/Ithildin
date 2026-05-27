COMPOSE ?= docker compose
COMPOSE_FILE ?= deploy/docker-compose.yml
COMPOSE_ENV_FILE ?= $(shell if [ -f .env ]; then echo .env; else echo .env.example; fi)

.PHONY: clean compose-config compose-down compose-logs compose-smoke compose-up demo-flow demo-seed lint manifest-lock manifest-lock-check test typecheck ui-dev

test:
	uv run pytest

lint:
	uv run ruff check .

manifest-lock:
	uv run python scripts/manifest_lock.py

manifest-lock-check:
	uv run python scripts/manifest_lock.py --check

typecheck:
	uv run mypy
	npm run typecheck --prefix apps/ui

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

clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache
	rm -rf apps/ui/dist apps/ui/node_modules
