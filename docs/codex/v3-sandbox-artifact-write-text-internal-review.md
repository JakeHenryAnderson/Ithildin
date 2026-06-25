# sandbox.artifact.write_text Internal Source Review

Status: internal source-review pass complete for continued local-preview development.

This review inspected `sandbox.artifact.write_text` as the first bounded local-preview sandbox
artifact write capability. It does not approve host promotion, VM/container lifecycle management,
sandbox orchestration, shell execution, broad filesystem writes, production identity, compliance
claims, public/security-product positioning, or any broader write capability class.

## Scope

- Manifest/schema: `tool-manifests/sandbox-artifact-write-text.yaml`.
- Executor/resource construction: `apps/api/src/ithildin_api/sandbox_artifacts.py` and
  `apps/api/src/ithildin_api/resources.py`.
- Governed-call, approval, and audit path: `apps/api/src/ithildin_api/tool_calls.py`.
- MCP path: `apps/mcp-server/src/ithildin_mcp_server/server.py`.
- Policy parity fixture: `policies/tests/parity.yaml`.
- Focused tests and evidence:
  `tests/test_governed_tool_calls.py`, `tests/test_mcp_adapter.py`,
  `tests/test_policy_parity.py`, `tests/test_tool_registry.py`,
  `tests/test_manifest_change_review.py`, and `tests/test_release_readiness.py`.
- Handoff and negative transcript generators:
  `scripts/sandbox_artifact_write_text_source_review_bundle.py` and
  `scripts/sandbox_artifact_write_text_negative_transcripts.py`.

## Claims Tested

- The tool is schema-closed and approval-gated.
- Policy preview/runtime evidence uses the normalized `sandbox_artifact` resource.
- Approval scope binds tool name, workspace, sandbox ID, artifact label, content hash/size,
  manifest hash/version, schema hash, policy engine/hash/version/document version, matched rules,
  requesting principal, request hash, and expiry.
- The response and audit path include hashes/counts/status metadata, not file contents or raw host
  paths.
- Unsafe paths, hidden/sensitive names, `.git` internals, symlinks, hardlinks, non-UTF-8 existing
  targets, replayed approvals, and approval-content mismatches deny safely.
- MCP exposure flows through the governed tool-call path and returns approval-required evidence
  rather than bypassing policy or approval.
- The source-review packet and observed negative transcripts give a reviewer enough source, tests,
  contracts, command evidence, and denial evidence to assess the lane.

## Implementation Evidence

- The manifest is `risk: write`, `category: sandbox`, MCP exposed, and has
  `additionalProperties: false`.
- `SandboxArtifactWriteService.approval_scope` stores content as `content_sha256` and
  `content_bytes`; content itself is not placed in approval scope metadata.
- `SandboxArtifactWriteService.apply_approved` validates the stored approval scope against the
  current action, manifest, schema, policy, matched rules, and principal before writing.
- The executor validates workspace confinement and path components, rejects ambiguous encoded path
  tokens and control/unnormalized input, blocks hidden/sensitive path names, denies symlink and
  hardlink targets, and writes UTF-8 text through a same-directory temporary file.
- Governed-call tests cover approval-required flow, single-use replay denial, scope mismatch denial,
  unsafe path denial, secret-free audit metadata, and non-UTF-8 target denial.
- MCP tests verify the tool is listed for the configured read/write principal and requests approval
  through the adapter path.
- Policy parity includes `sandbox_artifact_write_preview_matches_runtime`.
- `make sandbox-artifact-write-text-negative-transcripts` records observed local fixture denials for
  traversal, hidden/sensitive path, symlink target, approval-content mismatch, replayed approval,
  overwrite denied by default, and existing non-UTF-8 target.
- `make sandbox-artifact-write-text-source-review-bundle` produces a focused source-review packet
  with source, tests, contract docs, gate evidence, command transcript, intake commands, and artifact
  hashes.

## Finding

| Finding ID | Severity | Area | Affected files/functions | Blocking status | Disposition | Recommended fix |
| --- | --- | --- | --- | --- | --- | --- |
| XH-SANDBOX-WRITE-001 | medium | sandbox artifact write | `apps/api/src/ithildin_api/sandbox_artifacts.py` `_atomic_write_text`, `_validate_artifact_target`, `_mkdirs_under_workspace` | later | deferred | Keep the current local-preview posture explicit and require external/source review before stronger filesystem race or sandbox-isolation claims. |

## Residual Risk

`sandbox.artifact.write_text` is intentionally narrow, but it is still an application-level mediated
write on the local host filesystem. The current implementation revalidates target state immediately
before writing and avoids broad write powers, but it does not prove kernel-grade resistance to every
possible parent-directory replacement race or host compromise scenario. This is acceptable for the
current local-preview boundary because the tool remains approval-gated, sandbox-labeled,
workspace-confined, UTF-8/text-only, size-limited, audited, and explicitly not a sandbox or host
promotion mechanism. Stronger claims require separate external/source review and likely OS-level
sandboxing or descriptor-based write semantics.

## Follow-Up Queue

- No critical or high findings were found.
- `XH-SANDBOX-WRITE-001` is deferred as a documented local-preview filesystem race residual, not a
  blocker for continued local-preview development.
- The lane is locally reviewed for continued local-preview development only.
- The lane is not externally closed and does not unblock broad filesystem writes, host promotion,
  sandbox orchestration, production/security-product positioning, or new powerful tool classes.

## Verification

Run:

```bash
make sandbox-artifact-write-text-implementation-gate
make sandbox-artifact-write-text-negative-transcripts
make sandbox-artifact-write-text-source-review-bundle
make policy-parity
make reviewer-findings-check
make review-findings-summary
make release-check
```
