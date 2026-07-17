# Local Preview Deployment

This local preview deployment runs the Ithildin API and review console for demos and
development validation. It is not production hosting.

## Start

Install and launch Docker Desktop first. On macOS, follow Docker's official install flow
for your chip architecture, then verify:

```sh
docker --version
docker compose version
docker info
```

If `docker` is not found or `docker info` cannot connect to the daemon, open Docker Desktop
from Applications and wait until it reports that the engine is running.
If the CLI is installed but Docker returns HTTP 500 while the dashboard says "Starting the
Docker Engine", quit Docker Desktop, reopen it, and use Docker Desktop's Troubleshoot panel
if the engine does not become ready.

```sh
make demo-seed
make compose-up
make compose-smoke
make demo-flow
```

Open `http://127.0.0.1:5173` and use the token from `.env.example`, or copy
`.env.example` to `.env` and change `ITHILDIN_ADMIN_TOKEN`.
Keep `ITHILDIN_HTTP_ALLOWLIST` empty unless the demo needs a specific external fetch
destination; entries are exact hosts or scheme-qualified hosts, not wildcards.
Tool output redaction is always enabled. Use `ITHILDIN_REDACTION_EXTRA_KEYS` for additional
JSON field names and `ITHILDIN_REDACTION_EXTRA_PATTERNS` for newline-separated regex patterns.
Trusted tool manifests are hash-pinned by `tool-manifests.lock.json`; run `make manifest-lock`
after intentionally changing a manifest.
The default policy engine is the local YAML evaluator. To prototype an OPA sidecar, set
`ITHILDIN_POLICY_ENGINE=opa`, `ITHILDIN_OPA_URL=http://<opa-host>:8181`, and keep
`ITHILDIN_OPA_DECISION_PATH=/v1/data/ithildin/decision`. OPA mode verifies
`policies/opa/bundle.lock.json` before startup and reports the verified bundle hash in policy
status. OPA is optional and is not started by the local Compose stack in this task.

## Services

- `ithildin-api` runs `uvicorn ithildin_api.app:app` on `127.0.0.1:8000`.
- `ithildin-ui` serves the built review console on `127.0.0.1:5173`.
- Optional profile `ithildin-node` runs the signed configuration and heartbeat client with no
  inbound port or runner authority. See `deploy/node/README.md`; it is not started by `compose-up`.

The Compose stack mounts only:

- `tool-manifests/` read-only;
- `policies/` read-only;
- `workspaces/`;
- `var/`.

It does not mount the Docker socket.
Kubernetes and Docker agent powers are intentionally deferred; Docker is used here only to run
the local demo stack.

## Release Check

Before handing off a local preview build, run:

```sh
make release-check
```

This verifies the manifest lock, Python tests, lint, Python/UI type checks, and the UI production
build.

## Demo Flow

`make demo-flow` assumes the Compose stack is already running. It reseeds
`workspaces/demo/`, then verifies:

- API health, tool listing, policy preview, approvals, audit verification, and audit export;
- governed `fs.read`;
- governed output redaction for a seeded demo secret;
- `http.fetch` registration and network-resource policy preview without requiring external
  internet access;
- governed `fs.patch.propose`;
- approval creation and approval through the admin API;
- approved `fs.patch.apply`;
- a valid audit hash chain after the flow.

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
