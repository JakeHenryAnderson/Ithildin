# Docs/Claims Public-Preview Disposition Closure Gate

Status: fail-closed closure gate for residual docs/claims/public-preview wording rows.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Validate this gate with:

```sh
make docs-claims-public-preview-disposition-closure-check
```

This gate covers the legacy packet-only or gate-source rows that remain external-pending in the
source-review closure matrix:

- Documentation IA;
- Threat model refresh;
- v0.4 packet generator;
- v0.4 external packet;
- v0.5 roadmap;
- Capability expansion gate;
- Evidence-confusion gate;
- v0.5 threat model delta;
- v0.5 external review prompt;
- v0.5 boundary decision draft;
- v0.5 handoff packet;
- v0.6 boundary charter.

The gate is intentionally narrower than runtime source review. It can only validate that an external
reviewer found the docs/claims/public-preview wording coherent for the local-preview boundary. It
does not approve capability expansion, public/security-product positioning, production deployment,
runtime behavior, new governed tool powers, sandbox guarantees, SIEM custody, compliance claims,
production identity, runtime Postgres, hosted telemetry, remote MCP, plugin SDK behavior, arbitrary
HTTP, or broad filesystem writes.

## Normalized Response Path

The optional normalized response is:

```text
var/review-runs/docs-claims-public-preview/normalized-response.json
```

If this file is absent, malformed, incomplete, or unfavorable, this gate remains valid but
fail-closed:

- `closure_ready: false`
- `docs_claims_status: external_pending`
- `docs_claims_public_preview_wording_closed: false`
- `capability_expansion_allowed: false`
- `public_security_product_positioning_allowed: false`
- `runtime_changes_allowed: false`

## Required Normalized Response Shape

The response must use:

- `response_type: ithildin.external_review.normalized_response`
- reviewed area: `docs-claims-public-preview`
- `source_access`: `packet-only`, `source-level`, or `packet-and-source`
- finding namespace: `EXT-DOCS-CLAIMS-###`
- `can_close_source_rows: true`
- `mutates_findings: false`
- `closes_external_review: false`
- `reviewed_packet_hash`: a `sha256:` digest
- `no critical/high findings`
- `disposition_outcome: close_docs_claims_for_local_preview`

If every required field validates, the only allowed closure state is:

```text
closed_local_preview_docs_claims
```

That state allows a later separate committed matrix update to mark only these docs/claims rows as
closed for local-preview wording. It still does not approve capability expansion, public/security-
product positioning, production/security/compliance positioning, runtime behavior, or new tool
powers.

## Blocked Boundaries

This closure gate keeps all of the following blocked:

- capability expansion;
- public/security-product positioning;
- production/security/compliance positioning;
- production deployment ready wording;
- sandbox guarantee language;
- EDR/MDM claims;
- SIEM custody claims;
- compliance claims;
- compliance automation;
- production identity;
- enterprise RBAC;
- runtime Postgres;
- hosted telemetry;
- hosted MCP;
- remote MCP transport/gateway claims;
- managed model serving;
- Mission Control runtime behavior;
- sandbox orchestration;
- local model invocation;
- trusted-host promotion;
- SIEM adapter behavior;
- compliance mapping runtime behavior;
- shell/Docker/Kubernetes/browser governed powers;
- arbitrary HTTP;
- broad filesystem writes;
- plugin SDK behavior;
- new governed tool powers.

## Relationship To Other Gates

This gate complements:

- `external-review-closure-gate.md`
- `v0.7-external-review-row-partition.md`
- `public-security-product-positioning-decision-closure-gate.md`
- `capability-decision-report`
- `no-new-powers-guardrail`

It is a closure mechanism for residual docs/claims rows only. Runtime/security implementation lanes
still require their own source-level or packet-and-source review evidence, and public/security-
product positioning remains blocked by `ERG-010`.
