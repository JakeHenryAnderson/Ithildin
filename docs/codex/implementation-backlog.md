# Implementation Backlog

## MVP Track

| Task | Status | Spec |
| --- | --- | --- |
| 001 - Monorepo scaffold | Todo | [tasks/001-monorepo-scaffold.md](tasks/001-monorepo-scaffold.md) |
| 002 - Core schemas | Todo | [tasks/002-core-schemas.md](tasks/002-core-schemas.md) |
| 003 - FastAPI base service | Todo | [tasks/003-fastapi-base-service.md](tasks/003-fastapi-base-service.md) |
| 004 - Tool registry | Todo | [tasks/004-tool-registry.md](tasks/004-tool-registry.md) |
| 005 - Policy evaluator | Todo | [tasks/005-policy-evaluator.md](tasks/005-policy-evaluator.md) |
| 006 - Audit writer | Todo | [tasks/006-audit-writer.md](tasks/006-audit-writer.md) |
| 007 - Approval workflow | Todo | [tasks/007-approval-workflow.md](tasks/007-approval-workflow.md) |
| 008 - MCP adapter | Todo | [tasks/008-mcp-adapter.md](tasks/008-mcp-adapter.md) |
| 009 - Filesystem and git read tools | Todo | [tasks/009-read-tools.md](tasks/009-read-tools.md) |
| 010 - Patch proposal and apply | Todo | [tasks/010-patch-tools.md](tasks/010-patch-tools.md) |

## Definition of MVP Done

- Local Docker Compose deployment exists.
- MCP client can list and call governed tools.
- Static tool manifests are validated on startup.
- Policy evaluator is deny-default.
- Write tools require approval.
- Audit events are stored in SQLite and hash-chained JSONL.
- Path traversal, symlink escape, SSRF, approval replay, and invalid schema cases have tests.
- Documentation explains the threat model and security limitations.

