# Sandbox/VM Static Preflight Response Application Preflight

Status: checked preflight for applying a real `ERG-003` external response.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Current `ERG-003` status before real reviewer disposition: `external_review_required`.

Run:

```sh
make sandbox-vm-static-preflight-response-application-preflight-check
```

This preflight proves the ERG-003 response-application path is aligned before any real reviewer
response is applied. It does not normalize responses, does not write normalized response files, does
not mutate findings, does not record external review, does not close `ERG-003`, does not unblock
`ERG-004`, and does not approve runtime behavior.

## Path Contract

Use the all-lane enterprise response inbox for the raw reviewer transcript:

```text
var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-003.md
```

Normalize the real response only to the ERG-003 lane-local normalized-response path:

```text
var/review-runs/sandbox-vm-static-preflight/normalized-response.json
```

The normalization area and finding namespace must remain:

- reviewed area: `sandbox-vm-static-preflight`;
- finding namespace: `EXT-SVP-###`.

The operator command source is the checked [Enterprise Response Command Matrix](enterprise-response-command-matrix.md):

```sh
make enterprise-response-command-matrix
```

## Required Current State

Before applying a real response:

- `make enterprise-response-command-matrix` must report `ERG-003` with the raw response path above;
- `make sandbox-vm-static-preflight-disposition-closure-check` must report `closure_ready: false`
  while no real normalized response is present;
- `make sandbox-vm-static-preflight-response-dry-run` must prove favorable fixtures can become
  closure-ready and unfavorable fixtures fail closed;
- `make sandbox-vm-static-preflight-triage-update-check` must keep the committed triage path
  bounded;
- `make sandbox-vm-static-preflight-response-application-record-check` must keep the application
  record bounded;
- `make sandbox-vm-static-preflight-response-application-playbook-check` must keep the application
  command order and allowed file scope bounded.

## Apply Sequence After A Real Response Arrives

1. Run `make enterprise-response-inbox`.
2. Paste the real reviewer response into:

   ```text
   var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-003.md
   ```

3. Run the ERG-003 normalizer command from `ENTERPRISE_RESPONSE_INBOX.md` or
   [Enterprise Response Command Matrix](enterprise-response-command-matrix.md), using the exact
   reviewed packet hash from the generated inbox.
4. Run:

   ```sh
   make sandbox-vm-static-preflight-disposition-closure-check
   make sandbox-vm-static-preflight-response-dry-run
   make sandbox-vm-static-preflight-triage-update-check
   make sandbox-vm-static-preflight-response-application-record-check
   make sandbox-vm-static-preflight-response-application-playbook-check
   ```

5. If and only if the closure gate reports `closure_ready: true`, a later manager-owned triage
   commit may use the disposition skeleton to support this future transition:

   ```text
   ERG-003: external_review_required -> closed_local_preview_static_preflight
   ```

`closed_local_preview_static_preflight` means only that the CLI-only static sandbox/VM profile
preflight lane is externally/source reviewed for local-preview fixture evidence. ERG-004 remains
blocked until a separate live POC decision record exists.

Required invariant: ERG-004 remains blocked.

## Boundaries That Remain Blocked

- runtime implementation;
- live VM/container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- Mission Control runtime behavior;
- local model invocation;
- trusted-host promotion;
- network expansion;
- API/MCP profile loading;
- new governed tool powers;
- production identity;
- runtime Postgres;
- hosted telemetry;
- remote MCP;
- SIEM adapter behavior;
- compliance automation;
- public/security-product positioning.

## Validation

Run:

```sh
make sandbox-vm-static-preflight-response-application-preflight-check
make enterprise-response-command-matrix
make sandbox-vm-static-preflight-disposition-closure-check
make sandbox-vm-static-preflight-response-dry-run
make sandbox-vm-static-preflight-response-application-record-check
make sandbox-vm-static-preflight-response-application-playbook-check
```

`make release-check` includes this preflight so the ERG-003 raw-response path, normalized-response
path, command matrix, closure gate, dry-run, application record, application playbook, current
external-review-required state, and blocked runtime boundaries cannot quietly drift.
