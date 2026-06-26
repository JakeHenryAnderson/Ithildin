# Mission Control Display External Response Intake

Status: response-intake template for planning-only `ERG-002`.

This template records a GPT 5.5 Pro / Very High or human expert response to the Mission Control
display/importer disposition packet. It does not close `ERG-002` by itself. It does not mutate
reviewer findings, approve runtime implementation, approve Mission Control runtime importer
behavior, approve Mission Control execution authority, approve Mission Control policy authority,
approve Mission Control approval authority, approve Mission Control audit authority, approve API
callbacks, approve polling or mutating Ithildin APIs, approve local model invocation, approve
VM/container lifecycle management, approve sandbox orchestration, approve trusted-host promotion,
approve SIEM adapter behavior, approve production identity, approve runtime Postgres, approve
hosted telemetry, approve remote delivery, approve shell/Docker/Kubernetes/browser governed powers,
approve arbitrary HTTP, approve broad filesystem writes, approve compliance automation, approve new
governed tool powers, or approve public/security-product positioning.

Current governed tool count: `24`.

Current `ERG-002` status before reviewer disposition: `planning_only`.

Current selected capability: `not selected`.

Finding namespace: `EXT-MC-DISPLAY-###`.

Reviewed area for normalization: `mission-control-display`.

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
[mission-control-display-disposition-packet.md](mission-control-display-disposition-packet.md) and
[mission-control-display-decision-intake.md](mission-control-display-decision-intake.md):

1. Did the reviewer inspect the Mission Control display disposition packet, proposal, importer plan,
   schema contract, negative fixtures, side handoff plan, implementation ticket, and review packet?
2. Is the display-only importer boundary coherent enough for continued Mission Control-side design
   planning?
3. Are operator-selected local packet sources, stale packet warnings, mismatched commit/hash
   warnings, schema validation, artifact hashes, and negative fixtures explicit enough for continued
   planning?
4. Are display allowlists and hidden-field denylists complete enough to avoid raw prompts, file
   contents, diffs, response bodies, token values, private keys, raw host paths, environment values,
   dependency names, package script values, or raw sandbox-internal paths?
5. Are Mission Control non-authority boundaries clear for execution, policy, approval, audit,
   sandbox orchestration, local model invocation, trusted-host promotion, SIEM, identity, storage,
   remote delivery, and compliance claims?
6. Are there any critical/high findings?
7. If there are no critical/high findings, may the lane continue design-only Mission Control-side
   planning while `ERG-002` remains planning-only and runtime importer implementation remains
   blocked?
8. Does the reviewer explicitly avoid approving Mission Control runtime importer behavior, Mission
   Control execution/policy/approval/audit authority, API callbacks, polling or mutating Ithildin
   APIs, local model invocation, sandbox orchestration, trusted-host promotion, SIEM adapter
   behavior, compliance automation, or public/security-product positioning?

## Finding Extraction Table

Use this exact shape for actionable findings:

| Finding ID | Severity | Area | Affected files/functions | Blocking status | Disposition | Recommended fix |
| --- | --- | --- | --- | --- | --- | --- |
| EXT-MC-DISPLAY-### | critical/high/medium/low/informational | mission-control-display | path/function | blocking/should-fix/later/advisory | open | fix summary |

If the reviewer finds no actionable findings, the response must explicitly say `no findings` or
`finding_count: 0`.

## Normalization Command

After saving the raw response transcript, run the generic normalizer with the Mission Control display
area:

```sh
uv run python scripts/external_response_normalize.py \
  path/to/raw-response.md \
  --reviewer "reviewer label" \
  --reviewer-type "gpt-5.5-pro-or-human" \
  --source-access packet-and-source \
  --reviewed-commit "$(git rev-parse HEAD)" \
  --reviewed-packet-hash "sha256:<packet-hash>" \
  --area mission-control-display \
  --output var/review-runs/mission-control-display/normalized-response.json
```

The normalized response is intake evidence only. It sets `mutates_findings: false` and
`closes_external_review: false`; follow-up commits must separately add reviewer findings, update the
enterprise gap matrix or post-RC decision register, and rerun release gates.
Before a later committed triage update may use the response to support design-only continuation,
run the fail-closed closure gate in
[mission-control-display-disposition-closure-gate.md](mission-control-display-disposition-closure-gate.md).

## Allowed Intake Outcomes

The intake may record only the outcomes defined in the Mission Control display disposition packet:

- `continue_design_only`
- `revise_before_more_planning`
- `block_runtime_implementation`

Only a later committed triage update may move `ERG-002` away from `planning_only`, and even a
favorable response can only support continued design-only planning or a later implementation
decision record. It cannot approve runtime importer implementation.

## Boundaries That Remain Blocked

Even after a favorable response, this intake must not approve:

- runtime implementation;
- Mission Control runtime importer behavior;
- Mission Control execution authority;
- Mission Control policy authority;
- Mission Control approval authority;
- Mission Control audit authority;
- API callbacks;
- polling or mutating Ithildin APIs;
- local model invocation;
- VM/container lifecycle management;
- sandbox orchestration;
- trusted-host promotion;
- SIEM adapter behavior;
- production identity;
- runtime Postgres;
- hosted telemetry;
- remote delivery;
- shell/Docker/Kubernetes/browser governed powers;
- arbitrary HTTP;
- broad filesystem writes;
- compliance automation;
- new governed tool powers;
- public/security-product positioning.

## Validation

Run:

```sh
make mission-control-display-external-response-intake-check
make mission-control-display-disposition-closure-check
make external-findings-intake-dry-run
make mission-control-display-disposition-packet-check
make mission-control-display-decision-intake-check
```
