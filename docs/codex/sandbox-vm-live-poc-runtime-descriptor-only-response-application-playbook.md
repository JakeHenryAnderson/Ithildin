# Sandbox/VM Live POC Runtime Descriptor-Only Response Application Playbook

Status: manager-owned playbook for applying a real `ERG-004` descriptor-only response.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Current `ERG-004` descriptor-only status before real reviewer disposition:
`descriptor_only_runtime_implemented_source_review_pending`.

Run:

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-response-application-playbook-check
```

This playbook defines the safe command order for a future real `EXT-LIVE-DESC-###` response. It is
process-only. It does not normalize responses, does not write normalized response files, does not
mutate findings, does not record external review, does not close `ERG-004`, does not approve
descriptor-only source disposition by itself, and does not approve runtime implementation. Run
`sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight.md` before using this
playbook with a real response.

## Command Order

1. Refresh the current packet.

   ```sh
   make sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle
   make sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle-check
   ```

2. Save and normalize the real reviewer response using the intake command from:

   ```text
   docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake.md
   ```

   The output must be:

   ```text
   var/review-runs/sandbox-vm-live-poc-runtime-descriptor-only/normalized-response.json
   ```

3. Verify the response and gate path.

   ```sh
   make sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake-check
   make sandbox-vm-live-poc-runtime-descriptor-only-response-inbox-check
   make sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run
   make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check
   make sandbox-vm-live-poc-runtime-descriptor-only-response-application-record-check
   make sandbox-vm-live-poc-runtime-descriptor-only-response-application-playbook-check
   ```

4. Commit a later descriptor-only disposition update only if the normalized response proves:

   - `ithildin.external_review.normalized_response`;
   - `sandbox-vm-live-poc-runtime-descriptor-only`;
   - `EXT-LIVE-DESC-###`;
   - `source-level` or `packet-and-source`;
   - reviewer type is `human`, `gpt-5.5-pro`, `external-ai`, `codex-high`, or `codex-xhigh`;
   - `can_close_source_rows: true`;
   - `mutates_findings: false`;
   - `closes_external_review: false`;
   - `approve_descriptor_only_local_preview_disposition`;
   - no critical/high findings are open.

## Allowed Future State

This playbook may support only this later committed transition:

```text
ERG-004 descriptor-only: source_review_pending -> descriptor_only_local_preview_disposition_ready
```

If the reviewer is `codex-high` or `codex-xhigh`, that transition is an internal proxy disposition
for continued local-development progress only; it is not external review closure and does not
support public/security-product positioning, broader runtime claims, or enterprise deployment
claims.

Allowed committed file scope for that future response application is limited to status/decision
evidence and finding records:

- `docs/codex/source-review-closure-matrix.md`
- `docs/codex/enterprise-readiness-gap-matrix.md`
- `docs/codex/enterprise-external-review-queue.md`
- `docs/codex/post-rc-decision-register.md`
- `docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-response-application-record.md`
- `docs/codex/findings/ext-live-desc-*.md`

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
make sandbox-vm-live-poc-runtime-descriptor-only-response-application-playbook-check
make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check
```
