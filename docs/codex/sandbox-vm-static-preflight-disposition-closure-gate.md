# Sandbox/VM Static Preflight Disposition Closure Gate

Status: fail-closed closure gate for `ERG-003`.

This gate defines the minimum evidence required before `ERG-003` can move from
`external_review_required` to `closed_local_preview_static_preflight`. It does not close `ERG-003`
by itself. It does not approve live VM/container inspection, VM/container lifecycle management,
sandbox orchestration, Mission Control runtime behavior, local model invocation, trusted-host
promotion, network expansion, API/MCP profile loading, new governed tools, production identity,
runtime Postgres, hosted telemetry, remote MCP, SIEM adapters, compliance automation, or
public/security-product positioning.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Validate this gate with:

```sh
make sandbox-vm-static-preflight-disposition-closure-check
```

## Required Evidence

Before a later committed triage update may change `ERG-003`, the following evidence must exist:

- normalized response path:
  `var/review-runs/sandbox-vm-static-preflight/normalized-response.json`;
- response type: `ithildin.external_review.normalized_response`;
- reviewed area: `sandbox-vm-static-preflight`;
- reviewer source access: `source-level` or `packet-and-source`;
- reviewed packet hash: `sha256:<64 lowercase hex chars>`;
- reviewed packet hash source:
  `var/review-packets/v3/sandbox-vm-static-preflight-external-review/sandbox-vm-static-preflight-external-review-artifact-hashes.json`;
- finding namespace: `EXT-SVP-###`;
- `can_close_source_rows: true`;
- `mutates_findings: false`;
- `closes_external_review: false`;
- no critical/high findings;
- every finding row, if present, uses area `sandbox-vm-static-preflight`;
- the disposition plan and intake template remain linked from release/readiness docs.

If the normalized response is absent, the gate must pass as a readiness check but report
`closure_ready: false`. Absence of a response means the lane remains `external_review_required`.
If a normalized response is present, `reviewed_packet_hash` must exactly match the SHA-256 digest
of the current ERG-003 external-review artifact-hash manifest.

## Allowed Closure Result

The only closure result this gate can support is:

```text
closed_local_preview_static_preflight
```

That result means only:

```text
The CLI-only static sandbox/VM profile preflight lane is externally reviewed for local-preview
fixture evidence.
```

It still does not approve:

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

## Follow-Up Update Requirements

If this gate reports `closure_ready: true`, a separate committed triage update must still:

1. record the raw response transcript path and normalized response path;
2. record the reviewer label, source access, reviewed commit, and packet hash;
3. add or update reviewer finding files for every finding in the normalized response;
4. update `source-review-closure-matrix.md` and `enterprise-readiness-gap-matrix.md`;
5. update `post-rc-decision-register.md` without approving live runtime work;
6. follow `sandbox-vm-static-preflight-triage-update.md` for the safe committed update path;
7. follow `sandbox-vm-static-preflight-response-application-record.md` as the manager-owned
   response-application checklist;
8. use `sandbox-vm-static-preflight-disposition-record-skeleton.md` as the disposition-record
   shape for a favorable source-reviewed static preflight disposition;
9. rerun `make release-check` and `make review-candidate`.

## Validation

Run:

```sh
make sandbox-vm-static-preflight-disposition-closure-check
make sandbox-vm-static-preflight-disposition-plan-check
make sandbox-vm-static-preflight-external-response-intake-check
make sandbox-vm-static-preflight-triage-update-check
make sandbox-vm-static-preflight-response-application-record-check
make enterprise-external-review-queue-check
```
