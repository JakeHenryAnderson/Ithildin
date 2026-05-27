# Ithildin

Ithildin is a local-first governed MCP/tool gateway for AI agents.

The project goal is to let AI agents use local tools through narrow, policy-scoped, auditable interfaces instead of unrestricted endpoint access.

## Product Thesis

Ithildin is not an autonomous agent platform, an EDR product, an MDM product, or a replacement shell.

It is a trusted mediation layer between untrusted AI reasoning and sensitive local systems:

```text
Agent / local LLM
  -> MCP tools/list + tools/call
  -> Ithildin MCP Gateway
  -> schema validation + policy decision
  -> approval + audit
  -> sandboxed governed tools
  -> endpoint workspace / APIs / local services
```

The agent never receives direct OS access. Ithildin owns validation, policy, approval, execution, and evidence.

## MVP Target

A security-conscious developer can run Ithildin locally, connect an MCP-capable agent, expose a few safe file/git/http tools, require approval for writes, and inspect a trustworthy audit log.

## Repo Map

- `docs/obsidian/` - Obsidian-friendly strategy and architecture notes.
- `docs/codex/` - Codex-friendly implementation brief and task specs.
- `docs/adr/` - Architecture decision records.
- `docs/research/` - source verification and research notes.
- `apps/` - future application services.
- `packages/` - future shared libraries.
- `tools/` - future governed tool implementations.
- `deploy/` - future Docker Compose and deployment assets.
- `policies/` - future policy examples and local policy files.
- `tool-manifests/` - future trusted tool manifest definitions.

## Development Commands

- `make test` - run Python tests.
- `make lint` - run Python lint checks.
- `make typecheck` - run Python and UI type checks.
- `make ui-dev` - start the Vite UI app.

## Local Demo

The local Docker Compose demo runs the API and review console with a seeded workspace:

- `make demo-seed` - copy tracked demo files into ignored `workspaces/demo/`.
- `make compose-up` - build and start the local API/UI stack.
- `make compose-smoke` - check API health, authenticated tool listing, and UI reachability.
- `make demo-flow` - run a governed read, patch proposal, approval, apply, and audit check.
- `make compose-down` - stop the stack.

Use the admin token in `.env.example`, or copy `.env.example` to `.env` and change it.
The review console is served at `http://127.0.0.1:5173`.
Docker is only used for the local demo stack; Kubernetes support is deferred.
`http.fetch` is disabled until `ITHILDIN_HTTP_ALLOWLIST` names exact destinations such as
`example.com`, `example.com:443`, or `https://example.com`.
Governed tool outputs are redacted before they are returned to agents using an always-on
baseline for common tokens, secrets, passwords, cookies, and private keys; add local patterns
with `ITHILDIN_REDACTION_EXTRA_KEYS` and `ITHILDIN_REDACTION_EXTRA_PATTERNS`.

MCP is launched by an MCP client rather than as a persistent Compose service:

```sh
uv run python -m ithildin_mcp_server
```

## Core Invariant

No agent-originated action reaches the endpoint unless:

1. the caller is authenticated;
2. the tool is registered;
3. the input matches schema;
4. the resource is in scope;
5. policy allows it or requires approval;
6. approval is satisfied when required;
7. execution happens inside the declared sandbox;
8. the full decision and result are logged.

## Start Reading

Begin with [docs/obsidian/00-index.md](docs/obsidian/00-index.md), then use [docs/codex/project-brief.md](docs/codex/project-brief.md) when starting implementation work.
