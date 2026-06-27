# Sandbox/VM Static Preflight Response Application Playbook

Status: manager-owned playbook for applying a real `ERG-003` external response.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Current `ERG-003` status before real reviewer disposition: `external_review_required`.

This playbook turns the static sandbox/VM preflight response kit into a step-by-step application
path. It is not a runtime feature and it does not close `ERG-003` by itself. It does not approve
runtime implementation, live VM/container inspection, VM/container lifecycle management, sandbox
orchestration, Mission Control runtime behavior, local model invocation, trusted-host promotion,
network expansion, API/MCP profile loading, new governed tool powers, production identity, runtime
Postgres, hosted telemetry, remote MCP, SIEM adapter behavior, compliance automation, shell/Docker/
Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem writes, plugin SDK behavior,
live POC planning, or public/security-product positioning.

The blocked boundary list includes `runtime Postgres` and the exact phrase
`shell/Docker/Kubernetes/browser governed powers`; those phrases are repeated here so release checks
can detect accidental boundary drift even if prose wraps differently above.

Validation command:

```sh
make sandbox-vm-static-preflight-response-application-playbook-check
```

## Inputs

Use this playbook only after a real reviewer response exists. The expected ignored input paths are:

```text
var/review-runs/sandbox-vm-static-preflight/RAW_RESPONSE_ERG-003.md
var/review-runs/sandbox-vm-static-preflight/normalized-response.json
```

The normalized response must use:

- response type: `ithildin.external_review.normalized_response`;
- reviewed area: `sandbox-vm-static-preflight`;
- finding namespace: `EXT-SVP-###`;
- reviewed packet hash source:
  `var/review-packets/v3/sandbox-vm-static-preflight-external-review/sandbox-vm-static-preflight-external-review-artifact-hashes.json`;
- source access: `source-level` or `packet-and-source`;
- `can_close_source_rows: true`;
- `mutates_findings: false`;
- `closes_external_review: false`;
- no critical/high findings.

## Run Sequence

Run these commands in order after saving the real response and before editing committed status docs:

```sh
make sandbox-vm-static-preflight-reviewed-packet-hash
make sandbox-vm-static-preflight-external-response-intake-check
make sandbox-vm-static-preflight-disposition-closure-check
make sandbox-vm-static-preflight-response-dry-run
make sandbox-vm-static-preflight-triage-update-check
make sandbox-vm-static-preflight-response-application-record-check
make sandbox-vm-static-preflight-response-application-playbook-check
```

If any command fails, stop and keep `ERG-003` at `external_review_required`.

## Allowed Committed Files

If and only if the closure gate reports `closure_ready: true`, a manager-owned triage commit may
touch only status/evidence files needed to record the external response:

- `docs/codex/source-review-closure-matrix.md`;
- `docs/codex/enterprise-readiness-gap-matrix.md`;
- `docs/codex/enterprise-external-review-queue.md`;
- `docs/codex/post-rc-decision-register.md`;
- `docs/codex/sandbox-vm-live-poc-preconditions-map.md`;
- `docs/codex/sandbox-vm-static-preflight-disposition-record-skeleton.md` or a future committed
  disposition record derived from it;
- `docs/codex/findings/ext-svp-*.md` for any `EXT-SVP-###` findings.

No runtime source, manifests, policy files, API/MCP behavior, approval/audit logic, UI runtime
behavior, Mission Control runtime behavior, sandbox/VM runtime behavior, local model invocation,
trusted-host promotion, SIEM/telemetry behavior, identity/storage behavior, or public positioning
docs may be changed as part of the response application unless a separate explicit sprint approves
that work.

## Allowed State Change

If and only if the normalized response validates, has no critical/high findings, and
`make sandbox-vm-static-preflight-disposition-closure-check` reports `closure_ready: true`, the
response application may support this future committed state change:

```text
ERG-003: external_review_required -> closed_local_preview_static_preflight
```

That state means only:

```text
The CLI-only static sandbox/VM profile preflight lane is externally/source reviewed for
local-preview fixture evidence.
```

It does not authorize `ERG-004`, live sandbox/VM worker implementation planning, live VM/container
inspection, VM/container lifecycle management, Mission Control runtime behavior, local model
invocation, trusted-host promotion, sandbox orchestration, SIEM adapter behavior, or any broader
Ithildin authority.

## Stop Conditions

Stop without applying a disposition if:

- the real response is absent, malformed, stale, or hash-mismatched;
- the reviewer inspected packet/docs only rather than source;
- `source_access` is not `source-level` or `packet-and-source`;
- `can_close_source_rows` is not `true`;
- `mutates_findings` is not `false`;
- `closes_external_review` is not `false`;
- any finding is critical/high;
- any finding uses the wrong area or namespace;
- the response approves live runtime work, Mission Control runtime behavior, local model invocation,
  trusted-host promotion, sandbox orchestration, network expansion, API/MCP profile loading, or
  public/security-product positioning;
- the closure gate reports `closure_ready: false`;
- the update would touch files outside the allowed committed files list.

## Final Evidence

After a favorable response is applied, preserve this evidence in the triage commit or handoff note:

- raw response transcript path;
- normalized response path;
- reviewed commit;
- reviewed packet path;
- reviewed packet SHA-256;
- reviewer label/type and source access;
- finding IDs, severities, dispositions, and verification notes;
- closure gate output;
- response dry-run output;
- response application record output;
- response application playbook output;
- release-check output;
- review-candidate packet path.

## Final Gates

After applying a real favorable response, run:

```sh
make review-run-manifest-refresh
make sandbox-vm-static-preflight-disposition-closure-check
make sandbox-vm-static-preflight-response-dry-run
make sandbox-vm-static-preflight-response-application-record-check
make sandbox-vm-static-preflight-response-application-playbook-check
make release-check
make review-candidate
```
