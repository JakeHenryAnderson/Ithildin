# Public/Security-Product Positioning Decision Closure Gate

Status: fail-closed closure gate for blocked `ERG-010` and `PRD-PUBLIC-POSITIONING-001`.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Validate this gate with:

```sh
make public-security-product-positioning-decision-closure-check
```

This gate checks whether normalized external/source review evidence is strong enough to allow a
future claim-specific go/no-go decision record for public/security-product positioning. It does not
approve broader public distribution, production deployment readiness, security-product positioning,
sandbox claims, EDR/MDM claims, SIEM custody claims, compliance claims, production identity,
runtime Postgres, hosted telemetry, remote MCP, hosted MCP, plugin SDK behavior, compliance
automation, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem
writes, or new governed tool powers.

## Normalized Response Path

The optional normalized response is:

```text
var/review-runs/public-security-product-positioning/normalized-response.json
```

If this file is absent, malformed, incomplete, or unfavorable, this gate remains valid but
fail-closed:

- `closure_ready: false`
- `erg_010_status: blocked`
- `public_security_product_positioning_allowed: false`
- `production_security_compliance_positioning_allowed: false`
- `claim_decision_record_allowed: false`
- `runtime_changes_allowed: false`

## Required Normalized Response Shape

The response must use:

- `response_type: ithildin.external_review.normalized_response`
- reviewed area: `public-security-product-positioning`
- `source_access`: `source-level` or `packet-and-source`
- finding namespace: `EXT-PUBLIC-POSITIONING-###`
- `can_close_source_rows: true`
- `mutates_findings: false`
- `closes_external_review: false`
- `reviewed_packet_hash`: a `sha256:` digest
- `no critical/high findings`
- `disposition_outcome: ready_for_claim_decision_record`

If every required field validates, the only allowed closure state is:

```text
ready_for_claim_decision_record
```

That state allows a later separate committed triage update to draft a claim-specific decision
record. It still does not approve any public/security-product positioning, production/security/
compliance positioning, runtime behavior, or new tool power.

## Blocked Boundaries

This closure gate keeps all of the following blocked:

- broader public distribution;
- production deployment ready wording;
- security-product positioning;
- production/security/compliance positioning;
- sandbox guarantee language;
- EDR/MDM claims;
- SIEM custody claims;
- compliance claims;
- compliance automation;
- legal advice;
- automated certification;
- regulatory-grade audit claims;
- custody-grade audit claims;
- tamper-proof logging;
- audit immutability claims;
- production identity;
- enterprise RBAC;
- runtime Postgres;
- hosted telemetry;
- hosted MCP;
- remote MCP transport/gateway claims;
- managed model serving;
- arbitrary-tool safety wording;
- broad autonomous execution;
- HIPAA/GLBA/SOX/GDPR/SOC 2/NIST/CIS compliance;
- support/deployment/update/incident-response claims without matching review evidence;
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

## Forbidden Phrases

This gate fails if this document uses overclaiming language that treats blocked public positioning,
production or compliance positioning, deployment readiness, sandbox posture, SIEM custody,
compliance claims, or `ERG-010` itself as approved or closed.

## Relationship To The Intake

The intake remains the baseline no-go document:

- `public-security-product-positioning-decision-intake.md`
- `make public-security-product-positioning-decision-intake-check`

This closure gate only adds a repeatable way to test whether future external review evidence is
sufficient to begin a separate decision-record drafting step. Until that happens, `ERG-010` remains
blocked and broad public/security-product positioning remains no-go.
