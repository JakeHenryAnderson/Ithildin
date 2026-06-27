# Sandbox/VM Static Preflight Response Application Record

Status: process-only response-application record for `ERG-003`.

Current governed tool count: `24`.

Current `ERG-003` status before real reviewer disposition: `external_review_required`.

Current selected capability: `not selected`.

This record defines the manager-owned checklist for applying a real external/source reviewer
response to the sandbox/VM static preflight lane. It does not close `ERG-003` by itself. It does
not approve runtime implementation, live VM/container inspection, VM/container lifecycle
management, sandbox orchestration, Mission Control runtime behavior, local model invocation,
trusted-host promotion, network expansion, API/MCP profile loading, new governed tool powers,
production identity, runtime Postgres, hosted telemetry, remote MCP, SIEM adapter behavior,
compliance automation, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad
filesystem writes, plugin SDK behavior, live POC planning, or public/security-product positioning.

Use this record only after a real reviewer response has been saved under an ignored
`var/review-runs/` path and normalized at:

```text
var/review-runs/sandbox-vm-static-preflight/normalized-response.json
```

Use `sandbox-vm-static-preflight-response-application-playbook.md` as the companion command-order
and allowed-file-scope playbook for this record.

## Application Preconditions

- The reviewed packet is the current `ERG-003` static preflight packet.
- The normalized response uses the `EXT-SVP-###` finding namespace.
- The reviewer access is `source-level` or `packet-and-source`.
- `can_close_source_rows` is `true`.
- `mutates_findings` is `false`.
- `closes_external_review` is `false`.
- No critical/high finding is open.
- The reviewed packet hash is a SHA-256 digest and matches the packet being dispositioned.
- `make sandbox-vm-static-preflight-disposition-closure-check` reports `closure_ready: true`.
- `ERG-004 remains blocked`.

## Application Steps

1. Record the raw response transcript path.
2. Record the normalized response path.
3. Record the reviewer label, reviewer type, reviewed commit, reviewed packet path, reviewed
   packet SHA-256, source access, finding IDs, and finding severities.
4. Run:

   ```sh
   make sandbox-vm-static-preflight-disposition-closure-check
   make sandbox-vm-static-preflight-response-dry-run
   make sandbox-vm-static-preflight-triage-update-check
   make sandbox-vm-static-preflight-response-application-record-check
   make sandbox-vm-static-preflight-response-application-playbook-check
   ```

5. If the closure gate is favorable, create a committed disposition record using
   `sandbox-vm-static-preflight-disposition-record-skeleton.md`.
6. Update only the allowed status/evidence documents:
   - `source-review-closure-matrix.md`;
   - `enterprise-readiness-gap-matrix.md`;
   - `post-rc-decision-register.md`;
   - `enterprise-external-review-queue.md`;
   - `sandbox-vm-live-poc-preconditions-map.md`.
7. Add or update reviewer finding files for every `EXT-SVP-###` finding.
8. Preserve every blocked runtime boundary.
9. Regenerate release and review evidence:

   ```sh
   make review-run-manifest-refresh
   make release-check
   make review-candidate
   ```

## Allowed Committed Outcome

If and only if all preconditions are met, this response-application process may support the
following future disposition:

```text
ERG-003: external_review_required -> closed_local_preview_static_preflight
```

That status means only that the CLI-only static sandbox/VM profile preflight lane is
externally/source reviewed for local-preview fixture evidence. It does not authorize live POC
planning, live runtime behavior, Mission Control runtime behavior, local model invocation, trusted
host promotion, sandbox orchestration, SIEM adapter behavior, or any additional Ithildin authority.

## Required Evidence To Preserve

- Raw reviewer response transcript path.
- Normalized response path.
- Reviewed commit.
- Reviewed packet path.
- Reviewed packet SHA-256.
- Reviewer label/type and source access.
- Finding IDs, severities, and dispositions.
- Closure gate output.
- Response dry-run output.
- Release-check output.
- Review-candidate packet path.
- Disposition record path if a favorable response is applied.

## Fail-Closed Outcomes

Do not apply a disposition if:

- the normalized response is absent, malformed, stale, or hash-mismatched;
- source access is packet-only or docs-only;
- any critical/high finding exists;
- any finding uses a namespace outside `EXT-SVP-###`;
- the reviewer approves or implies live runtime behavior;
- the closure gate reports `closure_ready: false`;
- the update would touch runtime surfaces, manifests, policy rules, API/MCP behavior, approval/audit
  logic, UI runtime behavior, Mission Control runtime behavior, sandbox/VM runtime behavior, local
  model invocation, trusted-host promotion, SIEM/telemetry, identity, storage, remote services, or
  public/security-product positioning.

## Boundaries That Must Remain Blocked

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
make sandbox-vm-static-preflight-response-application-record-check
make sandbox-vm-static-preflight-response-application-playbook-check
make sandbox-vm-static-preflight-disposition-closure-check
make sandbox-vm-static-preflight-response-dry-run
make sandbox-vm-static-preflight-triage-update-check
```
