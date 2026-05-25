# Task 001 - Monorepo Scaffold

## Goal

Create the initial repository structure and developer tooling.

## Scope

- `apps/api`
- `apps/ui`
- `apps/mcp-server`
- `packages/schemas`
- `packages/policy-core`
- `packages/audit-core`
- `packages/tool-sdk`
- `tools/fs`
- `tools/git`
- `deploy`
- `policies`
- `tool-manifests`
- `tests`

## Acceptance Criteria

- `make test`, `make lint`, and `make typecheck` targets exist, even if initially minimal.
- Python dependencies are managed consistently.
- Frontend app can be started separately.
- Empty runtime directories are represented with `.gitkeep`.
- No Docker socket mount is introduced.

