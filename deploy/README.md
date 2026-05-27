# Local Demo Deployment

Task 015 provides a local Docker Compose deployment for the Ithildin API and review console.
It is intended for demos and development validation, not production hosting.

## Start

```sh
make demo-seed
make compose-up
make compose-smoke
```

Open `http://127.0.0.1:5173` and use the token from `.env.example`, or copy
`.env.example` to `.env` and change `ITHILDIN_ADMIN_TOKEN`.

## Services

- `ithildin-api` runs `uvicorn ithildin_api.app:app` on `127.0.0.1:8000`.
- `ithildin-ui` serves the built review console on `127.0.0.1:5173`.

The Compose stack mounts only:

- `tool-manifests/` read-only;
- `policies/` read-only;
- `workspaces/`;
- `var/`.

It does not mount the Docker socket.

## MCP

MCP is intentionally not a long-running Compose service in this task. Stdio MCP servers are
normally launched by an MCP client, so use the host command with the same `.env` settings:

```sh
uv run python -m ithildin_mcp_server
```

## Stop

```sh
make compose-down
```
