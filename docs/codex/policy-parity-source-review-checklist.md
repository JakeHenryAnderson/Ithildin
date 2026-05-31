# Policy Parity Source Review Checklist

Task 163 creates the source-review checklist for policy preview/runtime parity. Use it with
[source-review-runbook-v2.md](source-review-runbook-v2.md),
[source-file-inspection-packet.md](source-file-inspection-packet.md), and
[policy-parity-harness.md](policy-parity-harness.md).

## Files And Functions

Inspect:

- `apps/api/src/ithildin_api/policy_preview.py`
  - `PolicyPreviewService.preview`
  - `PolicyPreviewService._policy_evidence`
  - `PolicyPreviewService._deny_preview`
- `apps/api/src/ithildin_api/tool_calls.py`
  - `GovernedToolCallService.call_tool`
  - `GovernedToolCallService._audit_decision`
  - `_tool_call_hash`
- `apps/api/src/ithildin_api/resources.py`
  - resource construction for paths, patch proposals, and network URLs
- `apps/api/src/ithildin_api/policy.py`
  - default YAML policy evaluation and evidence
- `apps/api/src/ithildin_api/decision_evidence.py`
- `scripts/policy_parity.py`
- `scripts/policy_test.py`
- `policies/default.yaml`
- `policies/tests/default.yaml`

## Claims To Test

- Policy preview is side-effect-free: no approval creation, patch proposal creation, tool execution,
  audit writes, or database mutation.
- Preview and runtime share the same trusted principal normalization, role filtering, resource
  derivation, manifest hash/version evidence, and argument validation semantics.
- Unknown tools, invalid arguments, unknown/disabled principals, out-of-scope resources, and
  dangerous risks produce safe deny-style preview/runtime decisions.
- Runtime `policy.evaluated` audit metadata is comparable to preview decision evidence.
- Default YAML policy remains deny-by-default and keeps write actions approval-gated.
- Policy test fixtures cover read allow, write approval, write-proposal allow, network allow when
  in scope, dangerous denial, destructive denial, out-of-scope denial, and role-based denials.
- OPA remains optional sidecar evidence/prototype support unless an OPA fixture runner is explicitly
  added; YAML remains canonical for current release gates.

## Evidence Commands

```sh
make policy-test
make policy-parity
uv run pytest tests/test_policy_parity.py tests/test_policy_test_harness.py tests/test_policy_impact.py
uv run pytest tests/test_api_service.py tests/test_governed_tool_calls.py
make release-check
```

## Finding Prompts

For every issue, record:

- whether preview allowed something runtime denies or runtime allows something preview denies;
- whether the mismatch involves principal roles, resource scope, manifest/policy evidence, argument
  validation, OPA/YAML differences, or audit metadata;
- whether preview accidentally mutates state or executes tools;
- whether the fix changes default policy semantics or merely evidence parity.

## Non-Goals

This checklist does not add policy editing, production RBAC, OIDC/SAML/SCIM, OPA-as-canonical
runtime, new approval semantics, or new governed tool powers.
