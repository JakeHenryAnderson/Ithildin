# Sandbox/VM Live POC External Response Intake

Status: response-intake template for blocked `ERG-004`.

This template records a GPT 5.5 Pro / Very High or human expert response to the live sandbox/VM
worker proof-of-concept decision packet. It does not close `ERG-004` by itself. It does not mutate
reviewer findings, approve implementation planning, approve runtime implementation, approve live
VM/container inspection, approve sandbox orchestration, approve Mission Control runtime behavior,
approve local model invocation, approve trusted-host promotion, approve network expansion, approve
SIEM adapter behavior, approve production identity, approve runtime Postgres, approve hosted
telemetry, approve remote MCP, approve compliance automation, or approve public/security-product
positioning.

Current governed tool count: `24`.

Current `ERG-004` status before reviewer disposition: `blocked`.

Current selected capability: `not selected`.

Finding namespace: `EXT-LIVE-POC-###`.

Reviewed area for normalization: `sandbox-vm-live-poc`.

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

Answer every item from [sandbox-vm-live-poc-decision-packet.md](sandbox-vm-live-poc-decision-packet.md)
and [sandbox-vm-live-poc-preconditions-map.md](sandbox-vm-live-poc-preconditions-map.md):

1. Did the reviewer inspect the live POC decision packet and the referenced precondition artifacts?
2. Does the reviewer agree `ERG-004` remains blocked unless favorable `ERG-003` disposition exists?
3. Are the live POC preconditions complete enough for a later post-RC decision record?
4. Is the operator-managed VM/container profile boundary clear enough for planning-only review?
5. Are the cleanup transcript and failure transcript requirements sufficient for later POC planning?
6. Are the cross-source evidence fields sufficient for correlating operator intent, Ithildin audit,
   sandbox posture, local model/client evidence, and optional Mission Control display evidence?
7. Are there any critical/high findings?
8. If there are no critical/high findings, may a later committed decision record consider
   `approve_limited_operator_managed_poc_planning`?
9. Does the reviewer explicitly avoid approving runtime implementation, live VM/container
   inspection, VM/container lifecycle control, Mission Control execution authority, local model
   invocation, trusted-host promotion, SIEM delivery, or public/security-product positioning?

## Finding Extraction Table

Use this exact shape for actionable findings:

| Finding ID | Severity | Area | Affected files/functions | Blocking status | Disposition | Recommended fix |
| --- | --- | --- | --- | --- | --- | --- |
| EXT-LIVE-POC-### | critical/high/medium/low/informational | sandbox-vm-live-poc | path/function | blocking/should-fix/later/advisory | open | fix summary |

If the reviewer finds no actionable findings, the response must explicitly say `no findings` or
`finding_count: 0`.

## Normalization Command

After saving the raw response transcript, run the generic normalizer with the sandbox/VM live POC
area:

```sh
uv run python scripts/external_response_normalize.py \
  path/to/raw-response.md \
  --reviewer "reviewer label" \
  --reviewer-type "gpt-5.5-pro-or-human" \
  --source-access packet-and-source \
  --reviewed-commit "$(git rev-parse HEAD)" \
  --reviewed-packet-hash "sha256:<packet-hash>" \
  --area sandbox-vm-live-poc \
  --output var/review-runs/sandbox-vm-live-poc/normalized-response.json
```

The normalized response is intake evidence only. It sets `mutates_findings: false` and
`closes_external_review: false`; follow-up commits must separately add reviewer findings, update the
enterprise gap matrix or post-RC decision register, and rerun release gates.

## Allowed Intake Outcomes

The intake may record only the outcomes defined in the live POC decision packet:

- `continue_design_only`
- `revise_before_decision`
- `approve_limited_operator_managed_poc_planning`
- `block_live_poc`

Only a later committed triage update may move `ERG-004` away from `blocked`, and even a favorable
response can only support a later implementation-planning decision record. It cannot approve runtime
implementation.

## Boundaries That Remain Blocked

Even after a favorable response, this intake must not approve:

- implementation planning without a later committed decision record;
- runtime implementation;
- live VM/container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- local model invocation;
- Mission Control runtime behavior;
- trusted-host promotion;
- network expansion;
- SIEM adapter behavior;
- production identity;
- runtime Postgres;
- hosted telemetry;
- remote MCP;
- compliance automation;
- new governed tool powers;
- public/security-product positioning.

## Validation

Run:

```sh
make sandbox-vm-live-poc-external-response-intake-check
make external-findings-intake-dry-run
make sandbox-vm-live-poc-preconditions-map-check
make sandbox-vm-live-poc-decision-packet-check
```
