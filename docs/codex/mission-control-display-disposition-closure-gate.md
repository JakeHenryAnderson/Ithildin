# Mission Control Display Disposition Closure Gate

Status: fail-closed closure gate for planning-only `ERG-002`.

This gate records the minimum evidence required before a later committed triage update may move
`ERG-002` toward a design-only Mission Control-side decision record. It does not close `ERG-002` by
itself. It does not approve runtime implementation, Mission Control runtime importer behavior,
Mission Control execution authority, Mission Control policy authority, Mission Control approval
authority, Mission Control audit authority, API callbacks, polling or mutating Ithildin APIs, local
model invocation, VM/container lifecycle management, sandbox orchestration, trusted-host promotion,
SIEM adapter behavior, production identity, runtime Postgres, hosted telemetry, remote delivery,
shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem writes,
compliance automation, new governed tool powers, or public/security-product positioning.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Validation command:

```sh
make mission-control-display-disposition-closure-check
```

Run `make mission-control-display-response-application-preflight-check` before using a real
reviewer response. The companion `mission-control-display-response-application-preflight.md` checks
the all-lane raw response path, ERG-002 normalized response path, command matrix row, closure gate,
dry-run, response kit, decision-record skeleton, and blocked runtime boundaries without normalizing
responses or closing `ERG-002`.

## Required Normalized Response

The gate looks for this ignored/local evidence file:

```text
var/review-runs/mission-control-display/normalized-response.json
```

The response must be produced from
[mission-control-display-external-response-intake.md](mission-control-display-external-response-intake.md)
using the external response normalizer. The expected response shape is:

- response type: `ithildin.external_review.normalized_response`;
- reviewed area: `mission-control-display`;
- source access: `source-level` or `packet-and-source`;
- finding namespace: `EXT-MC-DISPLAY-###`;
- reviewed packet hash: `sha256:<64 lowercase hex chars>`;
- `can_close_source_rows: true`;
- `mutates_findings: false`;
- `closes_external_review: false`;
- no critical/high findings;
- `disposition_outcome: continue_design_only`.

If that file is absent, malformed, packet-only/docs-only, missing the allowed disposition outcome,
or contains critical/high findings, the gate must report:

```text
closure_ready: false
erg_002_status: planning_only
mission_control_runtime_allowed: false
runtime_importer_allowed: false
```

## Allowed Closure Readiness Result

The only readiness result this gate can support is:

```text
ready_for_design_only_decision_record
```

That result does not approve runtime implementation. It means a later committed post-RC decision
record may consider whether Mission Control-side design planning can continue from the reviewed
display/importer evidence.

## Required Later Triage Update

If the closure gate eventually reports `closure_ready: true`, a separate committed triage update
must still:

- record the raw reviewer response and normalized response path;
- use [mission-control-display-decision-record-skeleton.md](mission-control-display-decision-record-skeleton.md)
  for any design-only decision record;
- record reviewer label, source access, reviewed commit, and reviewed packet hash;
- add or update any `EXT-MC-DISPLAY-###` finding files;
- update [enterprise-readiness-gap-matrix.md](enterprise-readiness-gap-matrix.md);
- update [post-rc-decision-register.md](post-rc-decision-register.md);
- preserve Ithildin runtime behavior as unchanged unless a later implementation sprint is explicitly
  approved;
- preserve Mission Control as non-authoritative for execution, policy, approval, and audit unless a
  later external review and implementation decision explicitly changes that boundary;
- rerun `make release-check`;
- rerun `make review-candidate`.

## Boundaries That Remain Blocked

This closure gate must not approve:

- runtime implementation;
- Mission Control runtime importer behavior;
- Mission Control execution authority;
- Mission Control policy authority;
- Mission Control approval authority;
- Mission Control audit authority;
- API callbacks;
- polling or mutating Ithildin APIs;
- local model invocation;
- VM/container lifecycle management;
- sandbox orchestration;
- trusted-host promotion;
- SIEM adapter behavior;
- production identity;
- runtime Postgres;
- hosted telemetry;
- remote delivery;
- shell/Docker/Kubernetes/browser governed powers;
- arbitrary HTTP;
- broad filesystem writes;
- compliance automation;
- new governed tool powers;
- public/security-product positioning.
