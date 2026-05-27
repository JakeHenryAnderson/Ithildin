# Implementation Backlog

## Completed Local Preview Track

| Task | Status | Spec |
| --- | --- | --- |
| 001 - Monorepo scaffold | Done | [tasks/001-monorepo-scaffold.md](tasks/001-monorepo-scaffold.md) |
| 002 - Core schemas | Done | [tasks/002-core-schemas.md](tasks/002-core-schemas.md) |
| 003 - FastAPI base service | Done | [tasks/003-fastapi-base-service.md](tasks/003-fastapi-base-service.md) |
| 004 - Tool registry | Done | [tasks/004-tool-registry.md](tasks/004-tool-registry.md) |
| 005 - Policy evaluator | Done | [tasks/005-policy-evaluator.md](tasks/005-policy-evaluator.md) |
| 006 - Audit writer | Done | [tasks/006-audit-writer.md](tasks/006-audit-writer.md) |
| 007 - Approval workflow | Done | [tasks/007-approval-workflow.md](tasks/007-approval-workflow.md) |
| 008 - MCP adapter | Done | [tasks/008-mcp-adapter.md](tasks/008-mcp-adapter.md) |
| 009 - Filesystem and git read tools | Done | [tasks/009-read-tools.md](tasks/009-read-tools.md) |
| 010 - Patch proposal and apply | Done | [tasks/010-patch-tools.md](tasks/010-patch-tools.md) |
| 011 - Approval-gated patch apply | Done | Sprint checkpoint |
| 012 - Review console | Done | Sprint checkpoint |
| 013 - Audit verification and export | Done | Sprint checkpoint |
| 014 - Policy preview | Done | Sprint checkpoint |
| 015 - Local demo deployment | Done | Sprint checkpoint |
| 016 - Local deployment verification | Done | Sprint checkpoint |
| 017 - Governed HTTP fetch | Done | Sprint checkpoint |
| 018 - Tool output redaction | Done | Sprint checkpoint |
| 019 - MCP integration flow | Done | Sprint checkpoint |
| 020 - Security regression suite | Done | Sprint checkpoint |
| 021 - Policy evidence | Done | Sprint checkpoint |
| 022 - OPA policy prototype | Done | Sprint checkpoint |
| 023 - Manifest lock verification | Done | Sprint checkpoint |
| 024 - OPA bundle verification | Done | Sprint checkpoint |
| 025 - Review console trust status | Done | Sprint checkpoint |
| 026 - Local preview release guide | Done | This document |

## Next Candidate Track

| Area | Status | Notes |
| --- | --- | --- |
| Identity/RBAC seed | Planned | Local principal registry and role-aware filtering. |
| Ops backbone | Planned | Postgres option and OpenTelemetry export prototype. |
| Release packaging | Planned | Documentation site, source verification, and v0.1 OSS prep. |
| Local model demo | Planned | Ollama-based demo packaging without broadening tool powers. |

## Definition of MVP Done

- Local Docker Compose deployment exists.
- MCP client can list and call governed tools.
- Static tool manifests are validated on startup.
- Policy evaluator is deny-default.
- Write tools require approval.
- Audit events are stored in SQLite and hash-chained JSONL.
- Path traversal, symlink escape, SSRF, approval replay, and invalid schema cases have tests.
- Documentation explains the threat model and security limitations.
- `make release-check` passes before local-preview handoff.
