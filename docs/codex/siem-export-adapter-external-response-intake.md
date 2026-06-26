# SIEM Export Adapter External Response Intake

Status: response-intake template for planning-only `ERG-008`.

This template records a GPT 5.5 Pro / Very High or human expert response to the SIEM export adapter
disposition packet. It does not close `ERG-008` by itself. It does not mutate reviewer findings,
approve implementation planning, approve runtime implementation, approve SIEM adapter behavior,
approve hosted telemetry, approve remote delivery, approve custody-grade audit claims, approve
external notarization, approve immutable storage, approve production identity, approve runtime
Postgres, approve compliance automation, approve security-operations control-plane claims, approve
hosted control plane behavior, approve sandbox orchestration, approve local model invocation,
approve trusted-host promotion, approve shell/Docker/Kubernetes/browser governed powers, approve
arbitrary HTTP, approve broad filesystem writes, approve plugin SDK behavior, approve new governed
tool powers, or approve public/security-product positioning.

Current governed tool count: `24`.

Current `ERG-008` status before reviewer disposition: `planning_only`.

Current selected capability: `not selected`.

Finding namespace: `EXT-SIEM-ADAPTER-###`.

Reviewed area for normalization: `siem-export-adapter`.

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
[siem-export-adapter-disposition-packet.md](siem-export-adapter-disposition-packet.md) and
[siem-export-adapter-architecture.md](siem-export-adapter-architecture.md):

1. Did the reviewer inspect the SIEM export adapter disposition packet and architecture evidence?
2. Is the event category and safe-field boundary coherent enough for continued architecture
   planning?
3. Are redaction, denylist, and no-export expectations complete enough for continued design?
4. Are delivery profile, local-only versus remote posture, retry, backpressure, and dead-letter
   questions explicit enough for continued design?
5. Are signing, verification, key-loss, ordering, idempotency, replay, and compatibility questions
   complete enough for continued design?
6. Are there any critical/high findings?
7. If there are no critical/high findings, may the lane continue architecture planning while
   `ERG-008` remains planning-only and runtime implementation remains blocked?
8. Does the reviewer explicitly avoid approving SIEM adapter runtime behavior, hosted telemetry,
   remote delivery, custody-grade audit claims, external notarization, immutable storage,
   compliance automation, security-operations control-plane claims, or public/security-product
   positioning?

## Finding Extraction Table

Use this exact shape for actionable findings:

| Finding ID | Severity | Area | Affected files/functions | Blocking status | Disposition | Recommended fix |
| --- | --- | --- | --- | --- | --- | --- |
| EXT-SIEM-ADAPTER-### | critical/high/medium/low/informational | siem-export-adapter | path/function | blocking/should-fix/later/advisory | open | fix summary |

If the reviewer finds no actionable findings, the response must explicitly say `no findings` or
`finding_count: 0`.

## Normalization Command

After saving the raw response transcript, run the generic normalizer with the SIEM export adapter
area:

```sh
uv run python scripts/external_response_normalize.py \
  path/to/raw-response.md \
  --reviewer "reviewer label" \
  --reviewer-type "gpt-5.5-pro-or-human" \
  --source-access packet-and-source \
  --reviewed-commit "$(git rev-parse HEAD)" \
  --reviewed-packet-hash "sha256:<packet-hash>" \
  --area siem-export-adapter \
  --output var/review-runs/siem-export-adapter/normalized-response.json
```

The normalized response is intake evidence only. It sets `mutates_findings: false` and
`closes_external_review: false`; follow-up commits must separately add reviewer findings, update the
enterprise gap matrix or post-RC decision register, and rerun release gates.

## Allowed Intake Outcomes

The intake may record only the outcomes defined in the SIEM export adapter disposition packet:

- `continue_architecture_planning`
- `revise_before_more_planning`
- `block_runtime_implementation`

Only a later committed triage update may move `ERG-008` away from `planning_only`, and even a
favorable response can only support later architecture planning or a later implementation planning
decision record. It cannot approve runtime implementation.

## Boundaries That Remain Blocked

Even after a favorable response, this intake must not approve:

- implementation planning without a later committed decision record;
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

## Validation

Run:

```sh
make siem-export-adapter-external-response-intake-check
make external-findings-intake-dry-run
make siem-export-adapter-disposition-packet-check
make siem-export-adapter-architecture-check
```
