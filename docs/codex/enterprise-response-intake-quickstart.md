# Enterprise Response Intake Quickstart

Status: operator quickstart for applying `ERG-003` and `ERG-002` reviewer responses.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Run:

```sh
make enterprise-response-intake-quickstart
```

To regenerate the current ignored response inboxes and rerun the receive-side
status, rehearsal, quickstart, and paste-preflight checks in one operator
command, use:

```sh
make enterprise-response-intake-refresh
```

This quickstart begins after the current `ERG-003` and `ERG-002` packets have been sent and a real
reviewer response is available. It does not send packets, does not record external review, does not
normalize real responses, does not write response files, does not mutate findings, does not close
either lane, and does not approve runtime behavior.
Boundary shorthand: this quickstart does not normalize real responses.

If you copied and filled the ignored send receipt after sending the packets, validate it before
pasting responses:

```sh
make enterprise-review-send-receipt-validate RECEIPT=path/to/copied-receipt.json
```

The generated unsent template should validate but remain `ready_for_response_intake: false`. A
copied receipt filled after the human send step should report
`next_operator_action: wait_for_responses_then_run_enterprise_response_paste_preflight` before you
paste raw reviewer responses.

## Before Pasting A Response

Regenerate the current response inbox and status evidence:

```sh
make enterprise-dual-response-inbox
make enterprise-dual-response-readiness
make enterprise-response-waiting-room
make enterprise-response-now
make enterprise-response-status-board
make enterprise-response-command-matrix
make enterprise-response-application-protocol
make enterprise-response-application-rehearsal
make enterprise-response-paste-preflight
```

The equivalent one-command refresh path is:

```sh
make enterprise-response-intake-refresh
```

Use the generated cheat sheet for the exact normalization command, including reviewer metadata,
reviewed commit, reviewed packet hash, area, and output path:

```text
var/review-runs/enterprise-dual-response-inbox/ENTERPRISE_DUAL_RESPONSE_CHEATSHEET.md
```

Confirm the response belongs to the current packet and finding namespace:

| Lane | Expected packet | Raw response path | Finding namespace |
| --- | --- | --- | --- |
| `ERG-003` | `var/review-packets/v3/enterprise-dual-review-outbox/ERG-003/` | `var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-003.md` | `EXT-SVP-###` |
| `ERG-002` | `var/review-packets/v3/enterprise-dual-review-outbox/ERG-002/` | `var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-002.md` | `EXT-MC-DISPLAY-###` |

Do not paste reviewer content into committed docs. Raw reviewer responses belong only in ignored
`var/review-runs/` response paths until a lane-specific normalizer and closure gate prove that a
committed disposition is safe.

## ERG-003 Static Sandbox/VM Preflight

Save the raw response to:

```text
var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-003.md
```

Then run:

```sh
uv run python scripts/enterprise_response_paste_preflight.py \
  --lane ERG-003 \
  --raw-response var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-003.md
# Then run the exact `external_response_normalize.py` command from
# var/review-runs/enterprise-dual-response-inbox/ENTERPRISE_DUAL_RESPONSE_CHEATSHEET.md
# for --area sandbox-vm-static-preflight.
make sandbox-vm-static-preflight-response-dry-run
make sandbox-vm-static-preflight-disposition-closure-check
```

Allowed successful transition:

```text
ERG-003: external_review_required -> closed_local_preview_static_preflight
```

Even a favorable `ERG-003` response does not approve live VM/container inspection, local model
invocation, VM/container lifecycle management, sandbox orchestration, trusted-host promotion, SIEM
runtime adapters, compliance automation, public/security-product positioning, or new governed tool
powers.

## ERG-002 Mission Control Display/Import Planning

Save the raw response to:

```text
var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-002.md
```

Then run:

```sh
uv run python scripts/enterprise_response_paste_preflight.py \
  --lane ERG-002 \
  --raw-response var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-002.md
# Then run the exact `external_response_normalize.py` command from
# var/review-runs/enterprise-dual-response-inbox/ENTERPRISE_DUAL_RESPONSE_CHEATSHEET.md
# for --area mission-control-display.
make mission-control-display-response-dry-run
make mission-control-display-disposition-closure-check
```

Allowed successful transition:

```text
ERG-002: planning_only -> ready_for_design_only_decision_record
```

Even a favorable `ERG-002` response does not approve Mission Control runtime importer behavior,
Mission Control execution authority, Mission Control policy authority, Mission Control approval
authority, Mission Control audit authority, API callbacks, Ithildin polling, local model invocation,
sandbox orchestration, trusted-host promotion, SIEM runtime adapters, public/security-product
positioning, or new governed tool powers.

## After A Closure Gate Is Ready

If and only if a lane-specific closure gate reports ready and there are no critical/high findings,
use the lane-specific response application playbook or decision-record skeleton for a later committed
triage update:

- `docs/codex/sandbox-vm-static-preflight-response-application-playbook.md`
- `docs/codex/sandbox-vm-static-preflight-response-application-record.md`
- `docs/codex/mission-control-display-decision-record-skeleton.md`
- `docs/codex/mission-control-display-response-application-playbook.md`
- `docs/codex/mission-control-display-response-application-record.md`

After a committed disposition update, rerun:

```sh
make enterprise-current-checkpoint
make release-check
make review-candidate
```

## Stop Conditions

Stop and keep the lane in its current state if:

- the response references a different packet hash or artifact set;
- the normalizer rejects the response;
- the closure gate is not ready;
- any critical/high finding is present;
- the response asks for runtime behavior outside the lane scope;
- the response would imply production identity, runtime Postgres, hosted telemetry, remote MCP,
  sandbox orchestration, SIEM adapter runtime behavior, compliance automation,
  public/security-product positioning, or new governed tool powers.
