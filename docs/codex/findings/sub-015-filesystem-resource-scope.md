# SUB-015 Filesystem Resource Scope

- Finding ID: SUB-015
- Severity: high
- Area: policy/resource truthfulness
- Affected files/functions: apps/api/src/ithildin_api/resources.py; resource_from_arguments; apps/api/src/ithildin_api/read_tools.py; ReadToolExecutor.resource_from_arguments; apps/api/src/ithildin_api/policy_preview.py; PolicyPreviewService.preview; apps/api/src/ithildin_api/tool_calls.py; GovernedToolCallService.call_tool
- Claim being tested: policy preview and runtime policy evidence must not mark filesystem resources in scope when the executor would deny the path.
- Observed behavior: Filesystem resources were marked `in_scope: true` whenever a `path` argument existed, so traversal paths could be policy-allowed before executor denial.
- Risk: Preview/runtime policy evidence could overstate resource scope and hide a policy false positive behind later executor failure.
- Recommended fix: Derive filesystem resource scope with executor-equivalent workspace path safety before policy evaluation and deny out-of-scope resources before execution.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: Read and write-proposal resources now use `ReadToolExecutor.resource_from_arguments` when available, preserving workspace ID, normalized path, and safe scope errors. Preview and governed calls deny `in_scope: false` resources before execution. Tests cover traversal preview denial, governed-call pre-execution denial, and parity fixtures for out-of-scope filesystem paths. External/source review remains pending.
