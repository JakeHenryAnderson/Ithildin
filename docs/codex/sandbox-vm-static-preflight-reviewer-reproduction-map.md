# Sandbox/VM Static Preflight Reviewer Reproduction Map

Status: reviewer reproduction map for `ERG-003`.

This map gives a reviewer the shortest repeatable path for reproducing the CLI-only sandbox/VM
static preflight evidence. It does not close `ERG-003`, and it does not approve live VM/container
inspection, VM/container lifecycle management, sandbox orchestration, Mission Control runtime
behavior, local model invocation, trusted-host promotion, network expansion, API/MCP profile
loading, new governed tools, production identity, runtime Postgres, hosted telemetry, remote MCP,
SIEM delivery, compliance automation, or public/security-product positioning.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Current `ERG-003` status before reviewer disposition: `external_review_required`.

## Review Goal

Determine whether the static preflight lane is coherent enough for local-preview planning evidence
and whether an external/source reviewer can later disposition `ERG-003` as
`closed_local_preview_static_preflight`.

This review goal is narrow. A favorable result would only say that the static fixture preflight
runner, profile contract, negative fixtures, source-review packet, and response-intake process are
coherent for the local-preview boundary. It would not approve live sandbox/VM runtime work.

## Reproduction Commands

Run from the Ithildin repository at the reviewed commit:

```sh
make sandbox-vm-static-profile-preflight-plan-check
make sandbox-vm-static-profile-fixture-contract-check
make sandbox-vm-static-profile-negative-fixtures-check
make sandbox-vm-static-preflight
make sandbox-vm-static-preflight-negative-transcripts
make sandbox-vm-static-preflight-implementation-gate
make sandbox-vm-static-preflight-source-review-packet
make sandbox-vm-static-preflight-source-review-packet-check
make sandbox-vm-static-preflight-external-review-bundle
make sandbox-vm-static-preflight-reviewed-packet-hash
make sandbox-vm-static-preflight-disposition-plan-check
make sandbox-vm-static-preflight-external-response-intake-check
make sandbox-vm-static-preflight-response-dry-run
make sandbox-vm-static-preflight-triage-update-check
make sandbox-vm-static-preflight-disposition-packet
make sandbox-vm-static-preflight-disposition-packet-check
make external-findings-intake-dry-run
make no-new-powers-guardrail
make tool-surface-invariant-gate
```

For a full same-commit handoff gate, run:

```sh
make review-run-manifest-refresh
make release-check
make review-candidate
```

## Evidence To Inspect

Review these committed docs:

- `docs/codex/sandbox-vm-worker-boundary-charter.md`
- `docs/codex/sandbox-vm-profile-contract.md`
- `docs/codex/sandbox-vm-preflight-contract.md`
- `docs/codex/sandbox-vm-static-profile-preflight-plan.md`
- `docs/codex/sandbox-vm-static-profile-fixture-contract.md`
- `docs/codex/sandbox-vm-static-profile-negative-fixtures.md`
- `docs/codex/sandbox-vm-static-preflight-implementation-decision.md`
- `docs/codex/sandbox-vm-static-preflight-source-review.md`
- `docs/codex/v3-sandbox-vm-static-preflight-internal-review.md`
- `docs/codex/findings/xh-sandbox-preflight-001-safe-label-suppression.md`
- `docs/codex/sandbox-vm-static-preflight-disposition-plan.md`
- `docs/codex/sandbox-vm-static-preflight-external-response-intake.md`
- `docs/codex/sandbox-vm-static-preflight-response-dry-run.md`
- `docs/codex/sandbox-vm-static-preflight-triage-update.md`
- `docs/codex/sandbox-vm-static-preflight-disposition-packet.md`
- `docs/codex/enterprise-readiness-gap-matrix.md`
- `docs/codex/post-rc-decision-register.md`

Review these generated artifacts:

- `var/review-packets/v3/sandbox-vm-static-preflight-source-review/`
- `var/review-packets/v3/sandbox-vm-static-preflight-disposition/`
- `var/review-packets/v3/sandbox-vm-static-preflight-negative/`
- `var/review-packets/v3/sandbox-vm-poc-review/`

## Expected Safe Outcomes

The reproduction path should show:

- static profile fixture checks pass;
- negative static profile cases are rejected with safe reason labels;
- the CLI-only preflight runner reports static metadata and safe labels only;
- the source-review packet and disposition packet are generated with artifact hashes;
- the reviewed-packet hash helper prints the exact hash to pass into response normalization;
- response intake normalization remains non-mutating;
- response dry-run evidence shows absent responses stay not-ready, source-level favorable responses
  can become closure-ready for later triage, and packet-only, bad-hash, critical/high-finding, and
  direct external-closure attempts are rejected;
- no new governed tool manifests are added;
- tool count remains `24`;
- live VM/container inspection remains blocked;
- local model invocation remains blocked;
- Mission Control runtime behavior remains blocked;
- trusted-host promotion remains blocked;
- network expansion remains blocked.

## Reviewer Disposition Boundary

A reviewer may recommend one of the allowed outcomes from
`sandbox-vm-static-preflight-disposition-plan.md`:

- `external_review_requested`
- `external_review_changes_requested`
- `closed_local_preview_static_preflight`
- `accepted_deferred`
- `blocked`

Only a later committed triage update may move `ERG-003` away from
`external_review_required`. This reproduction map is not that triage update.
Use `sandbox-vm-static-preflight-triage-update.md` as the safe committed update checklist after
real favorable source-level evidence is recorded.
Use `sandbox-vm-static-preflight-disposition-record-skeleton.md` as the companion disposition-record
shape for that future favorable static preflight update.

## What This Map Does Not Prove

This map does not prove external review has happened, does not close `ERG-003`, does not approve
live sandbox/VM runtime work, does not approve live VM/container inspection, does not approve
API/MCP profile loading, and does not authorize Mission Control, local models, sandbox
orchestration, network expansion, trusted-host promotion, SIEM delivery, production identity,
compliance automation, or public/security-product positioning.

## Validation

Run:

```sh
make sandbox-vm-static-preflight-reviewer-reproduction-map-check
make sandbox-vm-static-preflight-triage-update-check
```
