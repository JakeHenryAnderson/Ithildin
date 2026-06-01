# Review Console Assurance

Tasks 099-100 tighten the local review console for v0.3-prep handoff. Task 139 adds the v0.4
approval-evidence UX pass, and Task 140 tightens unauthorized and request-failure states, without
changing approval APIs, auth semantics, or executor behavior.

## Approval Evidence Clarity

Pending approval cards show derived patch-apply binding evidence grouped by:

- patch artifact;
- tool manifest;
- policy decision;
- principal and scope.

The grouped evidence includes:

- tool name;
- proposal ID and proposal hash;
- base file hash;
- target path and workspace;
- manifest hash/version;
- policy engine/hash/version/document version;
- matched rules;
- requesting principal;
- request hash and expiry;
- tool input schema hash;
- approval scope hash;
- policy reason.

The console also exposes a copy action for the safe approval evidence payload, including the
derived `review_summary` validity, checks, reasons, and proposal review shown by the UI. This lets a
reviewer compare UI-visible approval state with API/audit evidence without copying raw diffs or file
contents.

## Failure-State and Trust UX

Unauthorized and request-failure states are intentionally plain:

- missing token shows a locked local-console state;
- rejected admin token shows a locked dashboard state;
- no loaded system status shows an unavailable console-data state;
- failed JSON API responses use the safe `detail` field or HTTP status text;
- failed export responses are parsed the same way rather than showing raw response bodies.

The console fetches `/patch-apply-diagnostics` with the rest of the dashboard data and surfaces:

- `clean`, `recovery_required`, or `ambiguous` patch-apply diagnostic status;
- incomplete apply-attempt count;
- approvals stuck in `executing`;
- safe recommended operator action;
- warning banners when audit verification, manifest lock/signature, token posture, CORS, remote MCP,
  or patch-apply diagnostics indicate attention is needed.

This is read-only UX. It does not add repair, rollback, approval mutation, new tools, or remote
review surfaces.
