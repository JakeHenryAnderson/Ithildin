# Review Packet Source Pointers

Task 174 adds a compact map from review-packet claims to implementation files. It is a navigation aid for
source reviewers and does not close external review or change runtime behavior.

## Pointer Table

| Area | Primary files to inspect | Reviewer focus |
| --- | --- | --- |
| Patch apply | `apps/api/src/ithildin_api/patches.py`, `apps/api/src/ithildin_api/tool_calls.py`, `apps/api/src/ithildin_api/approvals.py` | stored-proposal-only apply, approval binding, attempt evidence, stale-base rejection |
| Filesystem | `apps/api/src/ithildin_api/read_tools.py`, `apps/api/src/ithildin_api/workspaces.py`, `apps/api/src/ithildin_api/filesystem_contract.py` | path confinement, symlink/hardlink denial, platform contract evidence |
| HTTP fetch | `apps/api/src/ithildin_api/http_tools.py` | URL canonicalization, allowlist checks, DNS/IP validation, redirect revalidation |
| Signed evidence | `packages/audit-core/src/ithildin_audit_core/signing.py`, `apps/api/src/ithildin_api/manifest_lock.py` | local Ed25519 bundle verification and optional signed manifest-lock enforcement |
| Policy parity | `apps/api/src/ithildin_api/policy_preview.py`, `apps/api/src/ithildin_api/tool_calls.py`, `apps/api/src/ithildin_api/decision_evidence.py` | preview/runtime resource construction, trusted principal resolution, decision evidence |
| MCP ingress | `apps/mcp-server/src/ithildin_mcp_server/server.py` | stdio adapter thinness and use of the shared governed pipeline |
| Review console | `apps/ui/src/App.tsx` | local admin evidence display, approval evidence visibility, no hidden mutation controls |

## Command

```bash
make review-packet-source-pointers
```

The command validates that each referenced source file still exists and remains listed in this document.
