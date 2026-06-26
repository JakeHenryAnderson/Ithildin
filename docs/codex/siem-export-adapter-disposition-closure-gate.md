# SIEM Export Adapter Disposition Closure Gate

Status: fail-closed closure gate for planning-only `ERG-008`.

This gate records the minimum evidence required before a later committed triage update may move
`ERG-008` toward an architecture-planning decision record. It does not close `ERG-008` by itself.
It does not approve implementation planning, runtime implementation, SIEM adapter behavior, hosted
telemetry, remote delivery, custody-grade audit claims, external notarization, immutable storage,
production identity, runtime Postgres, compliance automation, security-operations control-plane
claims, hosted control plane behavior, sandbox orchestration, local model invocation,
trusted-host promotion, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad
filesystem writes, plugin SDK behavior, new governed tool powers, or public/security-product
positioning.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Validation command:

```sh
make siem-export-adapter-disposition-closure-check
```

## Required Normalized Response

The gate looks for this ignored/local evidence file:

```text
var/review-runs/siem-export-adapter/normalized-response.json
```

The response must be produced from
[siem-export-adapter-external-response-intake.md](siem-export-adapter-external-response-intake.md)
using the external response normalizer. The expected response shape is:

- response type: `ithildin.external_review.normalized_response`;
- reviewed area: `siem-export-adapter`;
- source access: `source-level` or `packet-and-source`;
- finding namespace: `EXT-SIEM-ADAPTER-###`;
- reviewed packet hash: `sha256:<64 lowercase hex chars>`;
- `can_close_source_rows: true`;
- `mutates_findings: false`;
- `closes_external_review: false`;
- no critical/high findings;
- `disposition_outcome: continue_architecture_planning`.

If that file is absent, malformed, packet-only/docs-only, missing the allowed disposition outcome,
or contains critical/high findings, the gate must report:

```text
closure_ready: false
erg_008_status: planning_only
implementation_planning_allowed: false
siem_adapter_allowed: false
hosted_telemetry_allowed: false
remote_delivery_allowed: false
```

## Allowed Closure Readiness Result

The only readiness result this gate can support is:

```text
ready_for_architecture_decision_record
```

That result does not approve implementation planning or runtime implementation. It means a later
committed post-RC decision record may consider whether the SIEM export adapter lane can continue
architecture planning from the reviewed evidence.

## Required Later Triage Update

If the closure gate eventually reports `closure_ready: true`, a separate committed triage update
must still:

- record the raw reviewer response and normalized response path;
- record reviewer label, source access, reviewed commit, and reviewed packet hash;
- add or update any `EXT-SIEM-ADAPTER-###` finding files;
- update [enterprise-readiness-gap-matrix.md](enterprise-readiness-gap-matrix.md);
- update [post-rc-decision-register.md](post-rc-decision-register.md);
- preserve runtime SIEM adapter behavior as blocked unless a later implementation sprint is
  explicitly approved;
- preserve local/offline evidence export as the current runtime posture;
- preserve optional locally signed evidence as local operator evidence, not external notarization or
  custody-grade proof;
- rerun `make release-check`;
- rerun `make review-candidate`.

## Boundaries That Remain Blocked

This closure gate must not approve:

- implementation planning;
- runtime implementation;
- SIEM adapter behavior;
- hosted telemetry;
- remote delivery;
- custody-grade audit claims;
- external notarization;
- immutable storage;
- production identity;
- runtime Postgres;
- compliance automation;
- security-operations control-plane claims;
- hosted control plane behavior;
- sandbox orchestration;
- local model invocation;
- trusted-host promotion;
- shell/Docker/Kubernetes/browser governed powers;
- arbitrary HTTP;
- broad filesystem writes;
- plugin SDK behavior;
- new governed tool powers;
- public/security-product positioning.
