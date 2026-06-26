# Compliance Mapping External Response Intake

Status: response-intake template for planning-only `ERG-009`.

This template records a GPT 5.5 Pro / Very High or human expert response to the compliance mapping
disposition packet. It does not close `ERG-009` by itself. It does not mutate reviewer findings,
approve implementation planning, approve runtime implementation, approve compliance mapping runtime
behavior, approve compliance automation, approve legal advice, approve automated certification,
approve HIPAA/GLBA/SOX/GDPR/SOC 2/NIST/CIS or other regulated-industry compliance claims, approve
custody-grade audit claims, approve external notarization, approve immutable storage, approve
production identity, approve runtime Postgres, approve SIEM adapter behavior, approve hosted
telemetry, approve remote delivery, approve sandbox orchestration, approve local model invocation,
approve trusted-host promotion, approve shell/Docker/Kubernetes/browser governed powers, approve
arbitrary HTTP, approve broad filesystem writes, approve plugin SDK behavior, approve new governed
tool powers, or approve public/security-product positioning.

Current governed tool count: `24`.

Current `ERG-009` status before reviewer disposition: `planning_only`.

Current selected capability: `not selected`.

Finding namespace: `EXT-COMPLIANCE-MAPPING-###`.

Reviewed area for normalization: `compliance-mapping`.

## Required Inputs

- Reviewer name/model or human reviewer label:
- Reviewer type:
- Source access: `source-level` / `packet-and-source` / `packet-only` / `docs-only`
- Reviewed commit:
- Reviewed packet path:
- Reviewed packet artifact hash:
- Reviewed response transcript path:
- Review date:

## Required Disposition Answers

Answer every item from
[compliance-mapping-disposition-packet.md](compliance-mapping-disposition-packet.md) and
[compliance-mapping-architecture.md](compliance-mapping-architecture.md):

1. Did the reviewer inspect the compliance mapping disposition packet and architecture evidence?
2. Is the target framework/control-family boundary coherent enough for continued architecture
   planning?
3. Are mapping-template shape, required fields, versioning, and unsupported-control handling
   explicit enough for continued design?
4. Are evidence-field allowlists, denylist/non-export expectations, and incident-reconstruction
   limits complete enough for continued design?
5. Are operator responsibility language, legal-review boundary, false-assurance warnings, and
   non-applicability language complete enough for continued design?
6. Are accepted-risk impacts for local principals, audit custody, sandbox posture, identity/storage,
   and review status explicit enough for continued design?
7. Are there any critical/high findings?
8. If there are no critical/high findings, may the lane continue architecture planning while
   `ERG-009` remains planning-only and runtime implementation remains blocked?
9. Does the reviewer explicitly avoid approving runtime compliance mapping, compliance automation,
   legal advice, automated certification, regulated-industry compliance claims, custody-grade audit
   claims, SIEM adapter behavior, or public/security-product positioning?

## Finding Extraction Table

Use this exact shape for actionable findings:

| Finding ID | Severity | Area | Affected files/functions | Blocking status | Disposition | Recommended fix |
| --- | --- | --- | --- | --- | --- | --- |
| EXT-COMPLIANCE-MAPPING-### | critical/high/medium/low/informational | compliance-mapping | path/function | blocking/should-fix/later/advisory | open | fix summary |

If the reviewer finds no actionable findings, the response must explicitly say `no findings` or
`finding_count: 0`.

## Normalization Command

After saving the raw response transcript, run the generic normalizer with the compliance mapping
area:

```sh
uv run python scripts/external_response_normalize.py \
  path/to/raw-response.md \
  --reviewer "reviewer label" \
  --reviewer-type "gpt-5.5-pro-or-human" \
  --source-access packet-and-source \
  --reviewed-commit "$(git rev-parse HEAD)" \
  --reviewed-packet-hash "sha256:<packet-hash>" \
  --area compliance-mapping \
  --output var/review-runs/compliance-mapping/normalized-response.json
```

The normalized response is intake evidence only. It sets `mutates_findings: false` and
`closes_external_review: false`; follow-up commits must separately add reviewer findings, update the
enterprise gap matrix or post-RC decision register, and rerun release gates.

## Allowed Intake Outcomes

The intake may record only the outcomes defined in the compliance mapping disposition packet:

- `continue_architecture_planning`
- `revise_before_more_planning`
- `block_runtime_implementation`

Only a later committed triage update may move `ERG-009` away from `planning_only`, and even a
favorable response can only support later architecture planning or a later implementation planning
decision record. It cannot approve runtime implementation.

## Boundaries That Remain Blocked

Even after a favorable response, this intake must not approve:

- implementation planning without a later committed decision record;
- runtime implementation;
- compliance mapping runtime behavior;
- compliance automation;
- legal advice;
- automated certification;
- HIPAA/GLBA/SOX/GDPR/SOC 2/NIST/CIS or other regulated-industry compliance claims;
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

## Validation

Run:

```sh
make compliance-mapping-external-response-intake-check
make external-findings-intake-dry-run
make compliance-mapping-disposition-packet-check
make compliance-mapping-architecture-check
```
