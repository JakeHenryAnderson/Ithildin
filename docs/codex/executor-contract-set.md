# Executor Contract Set

This document is the v0.3-prep index for Ithildin's local-preview executor contracts. It does not
add tool powers or stronger sandbox claims. It gives reviewers a single map from each mediated
surface to its contract, implementation files, test evidence, and external-review status.

Ithildin remains a local mediation layer: agents do not receive OS access through Ithildin's exposed
tools, but the local host, local admin, trusted manifests, trusted policies, trusted registries, and
the Ithildin process are part of the trusted computing base.

## Contract Inventory

| Surface | Tools / endpoints | Contract source | Implementation pointers | Test evidence |
| --- | --- | --- | --- | --- |
| Filesystem read | `fs.list`, `fs.stat`, `fs.read`, `fs.search` | [filesystem-executor-contract.md](filesystem-executor-contract.md) | `apps/api/src/ithildin_api/read_tools.py`; `FilesystemReadTools` | `tests/test_read_tools.py`; `tests/test_security_regressions.py`; `make filesystem-contract-check` |
| Git read | `git.status`, `git.diff`, `git.log` | This document plus [filesystem-executor-contract.md](filesystem-executor-contract.md) | `apps/api/src/ithildin_api/read_tools.py`; `GitReadTools._run_git` | `tests/test_read_tools.py`; `tests/test_governed_tool_calls.py` |
| Patch proposal | `fs.patch.propose` | [filesystem-executor-contract.md](filesystem-executor-contract.md) | `apps/api/src/ithildin_api/patches.py`; `PatchProposalService.create_proposal` | `tests/test_patch_proposals.py`; `tests/test_security_regressions.py`; `tests/test_governed_tool_calls.py` |
| Patch apply | `fs.patch.apply` | [patch-apply-state-machine.md](patch-apply-state-machine.md); [filesystem-executor-contract.md](filesystem-executor-contract.md) | `PatchProposalService.apply_approved`; `ApprovalService.begin_execution`; patch apply attempt store | `tests/test_governed_tool_calls.py`; `tests/test_approval_workflow.py`; `tests/test_security_regressions.py` |
| HTTP fetch | `http.fetch` | [http-executor-contract.md](http-executor-contract.md) | `apps/api/src/ithildin_api/http_tools.py`; `HttpFetchExecutor.fetch` | `tests/test_http_tools.py`; `tests/test_security_regressions.py` |
| Audit export/signing | `/audit-events/export`, `/audit-events/export/signed`, verification helpers | [evidence-contracts.md](evidence-contracts.md); [signed-audit-exports.md](signed-audit-exports.md) | `packages/audit-core/src/ithildin_audit_core/`; API audit routes | `tests/test_audit_writer.py`; `tests/test_audit_signing.py`; `tests/test_api_service.py` |
| Manifest lock verification | `tool-manifests.lock.json`; optional local signature | [evidence-contracts.md](evidence-contracts.md); [signed-manifest-locks.md](signed-manifest-locks.md) | `apps/api/src/ithildin_api/manifest_lock.py`; `ToolRegistry.load` | `tests/test_tool_registry.py`; release guardrails |
| Policy preview/parity | `/policy/preview`, `make policy-parity`, policy impact scripts | [policy-parity-harness.md](policy-parity-harness.md); [opa-parity-decision.md](opa-parity-decision.md) | `policy_preview.py`; `policy.py`; `scripts/policy_parity.py` | `tests/test_api_service.py`; `tests/test_policy_parity.py`; `make policy-test`; `make policy-parity` |
| MCP ingress | stdio `tools/list`, `tools/call` | [mcp-ingress-bypass-audit.md](mcp-ingress-bypass-audit.md) | `apps/mcp-server/src/ithildin_mcp_server/` | `tests/test_mcp_adapter.py`; `tests/test_mcp_integration_flow.py` |
| Review console evidence | Local admin UI approval/audit/status panels | [review-console-assurance.md](review-console-assurance.md) | `apps/ui/src/App.tsx`; API status/approval/audit routes | `npm run typecheck --prefix apps/ui`; `npm run build --prefix apps/ui`; API tests |

## Git Read Contract

Git read tools inherit the filesystem contract for path resolution and workspace confinement. They
are read-only wrappers around fixed command shapes:

- `git.status`: `git status --porcelain=v1`
- `git.diff`: `git diff --no-ext-diff --`
- `git.log`: bounded `git log` summaries

Callers cannot supply arbitrary flags, environment variables, shell fragments, remotes, refspecs,
subcommands, hooks, or output paths. The commands execute only inside a path that resolves under the
configured workspace root and is validated as a Git repository. Output is bounded by configured
limits and treated as evidence returned through the governed pipeline.

Git tools do not support mutation, fetch/push/pull, checkout, worktree changes, hook execution,
submodule update, credential access, or remote network access.

## Cross-Cutting Invariants

Every executor path listed here must preserve these local-preview invariants:

- registry lookup and manifest validation happen before policy execution;
- tool inputs are JSON Schema validated before execution;
- principal and workspace data are normalized through trusted registries where applicable;
- default YAML policy remains deny-by-default and approval-gates write actions;
- approval-gated writes bind to stored proposal, manifest, policy, schema, principal, request, base
  hash, target path, and expiry evidence;
- audit events avoid file contents, diffs, response bodies, private keys, admin tokens, and secrets;
- runtime errors return safe denials or safe failures without leaking sensitive content;
- no executor introduces shell execution, Docker socket access, Kubernetes tooling, browser
  automation, arbitrary HTTP methods/headers/bodies, broad network access, or broad filesystem
  writes.

## Review Status

This contract set is a review map, not final assurance. The current status remains pending external
review in [source-review-closure-matrix.md](source-review-closure-matrix.md). Internal Codex and
subagent reviews can create or close internal findings, but they cannot close external/source review
rows.
