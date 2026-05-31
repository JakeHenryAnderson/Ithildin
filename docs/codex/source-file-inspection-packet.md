# Source File Inspection Packet

Task 158 gives source reviewers one compact map of the files and functions that matter for v0.5
source-review closure. It is a pointer packet only; it does not prove correctness and does not close
external review rows.

Use this packet with [source-review-runbook-v2.md](source-review-runbook-v2.md),
[source-review-closure-matrix.md](source-review-closure-matrix.md), and the area-specific checklists
from Tasks 159-165.

## Inspection Table

| Area | Primary files/functions | Contract / tests |
| --- | --- | --- |
| Patch apply | `apps/api/src/ithildin_api/patches.py`: `PatchProposalService.apply_approved`, `PatchProposalService.approval_scope`, `PatchProposalService.approval_review`, `PatchProposalStore.create_apply_attempt`, `_atomic_write_text`; `apps/api/src/ithildin_api/approvals.py`: `ApprovalService.begin_execution`, `ApprovalService.complete_execution`; `apps/api/src/ithildin_api/tool_calls.py`: `GovernedToolCallService._execute_approved_patch` | [patch-apply-state-machine.md](patch-apply-state-machine.md); `tests/test_governed_tool_calls.py`; `tests/test_approval_workflow.py`; `tests/test_security_regressions.py` |
| Filesystem reads | `apps/api/src/ithildin_api/read_tools.py`: `FilesystemReadTools.resolve_existing_path`, `FilesystemReadTools.read_file`, `FilesystemReadTools.search`, `FilesystemReadTools._ensure_under_workspace`, `FilesystemReadTools._ensure_not_sensitive`, `FilesystemReadTools._ensure_not_hardlinked_file`, `_reject_ambiguous_path_input` | [filesystem-executor-contract.md](filesystem-executor-contract.md); `tests/test_read_tools.py`; `tests/test_security_regressions.py`; `make filesystem-contract-check` |
| Git reads | `apps/api/src/ithildin_api/read_tools.py`: `GitReadTools.status`, `GitReadTools.diff`, `GitReadTools.log`, `GitReadTools._repo_path`, `GitReadTools._run_git` | [executor-contract-set.md](executor-contract-set.md); `tests/test_read_tools.py`; `tests/test_governed_tool_calls.py` |
| HTTP fetch | `apps/api/src/ithildin_api/http_tools.py`: `HttpFetchExecutor.fetch`, `_ensure_allowed_destination`, `_validated_resolution`, `_open_response`, `parse_http_url`, `http_resource_from_url`, `_parse_allowlist_entry`, `_normalize_host`, `_looks_like_obfuscated_ip`, `_is_blocked_ip`, `_read_bounded` | [http-executor-contract.md](http-executor-contract.md); `tests/fixtures/http_canonicalization_corpus.json`; `tests/test_http_tools.py` |
| Signed audit export | `packages/audit-core/src/ithildin_audit_core/signing.py`: `signed_audit_export_bundle`, `verify_signed_audit_export_bundle`, `verify_exported_events_jsonl`, `_signature_payload`, `_metadata_matches_verification`, `_event_hash_from_event`; `packages/audit-core/src/ithildin_audit_core/writer.py`: audit export/verification helpers | [evidence-contracts.md](evidence-contracts.md); [signed-audit-exports.md](signed-audit-exports.md); `tests/test_audit_writer.py`; `tests/test_signed_evidence_demo.py` |
| Manifest-lock signatures | `apps/api/src/ithildin_api/manifest_lock.py`: `write_manifest_lock_signature`, `verify_manifest_lock_signature`, `manifest_lock_signature_status`, `require_manifest_lock_signature`; `apps/api/src/ithildin_api/registry.py`: `ToolRegistry.load` | [signed-manifest-locks.md](signed-manifest-locks.md); `tests/test_tool_registry.py`; `make manifest-lock-check` |
| Policy preview/runtime parity | `apps/api/src/ithildin_api/policy_preview.py`: `PolicyPreviewService.preview`; `apps/api/src/ithildin_api/tool_calls.py`: `GovernedToolCallService.call_tool`, `_audit_decision`; `apps/api/src/ithildin_api/decision_evidence.py`; `scripts/policy_parity.py` | [policy-parity-harness.md](policy-parity-harness.md); `tests/test_policy_parity.py`; `make policy-parity` |
| MCP ingress | `apps/mcp-server/src/ithildin_mcp_server/server.py`: `IthildinMcpAdapter.list_tools`, `IthildinMcpAdapter.call_tool`, `create_adapter`, `create_mcp_server`, `run_stdio_server` | [mcp-ingress-bypass-audit.md](mcp-ingress-bypass-audit.md); `tests/test_mcp_adapter.py`; `tests/test_mcp_integration_flow.py` |
| Review console evidence | `apps/ui/src/App.tsx`: approval list/detail rendering, binding evidence display, approve/deny handlers, trust/status panels; `apps/api/src/ithildin_api/app.py`: approval, audit, system status, diagnostics routes | [review-console-assurance.md](review-console-assurance.md); `npm run typecheck --prefix apps/ui`; `npm run build --prefix apps/ui` |
| Release/evidence automation | `scripts/release_evidence.py`, `scripts/release_guardrails.py`, `scripts/review_packet_bundle.py`, `scripts/consolidate_review_packet.py`, `scripts/capability_expansion_gate.py`, `scripts/tool_surface_invariant_gate.py`, `scripts/evidence_confusion_gate.py`, `scripts/external_review_closure_gate.py` | [release-evidence-schema.md](release-evidence-schema.md); [capability-expansion-gate.md](capability-expansion-gate.md); `make release-check`; `make review-candidate` |

## Reviewer Rules

- Inspect source and tests together.
- Cite file/function names in every finding.
- Use [reviewer-finding-template.md](reviewer-finding-template.md) for actionable findings.
- Do not mark external review rows closed from packet review alone.
- Treat any proposed shell, Docker, Kubernetes, browser, arbitrary HTTP, broad filesystem write,
  remote MCP, production identity, runtime Postgres, hosted telemetry, or plugin SDK work as a
  boundary decision, not a normal source-review fix.

## Handoff Note

This packet is intentionally redundant with the closure matrix. The matrix records status; this file
helps reviewers find code quickly.
