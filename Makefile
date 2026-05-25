.PHONY: clean lint test typecheck ui-dev

test:
	uv run pytest

lint:
	uv run ruff check .

typecheck:
	uv run mypy
	npm run typecheck --prefix apps/ui

ui-dev:
	npm run dev --prefix apps/ui

clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache
	rm -rf apps/ui/dist apps/ui/node_modules
