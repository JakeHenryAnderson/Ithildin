# Local Model Demo

Ithildin can be used beside a host-run local model, such as an Ollama model connected through an
MCP-capable client. Ithildin does not run Ollama, proxy prompts, manage model lifecycle, or grant
extra tool powers to local models.

## Smoke Check

Run:

```sh
make ollama-smoke
```

The command exits successfully when Ollama is unavailable, not running, or has no local models. In
those cases it prints a skip message so release checks and demos remain repeatable on machines
without Ollama.

## MCP Client Wiring

Run:

```sh
make local-model-demo
```

The command prints a host-side MCP server configuration using:

```sh
uv run python -m ithildin_mcp_server
```

Use the same `.env` settings as the API/UI stack. The seeded `model:ollama-local` principal is
present for audit and demo identity evidence, but the MCP adapter still uses the governed
`agent:mcp-local` identity for tool calls in this local-preview release.

## Boundaries

- No Ollama service is added to Docker Compose.
- No LLM proxy or prompt capture API is added.
- No shell, Docker, Kubernetes, or broad filesystem tool powers are added.
- Existing role-aware tool visibility, policy, approval, redaction, and audit behavior still apply.
