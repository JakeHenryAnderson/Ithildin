---
title: Runtime and Sandboxing
tags: [ithildin, runtime, docker]
---

# Runtime and Sandboxing

## Local Architecture

```text
docker compose
├── ithildin-api
├── ithildin-mcp
├── ithildin-policy
├── ithildin-ui
├── ithildin-db
├── ithildin-executor
└── optional-ollama
```

## Implementation Rule

Do not mount the Docker socket into Ithildin.

## Docker Requirements

| Control | Requirement |
| --- | --- |
| Non-root users | Mandatory. |
| `cap_drop: ALL` | Mandatory where possible. |
| `no-new-privileges` | Mandatory. |
| Read-only root filesystem | Mandatory where possible. |
| Explicit bind mounts | Mandatory. |
| Docker socket | Never mount. |
| Network disabled/internal | Default for tools. |
| CPU/memory limits | Add early. |
| Secrets | Use environment only for dev; stronger handling later. |

## Local Directories

- `./workspaces/` - explicitly mounted test workspaces.
- `./policies/` - local policies.
- `./tool-manifests/` - trusted tool definitions.
- `./var/logs/` - local audit JSONL.
- `./var/db/` - SQLite data.

