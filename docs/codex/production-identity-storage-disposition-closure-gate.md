# Production Identity And Storage Disposition Closure Gate

Status: fail-closed closure gate for planning-only `ERG-006` and `ERG-007`.

This gate records the minimum evidence required before a later committed triage update may move
`ERG-006` or `ERG-007` toward an architecture-planning decision record. It does not close
`ERG-006` or `ERG-007` by itself. It does not approve implementation planning, runtime
implementation, production IAM, enterprise RBAC, tenant/team authorization runtime behavior,
remote admin use, runtime Postgres, database migrations, backup/restore runtime behavior,
retention enforcement, hosted control plane, custody-grade audit claims, compliance automation,
hosted telemetry, remote MCP, SIEM adapter behavior, sandbox orchestration, local model invocation,
trusted-host promotion, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad
filesystem writes, plugin SDK behavior, new governed tool powers, or public/security-product
positioning.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Validation command:

```sh
make production-identity-storage-disposition-closure-check
```

## Required Normalized Response

The gate looks for this ignored/local evidence file:

```text
var/review-runs/production-identity-storage/normalized-response.json
```

The response must be produced from
[production-identity-storage-external-response-intake.md](production-identity-storage-external-response-intake.md)
using the external response normalizer. The expected response shape is:

- response type: `ithildin.external_review.normalized_response`;
- reviewed area: `production-identity-storage`;
- source access: `source-level` or `packet-and-source`;
- finding namespace: `EXT-PROD-IAM-STORAGE-###`;
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
erg_006_status: planning_only
erg_007_status: planning_only
implementation_planning_allowed: false
production_identity_allowed: false
runtime_postgres_allowed: false
```

## Allowed Closure Readiness Result

The only readiness result this gate can support is:

```text
ready_for_architecture_decision_record
```

That result does not approve implementation planning or runtime implementation. It means a later
committed post-RC decision record may consider whether the identity/storage lane can continue
architecture planning from the reviewed evidence.

## Required Later Triage Update

If the closure gate eventually reports `closure_ready: true`, a separate committed triage update
must still:

- record the raw reviewer response and normalized response path;
- record reviewer label, source access, reviewed commit, and reviewed packet hash;
- add or update any `EXT-PROD-IAM-STORAGE-###` finding files;
- update [enterprise-readiness-gap-matrix.md](enterprise-readiness-gap-matrix.md);
- update [post-rc-decision-register.md](post-rc-decision-register.md);
- preserve runtime identity and storage behavior as blocked unless a later implementation sprint is
  explicitly approved;
- preserve local-principal labels as preview attribution, not production authentication;
- preserve SQLite as the only current runtime backend unless a later storage implementation
  decision explicitly changes that boundary;
- rerun `make release-check`;
- rerun `make review-candidate`.

## Boundaries That Remain Blocked

This closure gate must not approve:

- implementation planning;
- runtime implementation;
- production IAM;
- enterprise RBAC;
- tenant/team authorization runtime behavior;
- remote admin use;
- runtime Postgres;
- database migrations;
- backup/restore runtime behavior;
- retention enforcement;
- hosted control plane;
- custody-grade audit claims;
- compliance automation;
- hosted telemetry;
- remote MCP;
- SIEM adapter behavior;
- sandbox orchestration;
- local model invocation;
- trusted-host promotion;
- shell/Docker/Kubernetes/browser governed powers;
- arbitrary HTTP;
- broad filesystem writes;
- plugin SDK behavior;
- new governed tool powers;
- public/security-product positioning.
