# Sandbox/VM Static Preflight External Response Intake

Status: response-intake template for `ERG-003`.

This template records a GPT 5.5 Pro / Very High or human expert response to the
CLI-only sandbox/VM static preflight source-review packet. It does not close `ERG-003` by itself.
It does not mutate reviewer findings, approve live VM/container inspection, sandbox orchestration,
Mission Control runtime behavior, local model invocation, trusted-host promotion, network
expansion, API/MCP profile loading, new governed tools, production identity, runtime Postgres,
hosted telemetry, remote MCP, SIEM adapters, compliance automation, or public/security-product
positioning.

Current governed tool count: `24`.

Current `ERG-003` status before reviewer disposition: `external_review_required`.

Finding namespace: `EXT-SVP-###`.

Reviewed area for normalization: `sandbox-vm-static-preflight`.

## Required Inputs

- Reviewer name/model or human reviewer label:
- Reviewer type:
- Source access: `source-level` / `packet-and-source` / `packet-only` / `docs-only`
- Reviewed commit:
- Reviewed packet path:
- Reviewed packet artifact hash: SHA-256 of
  `var/review-packets/v3/sandbox-vm-static-preflight-external-review/sandbox-vm-static-preflight-external-review-artifact-hashes.json`
  as printed by `make sandbox-vm-static-preflight-reviewed-packet-hash`
- Reviewed response transcript path:
- Review date:

## Required Disposition Answers

Answer every item from
[sandbox-vm-static-preflight-disposition-plan.md](sandbox-vm-static-preflight-disposition-plan.md):

1. Did the reviewer inspect the static preflight source-review packet and the source files named in
   that packet?
2. Does the CLI-only fixture runner stay within the approved boundary?
3. Are the static profile fixture contract and negative fixtures sufficient for local-preview
   planning evidence?
4. Are safe-label and safe-error expectations strong enough for packet/display use?
5. Does `XH-SANDBOX-PREFLIGHT-001` appear fixed for the local-preview fixture lane?
6. Are there any critical/high findings?
7. If there are no critical/high findings, can `ERG-003` move from `external_review_required` to
   `closed_local_preview_static_preflight`?
8. Does the reviewer explicitly avoid approving live VM/container control, Mission Control runtime
   behavior, local model invocation, trusted-host promotion, or production/security-product claims?

## Finding Extraction Table

Use this exact shape for actionable findings:

| Finding ID | Severity | Area | Affected files/functions | Blocking status | Disposition | Recommended fix |
| --- | --- | --- | --- | --- | --- | --- |
| EXT-SVP-### | critical/high/medium/low/informational | sandbox-vm-static-preflight | path/function | blocking/should-fix/later/advisory | open | fix summary |

If the reviewer finds no actionable findings, the response must explicitly say `no findings` or
`finding_count: 0`.

## Normalization Command

After saving the raw response transcript, run the generic normalizer with the sandbox/VM preflight
area:

```sh
REVIEWED_PACKET_HASH="$(make -s sandbox-vm-static-preflight-reviewed-packet-hash)"
uv run python scripts/external_response_normalize.py \
  path/to/raw-response.md \
  --reviewer "reviewer label" \
  --reviewer-type "gpt-5.5-pro-or-human" \
  --source-access packet-and-source \
  --reviewed-commit "$(git rev-parse HEAD)" \
  --reviewed-packet-hash "$REVIEWED_PACKET_HASH" \
  --area sandbox-vm-static-preflight \
  --output var/review-runs/sandbox-vm-static-preflight/normalized-response.json
```

If the helper reports that the artifact-hash manifest is missing, regenerate the current handoff
first:

```sh
make sandbox-vm-static-preflight-external-review-bundle
make sandbox-vm-static-preflight-reviewed-packet-hash
```

The normalized response is intake evidence only. It sets `mutates_findings: false` and
`closes_external_review: false`; follow-up commits must separately add reviewer findings, update the
closure matrix or enterprise gap matrix, and rerun release gates.
The fail-closed closure gate in
[sandbox-vm-static-preflight-disposition-closure-gate.md](sandbox-vm-static-preflight-disposition-closure-gate.md)
validates whether that normalized response is strong enough for a later committed triage update.
Use
[sandbox-vm-static-preflight-response-application-record.md](sandbox-vm-static-preflight-response-application-record.md)
as the manager-owned checklist for applying the real response without closing `ERG-003` directly or
unblocking `ERG-004`.

## Allowed Intake Outcomes

The intake may record only the outcomes defined in the disposition plan:

- `external_review_requested`
- `external_review_changes_requested`
- `closed_local_preview_static_preflight`
- `accepted_deferred`
- `blocked`

Only a later committed triage update may move `ERG-003` away from `external_review_required`, and
only when the recorded evidence supports that move.

## Boundaries That Remain Blocked

Even after a favorable response, this intake must not approve:

- live VM/container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- local model invocation;
- Mission Control runtime behavior;
- trusted-host promotion;
- network expansion;
- API/MCP profile loading;
- production identity;
- SIEM delivery;
- compliance automation;
- public/security-product positioning.

## Validation

Run:

```sh
make sandbox-vm-static-preflight-external-response-intake-check
make sandbox-vm-static-preflight-disposition-closure-check
make sandbox-vm-static-preflight-response-application-record-check
make external-findings-intake-dry-run
make sandbox-vm-static-preflight-disposition-plan-check
```
