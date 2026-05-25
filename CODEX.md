# Codex Project Context

Use this file as the first stop for future Codex sessions.

## Mission

Build Ithildin as a local-first governed MCP/tool gateway. Keep the project governance-first, not autonomy-first.

## Non-Negotiables

- Deny by default.
- Treat LLM output as proposed action, never authority.
- Do not expose direct OS, shell, Docker socket, home directory, cloud credentials, or secret access in the MVP.
- Tool manifests are trusted policy inputs; MCP descriptions and annotations are only model-facing hints.
- Writes require human approval unless an explicit policy safely narrows the scope.
- Every policy decision, approval, execution attempt, and result must be auditable.
- Fail closed if policy, approval state, or audit writing is unavailable.

## First Implementation Track

Follow [docs/codex/implementation-backlog.md](docs/codex/implementation-backlog.md).

Start with:

1. [Task 001 - Monorepo Scaffold](docs/codex/tasks/001-monorepo-scaffold.md)
2. [Task 002 - Core Schemas](docs/codex/tasks/002-core-schemas.md)
3. [Task 003 - FastAPI Base Service](docs/codex/tasks/003-fastapi-base-service.md)

## Preferred Stack

- Backend: Python, FastAPI, Pydantic.
- Policy: deterministic YAML evaluator first; OPA sidecar later.
- UI: React + Vite.
- Persistence: SQLite for MVP; Postgres optional later.
- Audit: SQLite index plus hash-chained JSONL.
- Packaging: Docker Compose.
- Dev tools: pytest, Ruff, mypy or pyright, pre-commit.

## Editing Guidance

- Keep changes small and security-focused.
- Add tests with every behavioral change.
- Preserve docs as living design constraints.
- Avoid implementing deferred features unless a task explicitly promotes them.

## Deferred Features

Do not build these in the MVP:

- general shell execution;
- Docker socket access;
- arbitrary browser automation;
- email/calendar mutation;
- plugin marketplace;
- autonomous multi-agent orchestration;
- cloud fleet management;
- EDR/MDM replacement features;
- natural-language policy authoring.

