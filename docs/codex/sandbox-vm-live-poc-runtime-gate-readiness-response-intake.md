# Sandbox/VM Live POC Runtime Gate Readiness Response Intake

Status: response-intake template for `ERG-004` runtime gate-readiness review.

This template records a GPT 5.5 Pro / Very High, High, xhigh, or human expert response to the
runtime gate-readiness packet. It does not close `ERG-004`. It does not mutate reviewer findings,
approve runtime implementation, approve live VM/container inspection, approve VM/container
lifecycle management, approve sandbox orchestration, approve Mission Control runtime behavior,
approve local model invocation, approve trusted-host promotion, approve host writes, approve
network expansion, approve API/MCP profile loading, approve SIEM adapter behavior, approve
production identity, approve runtime Postgres, approve hosted telemetry, approve remote MCP,
approve compliance automation, approve new governed tool powers, or approve public/security-product
positioning.

Current governed tool count: `24`.

Current `ERG-004` status before reviewer disposition: `ready_for_runtime_implementation_gate_review`.

Current selected capability: `not selected`.

Finding namespace: `EXT-LIVE-GATE-###`.

Reviewed area for normalization: `sandbox-vm-live-poc-runtime-gate-readiness`.

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
[sandbox-vm-live-poc-runtime-gate-readiness-review-bundle.md](sandbox-vm-live-poc-runtime-gate-readiness-review-bundle.md),
[sandbox-vm-live-poc-runtime-implementation-gate.md](sandbox-vm-live-poc-runtime-implementation-gate.md),
and
[sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton.md](sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton.md):

1. Did the reviewer inspect the runtime gate-readiness packet and the referenced implementation
   gate, descriptor contract, internal reviews, and command evidence?
2. Does the reviewer agree the packet preserves operator-managed VM lifecycle and OS isolation?
3. Does the reviewer agree the descriptor contract stays closed, safe-label-only, hash/correlation
   oriented, and secret-free?
4. Do the negative fixtures block lifecycle control, live inspection, local model invocation,
   Mission Control authority, host writes, trusted-host promotion, network expansion, and API/MCP
   profile loading?
5. Does the reviewer agree source review remains required before any live runtime readiness claim?
6. Are there any critical/high findings?
7. If there are no critical/high findings, may a later committed decision record consider
   `approved_for_descriptor_only_runtime_implementation_planning`?
8. Does the reviewer explicitly avoid approving runtime implementation, live VM/container
   inspection, VM/container lifecycle management, sandbox orchestration, Mission Control runtime
   authority, local model invocation, trusted-host promotion, host writes, network expansion,
   API/MCP profile loading, SIEM adapter runtime behavior, or new governed tool powers?

## Finding Extraction Table

Use this exact shape for actionable findings:

| Finding ID | Severity | Area | Affected files/functions | Blocking status | Disposition | Recommended fix |
| --- | --- | --- | --- | --- | --- | --- |
| EXT-LIVE-GATE-### | critical/high/medium/low/informational | sandbox-vm-live-poc-runtime-gate-readiness | path/function | blocking/should-fix/later/advisory | open | fix summary |

If the reviewer finds no actionable findings, the response must explicitly say `no findings` or
`finding_count: 0`.

## Normalization Command

After saving the raw response transcript, run the generic normalizer with the runtime
gate-readiness area:

```sh
uv run python scripts/external_response_normalize.py \
  path/to/raw-response.md \
  --reviewer "reviewer label" \
  --reviewer-type "high-or-xhigh-or-human" \
  --source-access packet-and-source \
  --reviewed-commit "$(git rev-parse HEAD)" \
  --reviewed-packet-hash "sha256:<packet-hash>" \
  --area sandbox-vm-live-poc-runtime-gate-readiness \
  --output var/review-runs/sandbox-vm-live-poc-runtime-gate-readiness/normalized-response.json
```

The normalized response is intake evidence only. It sets `mutates_findings: false` and
`closes_external_review: false`; follow-up commits must separately add reviewer findings, update
the decision-record evidence, and rerun release gates.

## Allowed Intake Outcomes

The intake may record only these outcomes:

- `approved_for_descriptor_only_runtime_implementation_planning`
- `revise_before_descriptor_only_planning`
- `block_descriptor_only_planning`

Only a later committed decision record may move `ERG-004` from
`ready_for_runtime_implementation_gate_review` to
`ready_for_descriptor_only_runtime_implementation_planning`, and even a favorable response can only
support later implementation planning. It cannot approve runtime implementation.

## Boundaries That Remain Blocked

Even after a favorable response, this intake must not approve:

- runtime implementation;
- live VM/container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- Mission Control runtime behavior;
- local model invocation;
- trusted-host promotion;
- host writes;
- network expansion;
- API/MCP profile loading;
- SIEM adapter runtime behavior;
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
make sandbox-vm-live-poc-runtime-gate-readiness-response-intake-check
make sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run
make sandbox-vm-live-poc-runtime-gate-readiness-review-bundle-check
make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton-check
make external-findings-intake-dry-run
```
