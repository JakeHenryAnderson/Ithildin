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
- `docs/codex/` - Codex-friendly implementation brief, task specs, and release notes.
- `docs/adr/` - Architecture decision records.
- `docs/research/` - source verification and research notes.
- `apps/api/` - FastAPI control plane for admin APIs, approvals, tools, policy, and audit.
- `apps/mcp-server/` - stdio MCP adapter backed by the governed tool-call pipeline.
- `apps/ui/` - local React review console.
- `packages/` - shared schemas, policy, audit, and SDK packages.
- `deploy/` - local Docker Compose demo assets.
- `policies/` - YAML policy and optional OPA bundle evidence.
- `tool-manifests/` - trusted YAML tool manifests pinned by `tool-manifests.lock.json`.

## Development Commands

- `make test` - run Python tests.
- `make lint` - run Python lint checks.
- `make typecheck` - run Python and UI type checks.
- `make manifest-lock` - regenerate `tool-manifests.lock.json` after intentional manifest edits.
- `make manifest-lock-check` - verify trusted tool manifests still match the committed lock.
- `make release-check` - run manifest lock verification, tests, lint, typecheck, and UI build.
- `make docs-site` - build a small local static docs site under ignored `site/`.
- `make ollama-smoke` - detect a host Ollama install and local models, skipping safely if absent.
- `make local-model-demo` - print host-side MCP wiring for an Ollama-backed local model client.
- `make ui-dev` - start the Vite UI app.

## Local Demo

The local Docker Compose demo runs the API and review console with a seeded workspace:

- `make demo-seed` - copy tracked demo files into ignored `workspaces/demo/`.
- `make compose-up` - build and start the local API/UI stack.
- `make compose-smoke` - check API health, authenticated tool listing, and UI reachability.
- `make demo-flow` - run governed reads, redaction, patch proposal, approval, apply, and audit checks.
- `make compose-down` - stop the stack.

Use the admin token in `.env.example`, or copy `.env.example` to `.env` and change it.
The review console is served at `http://127.0.0.1:5173`.
Docker is only used for the local demo stack; Kubernetes support is deferred.
Tool manifests are hash-pinned by default; run `make manifest-lock` only after intentional
manifest changes.
`http.fetch` is disabled until `ITHILDIN_HTTP_ALLOWLIST` names exact destinations such as
`example.com`, `example.com:443`, or `https://example.com`.
Governed tool outputs are redacted before they are returned to agents using an always-on
baseline for common tokens, secrets, passwords, cookies, and private keys; add local patterns
with `ITHILDIN_REDACTION_EXTRA_KEYS` and `ITHILDIN_REDACTION_EXTRA_PATTERNS`.
OPA is optional. When `ITHILDIN_POLICY_ENGINE=opa`, Ithildin verifies
`policies/opa/bundle.lock.json` before startup and reports bundle evidence in policy/system status.
SQLite is the runtime storage backend for v0.1. Postgres settings are readiness/status evidence only.
OpenTelemetry is opt-in preview instrumentation and is disabled by default.

MCP is launched by an MCP client rather than as a persistent Compose service:

```sh
uv run python -m ithildin_mcp_server
```

For local model demos, run `make local-model-demo`; Ollama remains a host-side client companion,
not an Ithildin-managed service or tool power.

Build local handoff docs with:

```sh
make docs-site
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

Begin with [docs/codex/local-preview-release.md](docs/codex/local-preview-release.md), then use
[docs/obsidian/00-index.md](docs/obsidian/00-index.md) and
[docs/codex/project-brief.md](docs/codex/project-brief.md) when starting implementation work.
