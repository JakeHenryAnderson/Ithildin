# Public Security Product Positioning Response Kit

Status: response-intake kit for blocked `ERG-010`.

This kit packages the public/security-product positioning response workflow after a reviewer has
used `public-positioning-external-review-bundle.md`. It is a handoff convenience only. It does not
prove external review happened, does not close `ERG-010`, does not approve a claim-decision record,
and does not approve public/security-product positioning.

## Commands

Generate the response kit:

```sh
make public-security-product-positioning-response-kit
```

Validate wiring without writing persistent review artifacts:

```sh
make public-security-product-positioning-response-kit-check
```

Generated artifacts are written under:

```text
var/review-packets/v3/public-security-product-positioning-response-kit/
```

## Generated Artifacts

1. `00_PUBLIC_SECURITY_PRODUCT_POSITIONING_RESPONSE_KIT_INDEX.md`
2. `01_PUBLIC_SECURITY_PRODUCT_POSITIONING_RESPONSE_INTAKE_GUIDE.md`
3. `02_PUBLIC_SECURITY_PRODUCT_POSITIONING_NORMALIZED_RESPONSE_EXAMPLES.md`
4. `03_PUBLIC_SECURITY_PRODUCT_POSITIONING_CLOSURE_TRIAGE_COMMANDS.md`
5. `04_PUBLIC_SECURITY_PRODUCT_POSITIONING_QUEUE_AND_BOUNDARY_STATUS.md`
6. `05_PUBLIC_SECURITY_PRODUCT_POSITIONING_RESPONSE_KIT_EVIDENCE.md`
7. `public-security-product-positioning-response-kit-artifact-hashes.json`

## Boundary

The kit keeps `ERG-010` blocked unless a later, separate committed claim-decision record is reviewed
and accepted through the fail-closed closure gate. Even a favorable normalized response only supports
preparing that later record.

The kit does not approve production/security/compliance positioning, broader public distribution,
production deployment readiness, sandbox guarantee language, EDR/MDM claims, SIEM custody claims,
compliance claims, compliance automation, legal advice, automated certification, regulatory-grade
audit claims, custody-grade audit claims, tamper-proof logging, audit immutability claims,
production identity, enterprise RBAC, runtime Postgres, hosted telemetry, hosted MCP, remote MCP,
managed model serving, support/deployment/update/incident-response claims, sandbox orchestration,
local model invocation, trusted-host promotion, SIEM adapter behavior, compliance mapping runtime
behavior, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem writes,
plugin SDK behavior, or new governed tool powers.

## Intake Path

Place a real normalized reviewer response at:

```text
var/review-runs/public-security-product-positioning/normalized-response.json
```

Then run:

```sh
make public-security-product-positioning-decision-closure-check
make public-positioning-external-review-bundle-check
make docs-claims-public-preview-disposition-closure-check
make enterprise-external-review-queue-check
make review-run-manifest-refresh
make release-check
make review-candidate
```

If any closure gate fails, keep `ERG-010` blocked and record the reviewer response as input for a
follow-up claim-boundary cleanup sprint.
