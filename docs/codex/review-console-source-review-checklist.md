# Review Console Source Review Checklist

Task 165 creates the source-review checklist for the local admin review console. Use it with
[source-review-runbook-v2.md](source-review-runbook-v2.md),
[source-file-inspection-packet.md](source-file-inspection-packet.md), and
[review-console-assurance.md](review-console-assurance.md).

## Files And Functions

Inspect:

- `apps/ui/src/App.tsx`
  - admin token/session storage handling
  - API request helper and error handling
  - system trust panel
  - approval list/detail rendering
  - approval binding evidence display
  - approve/deny action handlers
  - patch proposal detail rendering
  - audit verification/export actions
  - policy preview panel
  - patch apply diagnostics display
- `apps/api/src/ithildin_api/app.py`
  - approval routes
  - audit routes
  - system status route
  - patch proposal and diagnostics routes
- `apps/api/src/ithildin_api/patches.py`
  - approval review and diagnostics payloads

## Claims To Test

- The UI stores the admin token in session storage only and sends it as bearer auth to admin APIs.
- Unauthorized, loading, empty, and request-error states are clear without exposing raw secrets.
- Approval review shows proposal ID/hash, base file hash, target path, manifest hash/version, policy
  engine/hash/version, matched rules, requesting principal, request hash, expiry, and scope hash
  where present.
- The copied approval evidence includes the derived review verdict/checks/reasons that control
  approval enablement, without copying diffs, file contents, tokens, or secrets.
- Approve/deny controls call only the existing approval mutation endpoints and include
  `decided_by: "admin:local-ui"`.
- The UI does not add direct tool execution, patch apply, shell, Docker, Kubernetes, browser, or
  broad-write controls.
- Patch proposal details expose diffs only through admin-authenticated views.
- Audit export and signed export actions are separated and labeled as local evidence, not custody or notarization.
- System warnings make dev-token mode, unsupported filesystem profile, audit problems, manifest lock
  status, principal registry status, and telemetry/storage posture visible.

## Evidence Commands

```sh
npm run typecheck --prefix apps/ui
npm run build --prefix apps/ui
uv run pytest tests/test_api_service.py tests/test_release_readiness.py
make release-check
```

## Finding Prompts

For every issue, record:

- whether it affects approval clarity, admin authentication, evidence labeling, or unsafe mutation;
- whether hidden or confusing UI controls could trigger execution outside the governed pipeline;
- whether sensitive diffs, file contents, response bodies, tokens, keys, or secrets are exposed in
  error states;
- whether the issue is UI-only, API payload-related, or an evidence-contract mismatch.

## Non-Goals

This checklist does not add multi-user auth, production RBAC, UI policy editing, direct execution
controls, mutating recovery, shell/Docker/Kubernetes/browser tools, or hosted review workflows.
