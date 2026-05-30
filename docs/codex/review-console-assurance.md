# Review Console Assurance

Tasks 099-100 tighten the local review console for v0.3-prep handoff.

## Approval Evidence Clarity

Pending approval cards show derived patch-apply binding evidence:

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

The console also exposes a copy action for the safe approval evidence payload so a reviewer can
compare UI-visible evidence with API/audit evidence without copying raw diffs or file contents.

## Failure-State and Trust UX

The console fetches `/patch-apply-diagnostics` with the rest of the dashboard data and surfaces:

- `clean`, `recovery_required`, or `ambiguous` patch-apply diagnostic status;
- incomplete apply-attempt count;
- approvals stuck in `executing`;
- safe recommended operator action;
- warning banners when audit verification, manifest lock/signature, token posture, CORS, remote MCP,
  or patch-apply diagnostics indicate attention is needed.

This is read-only UX. It does not add repair, rollback, approval mutation, new tools, or remote
review surfaces.
