# CC-PILOT-101 Implementation Handoff

Status: implementation candidate complete; human product review required before `CC-PILOT-102`.

Base commit: `6a357bd4bb7e7a7dc10abeb4bfa834addf64175c`
Governed tool count: `24`
Runtime authority change: none
Schema/API/manifest/policy/approval/audit change: none

## Implemented Slice

The existing review console now presents the first bounded Ithildin Command Center entry slice:

- purpose-led `Ithildin Command Center` heading and concise Gateway authority boundary;
- persistent navigation for Attention, Missions / Agent Runs, Artifacts, Approvals, Evidence, and
  Administration;
- a visible Help disclosure explaining what Ithildin does and does not govern;
- explicit `Sign-in required` versus `Authenticated local preview` posture;
- an exception-first Attention section before implementation-shaped status tables;
- one deterministic primary Attention item selected from existing approval, failure, recovery, or
  proposal records;
- plain-language required action and consequence before technical fields;
- labeled workspace, requesting identity, tool, request, and policy reason values;
- honest `Unavailable` states instead of invented mission, identity, tool, or policy context;
- selection-only navigation to the existing Agent Run Workbench, approval, artifact, or evidence
  source record.

The deterministic priority and source mapping are recorded in
[CC-PILOT-101 Authoritative Data Feasibility Map](command-center-cc-pilot-101-data-feasibility.md).

## Authority Boundary

The UI derives one presentation priority from already loaded records. It does not store Attention,
mission, severity, or workflow state. Opening an item only selects existing `run_id` and
`proposal_id` values and scrolls to the relevant source surface.

The slice does not approve, deny, execute, apply, promote, start, pause, abort, schedule, notify,
repair, export, or mutate evidence. Existing approval and export controls remain unchanged and
continue to call their existing APIs.

## Focused Test Evidence

The UI interaction harness now verifies:

- first-time purpose and Gateway boundary copy;
- all six information-architecture links plus Help;
- sign-in-required Attention state;
- authenticated local-preview state;
- an approval-backed Attention item with mission presentation context, workspace, requesting
  identity, policy reason, and required action;
- navigation from Attention into the existing Workbench selection;
- existing trust, approval, proposal, Agent Run, evidence-export, filtering, and policy-preview
  behavior remains covered.

Focused result:

```text
Test Files  1 passed (1)
Tests       7 passed (7)
```

## Live Browser Verification

The documented local Vite UI and existing host API entrypoint were started temporarily and stopped
after verification. The visible first viewport showed:

- the Command Center purpose and enforcement boundary;
- persistent navigation and authenticated local-preview state;
- the real local token-length warning;
- one proposed-change Attention item before the legacy dashboard panels;
- explicit proposal consequence and labeled fields;
- `Unavailable` requesting identity/tool and absent policy-reason language because the current
  proposal did not have an exact correlated run or pending approval record;
- source-record navigation landing on the existing artifact/proposal panel.

No browser console warnings or errors were present. This is implementation QA, not fresh-operator
UAT, product acceptance, release evidence, or proof of enterprise readiness.

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

The full `make release-check` passed manifest-lock validation, release guardrails, release-evidence
schema validation, and reviewer-finding validation with zero open critical/high findings. It then
stopped at an ignored baseline review-run artifact:

```text
v0.9-git-commit-metadata-internal-xhigh commit does not match current HEAD
```

The ignored manifest records historical commit `4357a4e95475d2a08d7b0529202230c704652e63` while
current `HEAD` is `6a357bd4bb7e7a7dc10abeb4bfa834addf64175c`. It was not modified or refreshed because rebinding
historical review evidence to the current commit would be misleading.

## Review Questions

Human product review should answer:

1. Does the first viewport now make Ithildin's operator purpose legible?
2. Is the Gateway/Command Center authority split concise and understandable?
3. Does the Attention item lead with a useful action and consequence?
4. Are unavailable correlations labeled honestly rather than feeling broken?
5. Is the navigation sufficient as the first shell slice without implying later areas are complete?
6. Is this baseline acceptable for `CC-PILOT-102` to add the selected request decision explanation?

## Next Gate

Do not begin `CC-PILOT-102` until a human accepts this slice or records required changes. Acceptance
authorizes only the next bounded ticket; it does not approve the whole epic, fresh-operator UAT,
release, or enterprise/security-product claims.
