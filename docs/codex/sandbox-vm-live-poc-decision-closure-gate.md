# Sandbox/VM Live POC Decision Closure Gate

Status: fail-closed closure gate for blocked `ERG-004`.

This gate records the minimum evidence required before a later committed triage update may move
`ERG-004` away from `blocked`. It does not close `ERG-004` by itself. It does not approve
implementation planning, runtime implementation, live VM/container inspection, VM/container
lifecycle management, sandbox orchestration, Mission Control runtime behavior, local model
invocation, trusted-host promotion, network expansion, SIEM adapter behavior, production identity,
runtime Postgres, hosted telemetry, remote MCP, compliance automation, new governed tool powers, or
public/security-product positioning.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Validation command:

```sh
make sandbox-vm-live-poc-decision-closure-check
```

## Required Normalized Response

The gate looks for this ignored/local evidence file:

```text
var/review-runs/sandbox-vm-live-poc/normalized-response.json
```

The response must be produced from
[sandbox-vm-live-poc-external-response-intake.md](sandbox-vm-live-poc-external-response-intake.md)
using the external response normalizer. The expected response shape is:

- response type: `ithildin.external_review.normalized_response`;
- reviewed area: `sandbox-vm-live-poc`;
- source access: `source-level` or `packet-and-source`;
- finding namespace: `EXT-LIVE-POC-###`;
- reviewed packet hash: `sha256:<64 lowercase hex chars>`;
- `can_close_source_rows: true`;
- `mutates_findings: false`;
- `closes_external_review: false`;
- no critical/high findings;
- `erg_003_favorable_disposition: true`;
- `decision_outcome: approve_limited_operator_managed_poc_planning`.

If that file is absent, malformed, packet-only/docs-only, missing favorable `ERG-003` disposition,
or contains critical/high findings, the gate must report:

```text
closure_ready: false
erg_004_status: blocked
implementation_planning_allowed: false
```

## Allowed Closure Readiness Result

The only readiness result this gate can support is:

```text
ready_for_decision_record
```

That result does not approve runtime implementation. It means a later committed post-RC decision
record may consider whether to move from blocked status to implementation-planning-only status for a
limited operator-managed POC.

## Required Later Triage Update

If the closure gate eventually reports `closure_ready: true`, a separate committed triage update
must still:

- record the raw reviewer response and normalized response path;
- record reviewer label, source access, reviewed commit, and reviewed packet hash;
- add or update any `EXT-LIVE-POC-###` finding files;
- update [enterprise-readiness-gap-matrix.md](enterprise-readiness-gap-matrix.md);
- update [post-rc-decision-register.md](post-rc-decision-register.md);
- update [enterprise-sandbox-control-plane-readiness.md](enterprise-sandbox-control-plane-readiness.md);
- preserve implementation status as planning-only unless a later implementation sprint is explicitly
  approved;
- rerun `make release-check`;
- rerun `make review-candidate`.

## Boundaries That Remain Blocked

This closure gate must not approve:

- runtime implementation;
- live VM/container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- Mission Control runtime behavior;
- local model invocation;
- trusted-host promotion;
- network expansion;
- API/MCP profile loading;
- SIEM adapter behavior;
- production identity;
- runtime Postgres;
- hosted telemetry;
- remote MCP;
- compliance automation;
- new governed tool powers;
- public/security-product positioning.
