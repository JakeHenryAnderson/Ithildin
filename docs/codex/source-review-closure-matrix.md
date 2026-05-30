# Source Review Closure Matrix

This matrix tracks external/source review closure for the v0.2 review candidate for the v0.1
local-preview runtime boundary. Initial status is `pending external review` until a reviewer records
findings and disposition.

| Area | Files/functions to inspect | Reviewer | Date | Findings count | Blocking findings | Disposition | Closure notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `fs.read` | `apps/api/src/ithildin_api/read_tools.py`; `FilesystemReadTools.read_file`; `ReadToolExecutor.execute` | TBD | TBD | TBD | TBD | pending external review | Path normalization, hidden/sensitive denial, symlink/hardlink behavior, read limits, redaction handoff. |
| `fs.patch.propose` | `apps/api/src/ithildin_api/patches.py`; `PatchProposalService.create_proposal`; unified-diff parser/applicator helpers | TBD | TBD | TBD | TBD | pending external review | Stored proposal hash, base hash, target-path scope, binary/encoding denial, stale context handling. |
| `fs.patch.apply` | `apps/api/src/ithildin_api/patches.py`; `PatchProposalService.apply_approved_proposal`; `ApprovalService.begin_execution` | TBD | TBD | TBD | TBD | pending external review | One-time approval consumption, proposal/base/manifest/policy/schema binding, atomic replace, replay/crash behavior. |
| `http.fetch` | `apps/api/src/ithildin_api/http_tools.py`; `HttpFetchExecutor.fetch`; allowlist and resolver helpers | TBD | TBD | TBD | TBD | pending external review | URL parsing, exact allowlist, redirect revalidation, DNS/IP checks, proxy suppression, safe errors. |
| Audit export/signing | `packages/audit-core/src/ithildin_audit_core/`; signed export helpers; API export route | TBD | TBD | TBD | TBD | pending external review | JSONL digest binding, Ed25519 signature verification, public-key substitution, metadata/event ordering. |
| Manifest-lock verification | `apps/api/src/ithildin_api/manifest_lock.py`; registry startup verification | TBD | TBD | TBD | TBD | pending external review | Canonical lock payload, stale/missing entries, signature bundle verification, key ID mismatch behavior. |
| Policy preview/impact | `apps/api/src/ithildin_api/policy_preview.py`; `scripts/policy_impact.py`; policy evaluator | TBD | TBD | TBD | TBD | pending external review | Principal/resource normalization parity with runtime, fixture consistency, OPA/YAML evidence boundaries. |
| MCP ingress | `apps/mcp-server/src/ithildin_mcp_server/`; adapter list/call handlers | TBD | TBD | TBD | TBD | pending external review | Adapter thinness, schema/policy/approval/audit delegation, principal handling, no bypass path. |
| Review-console approval flow | `apps/ui/src/App.tsx`; approval review API consumers | TBD | TBD | TBD | TBD | pending external review | Binding evidence visibility, approve/deny payloads, stale/replay/expiry state clarity, no execution controls outside governed flow. |

## Closure Rule

A row is closed only when blocking findings are resolved or explicitly accepted as deferred with a
documented rationale. Closing this matrix does not make Ithildin production software; it only records
source-review disposition for the local-preview boundary.
