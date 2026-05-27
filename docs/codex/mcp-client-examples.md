# MCP Client Examples

These examples launch the local stdio MCP adapter. The command runs on the host with the
environment you provide, so treat it as security-sensitive local software.

Ithildin v0.1 exposes only governed tools from the trusted manifest registry. It does not provide a
remote MCP server, shell access, Docker/Kubernetes tools, browser automation, broad filesystem
writes, or production identity.

## Host Command

Run from the repository root:

```sh
uv run python -m ithildin_mcp_server
```

Use the same `.env` settings as the API, especially workspace, manifest, policy, principal registry,
audit, and admin-token settings. The MCP adapter uses `agent:mcp-local` by default and is filtered by
the local principal registry and role visibility rules.

## Generic stdio JSON

Use this shape for MCP clients that accept a JSON server configuration:

```json
{
  "mcpServers": {
    "ithildin-local": {
      "command": "uv",
      "args": ["run", "python", "-m", "ithildin_mcp_server"],
      "cwd": "/absolute/path/to/Ithildin",
      "env": {
        "ITHILDIN_ADMIN_TOKEN": "replace-with-a-local-token",
        "ITHILDIN_ALLOW_DEV_ADMIN_TOKEN": "false",
        "ITHILDIN_WORKSPACE_ROOT": "workspaces/demo"
      }
    }
  }
}
```

Do not paste the sample admin token into a public or shared client configuration. If you enable
`ITHILDIN_ALLOW_DEV_ADMIN_TOKEN=true` for a local demo, `/system/status` and the review console will
show a warning.

## Claude Desktop-style stdio

Many local MCP clients use the same stdio fields:

```json
{
  "mcpServers": {
    "ithildin-local": {
      "command": "uv",
      "args": ["run", "python", "-m", "ithildin_mcp_server"],
      "cwd": "/absolute/path/to/Ithildin"
    }
  }
}
```

Keep the workspace root narrow. The agent can only reach registered, schema-valid, policy-cleared
tools, but Ithildin is still a mediation layer, not a kernel sandbox.

## Local Model Demo

For an Ollama-backed local model client, run:

```sh
make ollama-smoke
make local-model-demo
```

The demo prints host-side wiring guidance. Ithildin does not run, manage, or proxy models in v0.1.
