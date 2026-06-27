# Sandbox/VM Static Preflight Triage Update

Status: triage-update checklist for `ERG-003` after favorable external evidence.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Current `ERG-003` status before real reviewer disposition: `external_review_required`.

Validation command:

```sh
make sandbox-vm-static-preflight-triage-update-check
```

This checklist defines the safe committed update path after a real external/source reviewer response
has been normalized at:

```text
var/review-runs/sandbox-vm-static-preflight/normalized-response.json
```

It does not close `ERG-003` by itself. It does not approve runtime implementation, live
VM/container inspection, VM/container lifecycle management, sandbox orchestration, Mission Control
runtime behavior, local model invocation, trusted-host promotion, network expansion, API/MCP
profile loading, new governed tool powers, production identity, runtime Postgres, hosted telemetry,
remote MCP, SIEM delivery, compliance automation, or public/security-product positioning.

## Required Triage Steps

1. Save the raw reviewer response transcript under an ignored `var/review-runs/` path.
2. Normalize the response with `sandbox-vm-static-preflight-external-response-intake.md`.
3. Run the closure gate:

   ```sh
   make sandbox-vm-static-preflight-disposition-closure-check
   ```

4. Confirm `closure_ready: true` and allowed closure state
   `closed_local_preview_static_preflight`.
5. Add or update reviewer finding files for every `EXT-SVP-###` finding in the normalized response.
6. Update status documents:
   - `source-review-closure-matrix.md`;
   - `enterprise-readiness-gap-matrix.md`;
   - `post-rc-decision-register.md`;
   - `enterprise-external-review-queue.md`;
   - `sandbox-vm-live-poc-preconditions-map.md`.
7. Preserve blocked runtime boundaries.
8. Regenerate evidence:

   ```sh
   make review-run-manifest-refresh
   make release-check
   make review-candidate
   ```

## Required Evidence To Record

The committed triage update must cite:

- reviewer label and reviewer type;
- raw response transcript path;
- normalized response path;
- reviewed commit;
- reviewed packet path;
- reviewed packet SHA-256;
- source access;
- finding IDs and severities;
- closure gate command output;
- release-check command output;
- review-candidate packet path.

## Allowed Status Change

If and only if the normalized response validates, has no critical/high findings, and the closure
gate reports `closure_ready: true`, a committed triage update may change `ERG-003` from
`external_review_required` to:

```text
closed_local_preview_static_preflight
```

That status means only:

```text
The CLI-only static sandbox/VM profile preflight lane is externally reviewed for local-preview
fixture evidence.
```

## Boundaries That Must Remain Blocked

The triage update must keep these blocked:

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
- SIEM delivery;
- compliance automation;
- public/security-product positioning.

`ERG-004 remains blocked` after this triage update. A favorable `ERG-003` disposition may satisfy
one prerequisite for a later live POC decision record, but it does not approve live POC
implementation planning and does not authorize local model or VM/container runtime work.
Use `sandbox-vm-static-preflight-disposition-record-skeleton.md` as the committed disposition-record
shape if favorable source-level static preflight evidence is ever recorded.
Use `sandbox-vm-static-preflight-response-application-playbook.md` as the manager-owned command and
file-scope playbook before committing that favorable response.
Use `sandbox-vm-static-preflight-response-application-record.md` as the manager-owned checklist for
applying that real reviewer response without accidentally closing `ERG-003` or unblocking `ERG-004`.

## Negative Triage Outcomes

Do not move `ERG-003` if:

- the normalized response is absent or malformed;
- source access is packet-only or docs-only;
- reviewed packet hash is not a SHA-256 digest;
- `can_close_source_rows` is not `true`;
- `mutates_findings` is not `false`;
- `closes_external_review` is not `false`;
- any critical/high finding is present;
- any finding uses the wrong area or namespace;
- the reviewer approves live runtime work rather than local-preview static preflight closure only.

Use `make sandbox-vm-static-preflight-response-dry-run` to confirm the gate rejects unfavorable
fixture shapes before applying a real triage update.

## Validation

Run:

```sh
make sandbox-vm-static-preflight-triage-update-check
make sandbox-vm-static-preflight-response-application-record-check
make sandbox-vm-static-preflight-response-application-playbook-check
make sandbox-vm-static-preflight-disposition-closure-check
make sandbox-vm-static-preflight-response-dry-run
make enterprise-external-review-queue-check
```
