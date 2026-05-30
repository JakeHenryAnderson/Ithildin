# Internal Source Review Pass 1

Date: 2026-05-30

Reviewer: Codex internal source review pass 1

Scope: v0.2 review candidate for the v0.1 local-preview runtime boundary.

## Overall Judgment

This pass inspected the highest-risk local-preview implementation surfaces against the source
review closure matrix. It found no critical or high blocking findings. The project is ready for
external source review, not broader public/security-product positioning.

This is an internal adversarial pass, not an independent external audit. It does not prove source
correctness, OS isolation, production identity, immutable audit custody, or production-security
readiness.

## Targeted Test Evidence

Targeted tests were run while reviewing source:

- `uv run pytest tests/test_governed_tool_calls.py tests/test_approval_workflow.py tests/test_security_regressions.py` - 45 passed.
- `uv run pytest tests/test_read_tools.py tests/test_patch_proposals.py tests/test_http_tools.py` - 42 passed.
- `uv run pytest tests/test_audit_writer.py tests/test_tool_registry.py tests/test_api_service.py tests/test_policy_test_harness.py tests/test_policy_impact.py` - 108 passed.
- `uv run pytest tests/test_mcp_adapter.py tests/test_mcp_integration_flow.py` - 14 passed.

## Findings Summary

| Finding | Severity | Area | Blocking status | Disposition |
| --- | --- | --- | --- | --- |
| ISR-001 | medium | Patch apply crash consistency | Not blocking external review; read-only evidence added in Task 079 | Addressed by Task 079; pending external review |
| ISR-002 | medium | Cross-platform filesystem semantics | Not blocking external review; Task 080 documents platform support and capability evidence | Addressed by Task 080; pending external review |

Blocking findings: 0.

## Reviewed Areas

### `fs.patch.apply` Approval Binding And Atomic Apply

Files/functions inspected:

- `apps/api/src/ithildin_api/tool_calls.py`: `GovernedToolCallService.call_tool`, `_execute_approved_patch`.
- `apps/api/src/ithildin_api/patches.py`: `PatchProposalService.approval_scope`, `apply_approved`, `_proposal_for_approval`, `_verify_approval_scope`, `_apply_proposal`, `_atomic_write_text`.
- `apps/api/src/ithildin_api/approvals.py`: `ApprovalService.begin_execution`, `complete_execution`, `ApprovalStore.compare_and_set_status`.
- Relevant tests: `tests/test_governed_tool_calls.py`, `tests/test_approval_workflow.py`, `tests/test_patch_proposals.py`, `tests/test_security_regressions.py`.

Security claim being tested:

Approved patch execution is stored-proposal-only, one-time, drift-checked, stale-base-checked, and
bound to proposal, base file, manifest, policy, schema, requesting principal, request hash, and
expiry evidence.

Implementation evidence found:

- The approval-required path builds `one_time_scope` through `PatchProposalService.approval_scope`.
- The scope includes `tool_name`, `proposal_id`, `proposal_hash`, `base_file_hash`, `workspace_id`,
  `path`, manifest hash/version, tool input schema hash, policy engine/hash/version/document
  version, matched rules, requesting principal, request hash, and expiry.
- Approved execution calls `ApprovalService.begin_execution`, which compares the approval
  `request_hash`, checks expiry, and performs a compare-and-set transition from approved to
  executing.
- `PatchProposalService._verify_approval_scope` revalidates proposal hash, base hash, path,
  workspace, manifest, schema, policy, matched rules, principal, and expiry before apply.
- `_apply_proposal` re-resolves the target path, re-reads the target, checks the current base hash,
  applies the stored unified diff in memory, and writes with a same-directory temporary file plus
  `replace`.
- Replay, stale base, manifest drift, policy drift, schema drift, rule drift, and principal drift are
  covered by existing tests.

Residual risk:

The core binding model is strong for local preview. The main residual risk is crash consistency
across the filesystem side effect and the SQLite state transitions that follow it.

Findings:

- ISR-001.

### Filesystem Read/Path Handling And Race-Sensitive Behavior

Files/functions inspected:

- `apps/api/src/ithildin_api/read_tools.py`: `FilesystemReadTools.resolve_existing_path`,
  `read_file_bytes`, `read_text_file`, `search`, `GitReadTools._run_git`.
- `apps/api/src/ithildin_api/patches.py`: target resolution and text-file validation paths shared
  with patch proposal/apply.
- Relevant tests: `tests/test_read_tools.py`, `tests/test_patch_proposals.py`,
  `tests/test_security_regressions.py`.

Security claim being tested:

Read and patch targets stay inside configured workspaces and deny traversal, absolute escapes,
symlinks, hidden/sensitive paths, `.git` internals, hardlinks, binary files, invalid encodings, and
oversized reads.

Implementation evidence found:

- Path inputs reject absolute paths, `..`, encoded path tokens, and non-NFC Unicode.
- Targets are resolved under the workspace root and checked for hidden/sensitive path components.
- Symlink targets are rejected, and file reads use `os.open` with `O_NOFOLLOW` when available.
- Hardlinked regular files are rejected before read/proposal use.
- Reads are bounded by `max_read_bytes`, reject NUL bytes, and require valid UTF-8 for returned text.
- Git tools run fixed read-only command shapes and do not accept arbitrary caller flags.
- Tests cover traversal, absolute escape, hidden/sensitive paths, symlinks, symlink replacement,
  hardlinks, `.git`, invalid encodings, binary files, large files, and stale patch context.

Residual risk:

The local-preview implementation has good same-host safeguards. Task 080 added a filesystem
executor contract, a temporary-file-only capability check, and additional proposal/apply symlink
swap regressions. Broader OS race proofs remain external-review topics before broader distribution
or stronger platform claims.

Findings:

- ISR-002.

### `http.fetch` SSRF/Redirect/DNS/IP Behavior

Files/functions inspected:

- `apps/api/src/ithildin_api/http_tools.py`: `HttpFetchExecutor.fetch`,
  `_ensure_allowed_destination`, `_validated_resolution`, `parse_http_url`, `_normalize_host`,
  `_is_blocked_ip`, `_read_bounded`.
- `apps/api/src/ithildin_api/resources.py`: network resource derivation.
- Relevant tests: `tests/test_http_tools.py`, `tests/test_governed_tool_calls.py`,
  `tests/test_security_regressions.py`.

Security claim being tested:

`http.fetch` is GET-only, exact-allowlist-only, proxy-disabled, redirect-revalidating, DNS/IP
checked, byte-limited, timeout-bound, and safe-error-oriented.

Implementation evidence found:

- Only `http` and `https` URLs are accepted.
- URL credentials and fragments are rejected.
- Hosts are lowercased, trailing dots removed, IDNA-encoded, and obfuscated IP forms rejected.
- Allowlist matching is exact by normalized host, scheme where specified, and port/default port.
- The default opener installs `ProxyHandler({})` and disables automatic redirect following.
- Each destination is allowlist-checked, resolved twice, and rejected if DNS results change.
- Every redirect hop is parsed, allowlist-checked, and IP-range checked before opening.
- Non-global, loopback, private, link-local, multicast, reserved, and unspecified IPs are blocked.
- Response body and declared content length are bounded.
- Tests cover unsupported schemes, credentials, fragments, exact allowlist, redirect-to-private,
  DNS change, IPv6 blocked ranges, encoded IPs, IDNA/punycode, proxy inheritance suppression,
  timeout/URL errors, redirect limit, response-size limits, and safe errors.

Residual risk:

No finding in this pass. This should still receive external source review because URL and DNS
canonicalization bugs are historically subtle.

Findings:

- None.

### Signed Audit Export Verification And Manifest-Lock Signature Verification

Files/functions inspected:

- `packages/audit-core/src/ithildin_audit_core/signing.py`:
  `signed_audit_export_bundle`, `verify_signed_audit_export_bundle`,
  `verify_exported_events_jsonl`.
- `apps/api/src/ithildin_api/manifest_lock.py`: `verify_manifest_lock`,
  `manifest_lock_signature_bundle`, `verify_manifest_lock_signature`,
  `require_manifest_lock_signature`.
- Relevant tests: `tests/test_audit_writer.py`, `tests/test_tool_registry.py`,
  `tests/test_api_service.py`.

Security claim being tested:

Signed local evidence binds deterministic export or lock digests to local Ed25519 keys, verifies
offline, and remains clearly bounded as local evidence rather than notarization.

Implementation evidence found:

- Audit export signing verifies the configured public key matches the private key, signs canonical
  metadata plus `events_sha256`, and includes public key metadata and key ID.
- Audit export verification checks bundle type/version, event JSONL digest, embedded key ID,
  optional trusted public key, Ed25519 signature, exported audit hash chain, and metadata/chain
  agreement.
- Manifest-lock signatures bind the current lock digest, lock path, key ID, public key, algorithm,
  timestamp, and signature.
- Manifest-lock verification rejects stale/missing entries, duplicate paths/names, path escapes,
  digest mismatch, wrong public key, key ID mismatch, and invalid signatures.
- Runtime signature enforcement remains optional and fail-closed only when configured.

Residual risk:

No finding in this pass. External review should still probe metadata replay, key substitution, and
operator-key lifecycle assumptions.

Findings:

- None.

### Policy Preview/Runtime Parity

Files/functions inspected:

- `apps/api/src/ithildin_api/policy_preview.py`: `PolicyPreviewService.preview`.
- `apps/api/src/ithildin_api/tool_calls.py`: runtime policy-input construction and decision
  evidence.
- `apps/api/src/ithildin_api/resources.py`: shared resource derivation.
- `apps/api/src/ithildin_api/decision_evidence.py`: shared decision evidence.
- Relevant tests: `tests/test_api_service.py`, `tests/test_policy_test_harness.py`,
  `tests/test_policy_impact.py`, `tests/test_governed_tool_calls.py`.

Security claim being tested:

Policy preview is side-effect-free and uses the same registry lookup, trusted principal resolution,
argument validation, resource construction, policy evaluation, and evidence model as runtime where
preview semantics permit.

Implementation evidence found:

- Preview and runtime both resolve registered tools, normalize principals through the principal
  registry, check role/risk visibility, validate JSON Schema input, build resources through
  `resource_from_arguments`, evaluate the same policy engine, and build `policy_decision_evidence`.
- Preview returns safe deny-style responses for unknown tools, unknown/disabled principals, and
  invalid arguments.
- Preview does not call approval creation, patch proposal creation, tool execution, or audit writes.

Residual risk:

No finding in this pass. External review should still compare exact error paths and evidence fields
for drift over future policy changes.

Findings:

- None.

### MCP Ingress Thinness

Files/functions inspected:

- `apps/mcp-server/src/ithildin_mcp_server/server.py`: `IthildinMcpAdapter.list_tools`,
  `call_tool`, `create_adapter`.
- Relevant tests: `tests/test_mcp_adapter.py`, `tests/test_mcp_integration_flow.py`.

Security claim being tested:

The MCP adapter is an ingress adapter only. It lists registered, MCP-exposed, role-visible tools and
routes calls through the same governed pipeline as the API without owning policy or execution logic.

Implementation evidence found:

- Tool listing reads from the trusted registry and filters through the principal registry for the
  local MCP principal.
- Tool calls pass arguments to `GovernedToolCallService.call_tool` with the fixed local MCP
  principal and `mcp-stdio` session.
- The adapter creates the same registry, principal registry, workspace registry, policy engine,
  audit writer, approval service, read executor, patch proposal service, HTTP executor, redaction
  service, and telemetry objects used by the governed pipeline.
- The adapter does not implement separate policy, approval, filesystem, patch, HTTP, or audit logic.

Residual risk:

No finding in this pass. Production or remote MCP transport would require a separate authorization
review and remains out of scope.

Findings:

- None.

### Review-Console Approval Evidence Flow

Files/functions inspected:

- `apps/ui/src/App.tsx`: approval fetching, approve/deny calls, `ApprovalEvidence`,
  `BindingReviewSummary`.
- Relevant validation: UI typecheck/build are part of final verification.

Security claim being tested:

The local review console shows enough approval binding evidence for an admin to understand the exact
stored action before approving, without adding execution controls outside the governed path.

Implementation evidence found:

- The console fetches `/approvals/review?status=pending`.
- `ApprovalEvidence` displays proposal ID/hash, base hash, target path, manifest hash/version,
  policy engine/hash/version/document version, matched rules, requesting principal, request hash,
  expiry, and tool input schema hash from `one_time_scope`.
- `BindingReviewSummary` displays server-derived review checks and disables approval when review is
  invalid.
- Approve/deny actions use the existing mutation endpoints and do not apply patches directly.

Residual risk:

No finding in this pass. External review should inspect UI failure/empty/unauthorized states and
ensure compact hashes are still understandable to local admins.

Findings:

- None.

## Findings

### ISR-001: Patch apply side effect and state completion are not crash-atomic

Severity: medium

Area: `fs.patch.apply` approval binding and atomic apply

Affected files/functions:

- `apps/api/src/ithildin_api/patches.py`: `PatchProposalService.apply_approved`,
  `_apply_proposal`, `_atomic_write_text`.
- `apps/api/src/ithildin_api/approvals.py`: `ApprovalService.begin_execution`,
  `complete_execution`.
- `apps/api/src/ithildin_api/tool_calls.py`: `GovernedToolCallService._execute_approved_patch`.

Claim being tested:

Approval-gated patch apply is one-time, exact-proposal-bound, stale-base-checked, atomically written,
and audit-backed.

Observed behavior:

The implementation performs the important safety checks before writing: approval scope validation,
compare-and-set transition to `executing`, target re-resolution, current base hash check, in-memory
patch generation, and same-directory temporary-file replacement. After the filesystem replacement
succeeds, proposal status and approval completion are updated in SQLite and execution-completed audit
metadata is written by the caller. These database/audit transitions are not atomic with the
filesystem replacement.

Risk:

A process crash, filesystem error after replace, or database/audit failure after the file has been
replaced could leave the workspace modified while the approval remains `executing`, proposal status
is not `applied`, or completed audit evidence is missing. This does not appear to create a direct
approval replay path because `begin_execution` consumes the approval before writing, but it can
produce ambiguous recovery/evidence state.

Recommended fix:

Task 079 added durable patch apply attempt evidence and read-only diagnostics for approvals stuck
after a file replacement. Mutating reconciliation remains deferred until after external review.

Blocking status:

Not blocking external source review. Should fix before broader write powers, broader public
distribution, or stronger evidence claims.

Disposition:

Addressed by Task 079; pending external review.

Verification notes:

Existing tests cover replay, stale base, manifest/policy/schema/principal drift, apply success, and
failed apply audit paths. They do not simulate a process crash or database/audit failure after
successful `Path.replace`.

### ISR-002: Cross-platform filesystem race semantics remain unverified

Severity: medium

Area: filesystem read/path handling and patch proposal/apply

Affected files/functions:

- `apps/api/src/ithildin_api/read_tools.py`: `FilesystemReadTools.resolve_existing_path`,
  `read_file_bytes`, `_ensure_not_hardlinked_file`.
- `apps/api/src/ithildin_api/patches.py`: target resolution, base-file reads, and atomic replace
  paths used by patch proposal/apply.

Claim being tested:

Workspace path controls deny traversal, symlink escape, hardlink ambiguity, hidden/sensitive paths,
binary/encoding issues, and race-prone target replacement.

Observed behavior:

The source uses conservative local controls: resolved workspace roots, path-component checks,
symlink denial, `O_NOFOLLOW` where available, hardlink rejection, size bounds, UTF-8-only text
handling, and same-directory replacement. Existing tests cover representative traversal, symlink,
hardlink, hidden path, `.git`, binary/encoding, and symlink-swap cases on the current test platform.
They do not prove behavior across macOS/Linux/Windows filesystem differences or every race window
around metadata checks, open, and replace.

Risk:

If Ithildin is run on a platform with different symlink, hardlink, normalization, case-sensitivity,
locking, or atomic-replace semantics, a workspace-scope guarantee may be weaker than the current
tests imply. This is especially important before broadening write capability or claiming supported
platform coverage.

Recommended fix:

Task 080 added [filesystem-executor-contract.md](filesystem-executor-contract.md), the
`make filesystem-contract-check` capability report, explicit macOS/Linux support status, explicit
Windows/WSL unsupported status for workspace/race claims, and additional race-like regression
coverage around proposal/apply symlink replacement.

Blocking status:

Not blocking external source review. Should verify before broader distribution, broader write
capability, or explicit multi-platform support claims.

Disposition:

Addressed by Task 080; pending external review.

Verification notes:

The current tests cover the intended local-preview cases on this development environment, and Task
080 makes the supported platform/race contract explicit. This finding remains pending external
review because it is about portability and adversarial race confidence, not an observed bypass in
the current test run.

## Task 080+ Follow-Up Queue

Immediate follow-up candidates:

- None from this internal pass after Task 079 and Task 080. External/source review remains the next
  gate before new governed tool powers.

Hardening backlog candidates:

- External source review of HTTP canonicalization and DNS/redirect behavior.
- External source review of signed evidence metadata replay and key-substitution assumptions.
- External source review of review-console approval evidence clarity.

With the two medium findings recorded, this internal pass recommends moving to external source
review before adding new governed tool powers or changing the runtime boundary.
