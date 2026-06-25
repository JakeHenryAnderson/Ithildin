# XH-SANDBOX-WRITE-001 Filesystem Race Residual

- Finding ID: XH-SANDBOX-WRITE-001
- Severity: medium
- Area: sandbox artifact write
- Affected files/functions: apps/api/src/ithildin_api/sandbox_artifacts.py `_atomic_write_text`, `_validate_artifact_target`, `_mkdirs_under_workspace`
- Claim being tested: The bounded sandbox artifact write path should be honest about what it can and cannot guarantee as an application-level local-preview filesystem write.
- Observed behavior: Internal review found the tool validates path scope, denies symlinks/hardlinks, revalidates before writing, writes through a same-directory temporary file, and replaces or links atomically for the target path. However, the implementation still relies on path-based filesystem operations, so it does not prove resistance to every possible parent-directory replacement race or host compromise scenario.
- Risk: If documentation or downstream users overread the feature as OS sandboxing, host promotion control, or a fully race-proof filesystem boundary, they could trust it for stronger enterprise/security claims than the current implementation supports.
- Recommended fix: Keep the feature scoped to local-preview, approval-gated, sandbox-labeled artifact writes; preserve warning language; require external/source review and likely OS-level sandboxing or descriptor-based write semantics before claiming stronger filesystem race or sandbox-isolation guarantees.
- Blocking status: later
- Disposition: deferred
- Verification notes: `docs/codex/v3-sandbox-artifact-write-text-internal-review.md` records the residual risk and `make sandbox-artifact-write-text-implementation-gate`, `make sandbox-artifact-write-text-negative-transcripts`, `make sandbox-artifact-write-text-source-review-bundle`, `make policy-parity`, and `make release-check` verify the current local-preview evidence path.
