# CC-PILOT-103 Implementation Handoff

Status: implementation candidate complete; authorized to proceed to `CC-PILOT-104` after gates.

Base commit: `6a357bd4bb7e7a7dc10abeb4bfa834addf64175c`
Governed tool count: `24`
Runtime authority change: none
Schema/API/manifest/policy/approval/audit change: none

## Implemented Slice

The Artifacts surface now supports a bounded proposal lifecycle review:

- client-side search over artifact path, workspace, request, and proposal ID;
- proposal-state filtering and deterministic updated/path sorting;
- workspace grouping with labeled Artifact, Requester, Lifecycle, Updated, and Next columns;
- stable proposal-ID selection with the default detail aligned to the first visible sorted row;
- exact requesting identity when correlated approval history supplies it, otherwise `Unavailable`;
- separate proposal, approval, application, and operator-review steps;
- generated addition/removal summary before raw diff;
- proposal, base artifact, and current artifact digests under technical disclosure;
- current pending-approval navigation only when the separately reviewed binding is present;
- explicit applied-versus-reviewed/promoted/published/release-ready boundary language.

Applied proposals no longer inherit a misleading stale-warning presentation merely because the
proposal-review helper correctly considers non-proposed records non-actionable. Proposed records
still surface genuine base-file drift or stale binding attention.

## Approval History Compatibility

Implementation QA found that unfiltered `GET /approvals/review` is not a safe historical-list
source when a local database contains legacy approvals whose one-time scopes predate current binding
fields. The client therefore uses:

- `GET /approvals` for read-only historical lifecycle correlation; and
- `GET /approvals/review?status=pending` only for current actionable binding validation.

This preserves historical state visibility while keeping approve/deny enablement fail-closed. No
legacy record is rewritten and no API behavior is changed.

## Authority Boundary

Proposal, approval, and application values remain recorded Gateway states. `Ready for operator
review` is explanatory UI guidance for an applied artifact, not stored review state. Ithildin has no
review-complete or artifact-promotion mutation in this slice, so Command Center does not create or
imply one.

No new endpoint, state, role, permission, policy semantic, tool, or governed power was introduced.

## Focused Test Evidence

The UI harness verifies:

- proposed artifact plus exact valid pending approval presentation;
- four distinct lifecycle steps and the non-promotion boundary;
- applied proposal plus executed approval history;
- no pending-approval action for the applied artifact;
- search-empty behavior with selected detail retained;
- existing decision explanation, approval actions, run evidence, export, filter, trust, empty, and
  locked behaviors.

Focused result:

```text
Test Files  1 passed (1)
Tests       9 passed (9)
```

## Live Browser Verification

The documented demo seed/flow created bounded ignored local-preview evidence for QA. The live
Command Center loaded nine proposal records across applied and expired lifecycle states, correlated
requesters from raw approval history, and selected the most recently updated proposal by default.
The selected applied record showed:

- proposal state `applied`;
- approval state `executed`;
- application state `recorded applied` without inventing an application timestamp;
- operator review `not recorded`;
- one addition and one removal before technical diff evidence;
- no review-complete or promotion control.

Browser logs contained only Vite connection/hot-update messages and the React development-tools
notice; no warnings or errors were present after the compatibility fix. Demo records and generated
result artifacts are local ignored QA evidence, not release or product-acceptance evidence.

## Validation

Passed:

```text
make ui-test
make typecheck
make tool-surface-invariant-gate
make no-new-powers-guardrail
make agent-workflow-check
uv run pytest tests/test_release_readiness.py tests/test_docs_site.py -q
make lint
make docs-site
git diff --check
```

## Next Gate

Proceed to `CC-PILOT-104` only after the proportional repository gates pass. The next ticket may
improve evidence closeout presentation but must not alter signing, verification, export, audit,
approval, or release semantics. Fresh-operator UAT remains deferred to `CC-PILOT-107`.
