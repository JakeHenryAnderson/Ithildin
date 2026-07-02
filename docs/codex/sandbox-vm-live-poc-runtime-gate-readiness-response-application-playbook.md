# Sandbox/VM Live POC Runtime Gate Readiness Response Application Playbook

Status: manager-owned playbook for applying a real `ERG-004` runtime gate-readiness response.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Current `ERG-004` status before real reviewer disposition:
`ready_for_runtime_implementation_gate_review`.

Run:

```sh
make sandbox-vm-live-poc-runtime-gate-readiness-response-application-playbook-check
```

This playbook defines the safe command order for a future real `EXT-LIVE-GATE-###` response. It is
process-only. It does not normalize responses, does not write normalized response files, does not
mutate findings, does not record external review, does not close `ERG-004`, does not approve
descriptor-only implementation planning by itself, and does not approve runtime implementation.
Run `sandbox-vm-live-poc-runtime-gate-readiness-response-application-preflight.md` before using this
playbook with a real response.

## Command Order

1. Refresh the current packet and inbox.

   ```sh
   make sandbox-vm-live-poc-runtime-gate-readiness-review-bundle
   make sandbox-vm-live-poc-runtime-gate-readiness-response-inbox
   make sandbox-vm-live-poc-runtime-gate-readiness-response-inbox-check
   ```

2. Paste the real reviewer response into:

   ```text
   var/review-runs/sandbox-vm-live-poc-runtime-gate-readiness-response-inbox/RAW_RESPONSE_ERG-004-RUNTIME-GATE-READINESS.md
   ```

3. Normalize with the command generated in the inbox cheat sheet. The output must be:

   ```text
   var/review-runs/sandbox-vm-live-poc-runtime-gate-readiness/normalized-response.json
   ```

4. Verify the response and gate path.

   ```sh
   make sandbox-vm-live-poc-runtime-gate-readiness-response-intake-check
   make sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run
   make sandbox-vm-live-poc-runtime-gate-readiness-response-application-preflight-check
   make sandbox-vm-live-poc-runtime-gate-readiness-response-application-record-check
   make sandbox-vm-live-poc-runtime-gate-readiness-response-application-playbook-check
   make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton-check
   ```

5. Commit a later decision record only if the normalized response proves:

   - `ithildin.external_review.normalized_response`;
   - `sandbox-vm-live-poc-runtime-gate-readiness`;
   - `EXT-LIVE-GATE-###`;
   - `source-level` or `packet-and-source`;
   - `can_close_source_rows: true`;
   - `mutates_findings: false`;
   - `closes_external_review: false`;
   - `approved_for_descriptor_only_runtime_implementation_planning`;
   - no critical/high findings are open.

## Allowed Future State

This playbook may support only this later committed transition:

```text
ERG-004: ready_for_runtime_implementation_gate_review -> ready_for_descriptor_only_runtime_implementation_planning
```

Allowed committed file scope for that future response application is limited to status/decision
evidence and finding records:

- `docs/codex/source-review-closure-matrix.md`
- `docs/codex/enterprise-readiness-gap-matrix.md`
- `docs/codex/enterprise-external-review-queue.md`
- `docs/codex/post-rc-decision-register.md`
- `docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton.md`
- `docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-response-application-record.md`
- `docs/codex/findings/ext-live-gate-*.md`

Any broader file scope requires a separate explicit sprint.

## Explicitly Blocked Scope

This playbook does not approve runtime implementation, live VM/container inspection, VM/container
lifecycle management, sandbox orchestration, Mission Control runtime behavior, local model
invocation, trusted-host promotion, host writes, network expansion, API/MCP profile loading, SIEM
adapter runtime behavior, production identity, runtime Postgres, hosted telemetry, remote MCP,
compliance automation, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad
filesystem writes, plugin SDK behavior, new governed tool powers, or public/security-product
positioning.

Blocked-boundary labels for release checks: live VM/container inspection, VM/container lifecycle management, Mission Control runtime behavior, local model invocation, API/MCP profile loading, hosted telemetry, public/security-product positioning.

## Validation

Run:

```sh
make sandbox-vm-live-poc-runtime-gate-readiness-response-application-playbook-check
make sandbox-vm-live-poc-runtime-gate-readiness-response-application-preflight-check
```
