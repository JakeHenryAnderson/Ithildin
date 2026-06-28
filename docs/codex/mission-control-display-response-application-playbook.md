# Mission Control Display Response Application Playbook

Status: manager-owned playbook for applying a real `ERG-002` external response.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Current `ERG-002` status before real reviewer disposition: `planning_only`.

This playbook turns the Mission Control display/import response kit into a step-by-step application
path. It is not a runtime feature and it does not close `ERG-002` by itself. It does not approve
Mission Control runtime importer behavior, Mission Control execution authority, Mission Control
policy authority, Mission Control approval authority, Mission Control audit authority, API
callbacks, polling or mutating Ithildin APIs, local model invocation, sandbox orchestration,
trusted-host promotion, SIEM adapter behavior, new governed tool powers, production identity,
runtime Postgres, hosted telemetry, remote MCP, compliance automation, or public/security-product
positioning.

Validation command:

```sh
make mission-control-display-response-application-playbook-check
```

Run `make mission-control-display-response-application-preflight-check` before applying a real
reviewer response. The companion `mission-control-display-response-application-preflight.md` checks
the all-lane raw response inbox path, ERG-002 normalized response path, command matrix row, closure
gate, dry-run, application record, playbook, and blocked runtime boundaries without normalizing
responses or closing `ERG-002`.

## Inputs

Use this playbook only after a real reviewer response exists. The expected ignored input paths are:

```text
var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-002.md
var/review-runs/mission-control-display/normalized-response.json
```

The normalized response must use:

- response type: `ithildin.external_review.normalized_response`;
- reviewed area: `mission-control-display`;
- finding namespace: `EXT-MC-DISPLAY-###`;
- reviewed packet hash source:
  `var/review-packets/v3/mission-control-display-external-review/mission-control-display-external-review-artifact-hashes.json`;
- `can_close_source_rows: true`;
- `mutates_findings: false`;
- `closes_external_review: false`;
- no critical/high findings.

## Run Sequence

Run these commands in order after saving the real response and before editing committed status docs:

```sh
make mission-control-display-external-response-intake-check
make mission-control-display-disposition-closure-check
make mission-control-display-response-dry-run
make mission-control-display-response-application-record-check
make mission-control-display-response-application-playbook-check
```

If any command fails, stop and keep `ERG-002` at `planning_only`.

## Allowed Committed Files

If and only if the closure gate reports `closure_ready: true`, a manager-owned triage commit may
touch only status/evidence files needed to record the external response and prepare a design-only
decision record:

- `docs/codex/mission-control-display-decision-record-skeleton.md`;
- `docs/codex/enterprise-readiness-gap-matrix.md`;
- `docs/codex/enterprise-external-review-queue.md`;
- `docs/codex/post-rc-decision-register.md`;
- `docs/codex/mission-control-side-handoff-plan.md`;
- `docs/codex/mission-control-integration-implementation-ticket.md`;
- `docs/codex/findings/ext-mc-display-*.md` for any `EXT-MC-DISPLAY-###` findings.

No runtime source, manifests, policy files, API/MCP behavior, approval/audit logic, UI runtime
behavior, Mission Control runtime behavior, sandbox/VM runtime behavior, local model invocation,
trusted-host promotion, SIEM/telemetry behavior, identity/storage behavior, or public positioning
docs may be changed as part of the response application unless a separate explicit sprint approves
that work.

## Allowed State Change

If and only if the normalized response validates, has no critical/high findings, and
`make mission-control-display-disposition-closure-check` reports `closure_ready: true`, the response
application may support this future committed planning state change:

```text
ERG-002: planning_only -> ready_for_design_only_decision_record
```

That state means only:

```text
Mission Control display/import planning may proceed to a design-only decision record while
runtime importer behavior remains blocked.
```

It does not authorize Mission Control runtime importer behavior, Mission Control execution
authority, Mission Control policy authority, Mission Control approval authority, Mission Control
audit authority, API callbacks, polling or mutating Ithildin APIs, local model invocation, sandbox
orchestration, trusted-host promotion, SIEM adapter behavior, or any broader Ithildin authority.

## Stop Conditions

Stop without applying a disposition if:

- the real response is absent, malformed, stale, or hash-mismatched;
- `can_close_source_rows` is not `true`;
- `mutates_findings` is not `false`;
- `closes_external_review` is not `false`;
- any finding is critical/high;
- any finding uses the wrong area or namespace;
- the response approves Mission Control runtime importer behavior, execution authority, policy
  authority, approval authority, audit authority, API callbacks, polling or mutating Ithildin APIs,
  local model invocation, sandbox orchestration, trusted-host promotion, SIEM adapter behavior, or
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
make mission-control-display-disposition-closure-check
make mission-control-display-response-dry-run
make mission-control-display-response-application-record-check
make mission-control-display-response-application-playbook-check
make release-check
make review-candidate
```
