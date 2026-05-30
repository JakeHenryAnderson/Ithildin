# Source Review Closure Matrix

This matrix tracks external/source review closure for the v0.2 review candidate for the v0.1
local-preview runtime boundary. Initial status is `pending external review` until a reviewer records
findings and disposition.

| Area | Files/functions to inspect | Reviewer | Date | Findings count | Blocking findings | Disposition | Closure notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `fs.read` | `apps/api/src/ithildin_api/read_tools.py`; `FilesystemReadTools.read_file`; `ReadToolExecutor.execute`; `docs/codex/filesystem-executor-contract.md` | Codex internal source review pass 1 | 2026-05-30 | 1 | 0 | internal reviewed; pending external review | ISR-002 is addressed by Task 080 filesystem contract and capability check; external review remains pending. Path normalization, hidden/sensitive denial, symlink/hardlink behavior, read limits, and redaction handoff inspected. |
| `fs.patch.propose` | `apps/api/src/ithildin_api/patches.py`; `PatchProposalService.create_proposal`; unified-diff parser/applicator helpers; `docs/codex/filesystem-executor-contract.md` | Codex internal source review pass 1 | 2026-05-30 | 1 | 0 | internal reviewed; pending external review | ISR-002 also applies to proposal target path semantics and is addressed by Task 080 contract/regressions; external review remains pending. Stored proposal hash, base hash, target-path scope, binary/encoding denial, and stale context handling inspected. |
| `fs.patch.apply` | `apps/api/src/ithildin_api/patches.py`; `PatchProposalService.apply_approved`; `ApprovalService.begin_execution`; `docs/codex/filesystem-executor-contract.md` | Codex internal source review pass 1 | 2026-05-30 | 2 | 0 | internal reviewed; pending external review | ISR-001 is addressed by Task 079 read-only recovery evidence; ISR-002 is addressed by Task 080 filesystem contract and capability check. One-time approval consumption, proposal/base/manifest/policy/schema binding, atomic replace, replay/crash behavior inspected. |
| `http.fetch` | `apps/api/src/ithildin_api/http_tools.py`; `HttpFetchExecutor.fetch`; allowlist and resolver helpers | Codex internal source review pass 1 | 2026-05-30 | 0 | 0 | internal reviewed; pending external review | URL parsing, exact allowlist, redirect revalidation, DNS/IP checks, proxy suppression, and safe errors inspected. |
| Audit export/signing | `packages/audit-core/src/ithildin_audit_core/`; signed export helpers; API export route | Codex internal source review pass 1 | 2026-05-30 | 0 | 0 | internal reviewed; pending external review | JSONL digest binding, Ed25519 signature verification, public-key substitution, metadata/event ordering inspected. |
| Manifest-lock verification | `apps/api/src/ithildin_api/manifest_lock.py`; registry startup verification | Codex internal source review pass 1 | 2026-05-30 | 0 | 0 | internal reviewed; pending external review | Canonical lock payload, stale/missing entries, signature bundle verification, and key ID mismatch behavior inspected. |
| Policy preview/impact | `apps/api/src/ithildin_api/policy_preview.py`; `scripts/policy_impact.py`; policy evaluator | Codex internal source review pass 1 | 2026-05-30 | 0 | 0 | internal reviewed; pending external review | Principal/resource normalization parity with runtime, fixture consistency, and OPA/YAML evidence boundaries inspected. |
| MCP ingress | `apps/mcp-server/src/ithildin_mcp_server/`; adapter list/call handlers | Codex internal source review pass 1 | 2026-05-30 | 0 | 0 | internal reviewed; pending external review | Adapter thinness, schema/policy/approval/audit delegation, principal handling, and no-bypass path inspected. |
| Review-console approval flow | `apps/ui/src/App.tsx`; approval review API consumers | Codex internal source review pass 1 | 2026-05-30 | 0 | 0 | internal reviewed; pending external review | Binding evidence visibility, approve/deny payloads, stale/replay/expiry state clarity, and lack of direct execution controls inspected. |

## Closure Rule

A row is closed only when blocking findings are resolved or explicitly accepted as deferred with a
documented rationale. Closing this matrix does not make Ithildin production software; it only records
source-review disposition for the local-preview boundary.
