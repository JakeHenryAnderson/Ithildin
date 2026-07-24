# LV1-002 Fresh Recovery Disposition

Status: `STOP — single authorized recovery retry failed closed`

- Local-v1 milestone: `LV1-002`
- Release outcome: `O3`
- Exact attempted candidate: `7f7b5fde932fd678afd465924e7dcbe936fbcfb2`
- Milestone status: `in_progress`
- Outcome status: `not_started`
- Runtime authority: `false`
- Release, promotion, production identity/storage, and UAT authority: `false`
- Additional live retry in this recovery task: `not_authorized`

This record closes only the fresh bounded recovery task authorized after the repeated live-gate
disposition. It does not complete authenticated Node onboarding, qualify a Local-v1 candidate, or
authorize another live attempt.

## Reviewed Recovery Candidate

The recovery added one exact, read-only, project-scoped Compose status query for only
`ithildin-api` and `ithildin-ui`. It records closed service lifecycle and probe classifications
without recording raw Docker output, HTTP material, environment, logs, container-inspect data, host
metadata, credentials, or arbitrary service input.

The first exact candidate, `7214568251d6a821922a4be36dab971059fb87ce`, received an independent
Sol xhigh `NO-GO` with zero Critical, zero High, two Medium, and zero Low findings. The Medium
findings covered delayed trust-invariant failures and rejection of a legitimate
restarting/nonzero-exit classification.

The repaired exact candidate, `7f7b5fde932fd678afd465924e7dcbe936fbcfb2`, received independent
Sol xhigh `GO` with zero Critical, High, Medium, or Low findings. Before the live action, its focused
journey tests, Ruff, strict mypy, compile checks, and the Local-v1 runtime trust slice passed. The
review authorized exactly one local-only retry under the existing isolation, cleanup, and
no-further-blind-retry stop lines.

## Single Live Retry

The exact command `make local-v1-node-journey` ran once against the clean repaired candidate. It
failed closed with `compose_stack_health_timeout` before workspace selection, enrollment-code
issuance, Node enrollment, configuration assignment, synchronization, or revocation.

The retained closed diagnostic records:

- API container: `service_running_healthy`
- UI container: `service_running_without_healthcheck`
- unauthenticated API health probe: `probe_ready`
- authenticated API system-status probe: `probe_invalid`
- UI shell probe: `probe_ready`
- bounded reason: `stack_authenticated_system_status_not_ready`
- diagnostic collection: `compose_stack_diagnostic_collected`

This narrows the failed readiness condition to the authenticated system-status response path. It
does not reveal or authorize collection of the raw response, a container log, environment data, or
an inspect payload.

## Retained Safe Evidence

- Run: `20260724T152305Z-a71011e2`
- JSON:
  `var/local-v1-node-journey/20260724T152305Z-a71011e2/local-v1-node-journey.json`
- JSON SHA-256: `5c8a2d1e39e31196954f1c7da808abc3bf4d6e197e30bc280ed71156505db3d5`
- Markdown:
  `var/local-v1-node-journey/20260724T152305Z-a71011e2/local-v1-node-journey.md`
- Markdown SHA-256: `ccfd1a4fd0d804e632a98c074032109d7663fccd5e2ab7091bff11d21302dd44`
- File modes: owner read/write only (`0600`)

The report is ignored runtime evidence, not successful journey evidence. The success-only checker
must reject it.

## Cleanup And Authority

The report records:

- `compose_down_succeeded: true`
- `volumes_removed: true`
- `images_removed: true`
- `resources_absent: true`
- `runtime_state_removed: true`
- `runtime_state_retained: false`
- `recovery_required: false`

The ignored runtime directory is empty after the attempt. The report records all runtime, release,
promotion, production identity/storage, and UAT authority fields as false. No Node identity was
created and no ambiguous-enrollment recovery or revocation is required.

## Source-Aligned Explanation, Not Live Proof

Static source inspection provides a bounded explanation for the closed `probe_invalid` result:

- the production `/system/status` response contains a safe posture object under
  `security.admin_token`; and
- the journey HTTP client currently applies its generic recursive secret-shaped-field rejection to
  the entire system-status document before using the small set of readiness fields.

That generic rejection intentionally treats an `admin_token` key as unsafe on ordinary responses.
The production status field contains posture rather than the token value, but the current journey
client does not project the status response before applying the generic rule. This is a
source-aligned explanation, not an observation of the raw live response, which was neither
requested nor recorded.

## Next Recovery Boundary

No additional live retry is authorized in this recovery task. A new explicitly resumed,
exact-reviewed recovery should:

1. add a system-status-specific closed projection containing only `status`, `tool_count`,
   `runtime_candidate.posture`, `storage.runtime_backend`, and `storage.postgres.configured`;
2. preserve the generic recursive secret-field rejection for every other response and avoid a
   broad `admin_token` exception;
3. test the projection against a production-shaped status fixture containing the safe
   `security.admin_token` posture field and hostile secret-bearing variants;
4. prove that no unprojected field or raw HTTP material reaches JSON, Markdown, CLI output, or
   exceptions;
5. run focused and Local-v1 runtime-trust checks, freeze an exact candidate, and obtain independent
   high-effort review; and
6. authorize at most one further live retry only after that exact review returns GO.

`LV1-002` remains `in_progress`, `O3` remains `not_started`, the fixed 24-tool surface is unchanged,
and no arbitrary host-control, production, release, promotion, or UAT authority is granted.
