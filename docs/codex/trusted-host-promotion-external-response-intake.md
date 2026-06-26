# Trusted-Host Promotion External Response Intake

Status: response-intake template for blocked `ERG-005`.

This template records a GPT 5.5 Pro / Very High or human expert response to the trusted-host
promotion disposition packet. It does not close `ERG-005` by itself. It does not mutate reviewer
findings, approve implementation planning, approve runtime implementation, approve trusted-host
promotion, approve direct host writes, approve overwrite/delete/move behavior, approve broad archive
extraction, approve automatic promotion, approve promotion without exact artifact hash binding,
approve promotion without approval evidence, approve Mission Control runtime behavior, approve local
model invocation, approve VM/container lifecycle management, approve sandbox orchestration, approve
SIEM adapter behavior, approve production identity, approve runtime Postgres, approve hosted
telemetry, approve remote MCP, approve shell/Docker/Kubernetes/browser governed powers, approve
arbitrary HTTP, approve broad filesystem writes, approve compliance automation, or approve
public/security-product positioning.

Current governed tool count: `24`.

Current `ERG-005` status before reviewer disposition: `blocked`.

Current selected capability: `not selected`.

Finding namespace: `EXT-TRUSTED-HOST-###`.

Reviewed area for normalization: `trusted-host-promotion`.

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
[trusted-host-promotion-disposition-packet.md](trusted-host-promotion-disposition-packet.md) and
[trusted-host-promotion-source-review.md](trusted-host-promotion-source-review.md):

1. Did the reviewer inspect the trusted-host promotion disposition packet and the referenced
   source-review artifacts?
2. Are the source/staging/approved/evidence zone labels precise enough and non-authoritative?
3. Does the implementation-plan skeleton require exact artifact hash binding, approval binding,
   one-time scope evidence, conflict/replay/stale/path-escape denials, and policy/manifest evidence
   before any future runtime path?
4. Are the negative fixture and state-machine expectations strong enough for a future
   implementation proposal to be considered?
5. Does the internal review appear sufficient for design-only continuation?
6. Are there any critical/high findings?
7. If there are no critical/high findings, may the lane continue design-only planning while
   `ERG-005` remains blocked from runtime implementation?
8. Does the reviewer explicitly avoid approving host promotion, direct host writes,
   overwrite/delete/move behavior, broad archive extraction, automatic promotion, Mission Control
   runtime behavior, local model invocation, sandbox orchestration, SIEM adapter behavior, or
   production/security-product claims?

## Finding Extraction Table

Use this exact shape for actionable findings:

| Finding ID | Severity | Area | Affected files/functions | Blocking status | Disposition | Recommended fix |
| --- | --- | --- | --- | --- | --- | --- |
| EXT-TRUSTED-HOST-### | critical/high/medium/low/informational | trusted-host-promotion | path/function | blocking/should-fix/later/advisory | open | fix summary |

If the reviewer finds no actionable findings, the response must explicitly say `no findings` or
`finding_count: 0`.

## Normalization Command

After saving the raw response transcript, run the generic normalizer with the trusted-host
promotion area:

```sh
uv run python scripts/external_response_normalize.py \
  path/to/raw-response.md \
  --reviewer "reviewer label" \
  --reviewer-type "gpt-5.5-pro-or-human" \
  --source-access packet-and-source \
  --reviewed-commit "$(git rev-parse HEAD)" \
  --reviewed-packet-hash "sha256:<packet-hash>" \
  --area trusted-host-promotion \
  --output var/review-runs/trusted-host-promotion/normalized-response.json
```

The normalized response is intake evidence only. It sets `mutates_findings: false` and
`closes_external_review: false`; follow-up commits must separately add reviewer findings, update the
enterprise gap matrix or post-RC decision register, and rerun release gates.

## Allowed Intake Outcomes

The intake may record only the outcomes defined in the trusted-host promotion disposition packet:

- `continue_design_only`
- `revise_before_more_planning`
- `block_runtime_implementation`

Only a later committed triage update may move `ERG-005` away from `blocked`, and even a favorable
response can only support later design-only planning or a later implementation-planning decision
record. It cannot approve runtime implementation.

## Boundaries That Remain Blocked

Even after a favorable response, this intake must not approve:

- implementation planning without a later committed decision record;
- runtime implementation;
- trusted-host promotion;
- direct host writes;
- overwrite/delete/move behavior;
- broad archive extraction;
- automatic promotion;
- promotion without exact artifact hash binding;
- promotion without approval evidence;
- Mission Control runtime behavior;
- local model invocation;
- VM/container lifecycle management;
- sandbox orchestration;
- SIEM adapter behavior;
- production identity;
- runtime Postgres;
- hosted telemetry;
- remote MCP;
- shell/Docker/Kubernetes/browser governed powers;
- arbitrary HTTP;
- broad filesystem writes;
- compliance automation;
- new governed tool powers;
- public/security-product positioning.

## Validation

Run:

```sh
make trusted-host-promotion-external-response-intake-check
make external-findings-intake-dry-run
make trusted-host-promotion-disposition-packet-check
make trusted-host-promotion-source-review-packet-check
```
