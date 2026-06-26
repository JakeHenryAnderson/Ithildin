# Compliance Mapping Disposition Closure Gate

Status: fail-closed closure gate for planning-only `ERG-009`.

This gate validates whether a normalized external/source-review response is strong enough to support
continued architecture planning for compliance mapping support. It does not close `ERG-009` by
itself, does not mutate reviewer findings, does not approve implementation planning, and does not
approve runtime compliance mapping.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Validation command:

```sh
make compliance-mapping-disposition-closure-check
```

The closure gate reads normalized reviewer evidence from:

```text
var/review-runs/compliance-mapping/normalized-response.json
```

If that file is absent, malformed, packet-only, docs-only, unfavorable, or contains critical/high
findings, this gate remains valid but fail-closed:

```text
closure_ready: false
erg_009_status: planning_only
implementation_planning_allowed: false
compliance_mapping_runtime_allowed: false
```

## Required Normalized Response

The normalized response must use the generic external review schema:

```text
ithildin.external_review.normalized_response
```

It must include:

- reviewed area: `compliance-mapping`;
- source access: `source-level` or `packet-and-source`;
- finding namespace: `EXT-COMPLIANCE-MAPPING-###`;
- `can_close_source_rows: true`;
- `mutates_findings: false`;
- `closes_external_review: false`;
- a `sha256:<digest>` reviewed packet hash;
- no critical/high findings;
- `disposition_outcome: continue_architecture_planning`.

If all checks pass, the gate may report:

```text
ready_for_architecture_decision_record
```

That state means only that a later committed triage update may consider moving `ERG-009` toward an
architecture decision record. It still does not approve runtime implementation.

## Boundaries That Remain Blocked

This closure gate must not approve:

- implementation planning;
- runtime implementation;
- compliance mapping runtime behavior;
- compliance automation;
- legal advice;
- automated certification;
- regulated-industry compliance claims;
- custody-grade audit claims;
- external notarization;
- immutable storage;
- production identity;
- runtime Postgres;
- SIEM adapter behavior;
- hosted telemetry;
- remote delivery;
- sandbox orchestration;
- local model invocation;
- trusted-host promotion;
- shell/Docker/Kubernetes/browser governed powers;
- arbitrary HTTP;
- broad filesystem writes;
- plugin SDK behavior;
- new governed tool powers;
- public/security-product positioning.

## Follow-Up Required After Favorable Evidence

Even a favorable normalized response only supports a separate committed triage update. That update
must:

- cite the reviewed packet hash;
- cite this closure-gate output;
- preserve any reviewer findings in the normal finding workflow;
- keep `closes_external_review: false` unless the external-review closure process is explicitly
  completed elsewhere;
- keep runtime work blocked until a later post-RC decision record approves a specific implementation
  plan.

## Validation

Run:

```sh
make compliance-mapping-disposition-closure-check
make compliance-mapping-external-response-intake-check
make compliance-mapping-disposition-packet-check
make compliance-mapping-architecture-check
make release-check
```
