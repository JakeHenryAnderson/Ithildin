# Mission Control Display Response Application Record

Status: process-only response-application record for `ERG-002`.

Current governed tool count: `24`.

Current `ERG-002` status before real reviewer disposition: `planning_only`.

Current selected capability: `not selected`.

This record defines the manager-owned checklist for applying a real external reviewer response to
the Mission Control display/import planning lane. It does not close `ERG-002` by itself. It does not
approve Mission Control runtime importer behavior, Mission Control execution authority, Mission
Control policy authority, Mission Control approval authority, Mission Control audit authority, API
callbacks, polling or mutating Ithildin APIs, local model invocation, sandbox orchestration,
trusted-host promotion, SIEM adapter behavior, new governed tool powers, production identity,
runtime Postgres, hosted telemetry, remote MCP, compliance automation, or public/security-product
positioning.

Use this record only after a real reviewer response has been saved under an ignored
`var/review-runs/` path and normalized at:

```text
var/review-runs/mission-control-display/normalized-response.json
```

Use `mission-control-display-response-application-playbook.md` as the companion command-order and
allowed-file-scope playbook for this record.

Use `mission-control-display-response-application-preflight.md` before applying a real response to
verify the all-lane enterprise response inbox path, lane-local normalized response path, command
matrix row, closure gate, dry-run, application record, playbook, and blocked Mission Control
runtime boundaries are still aligned.

## Application Preconditions

- The reviewed packet is the current `ERG-002` Mission Control display/import planning packet.
- The normalized response uses the `EXT-MC-DISPLAY-###` finding namespace.
- The reviewer access is `source-level`, `packet-and-source`, or the strongest access class recorded
  by the external response intake template.
- `can_close_source_rows` is `true`.
- `mutates_findings` is `false`.
- `closes_external_review` is `false`.
- No critical/high finding is open.
- The reviewed packet hash is a SHA-256 digest and matches the packet being dispositioned.
- `make mission-control-display-disposition-closure-check` reports `closure_ready: true`.
- `runtime importer behavior remains blocked`.

## Application Steps

1. Record the raw response transcript path.
2. Record the normalized response path.
3. Record the reviewer label, reviewer type, reviewed commit, reviewed packet path, reviewed packet
   SHA-256, source access, finding IDs, and finding severities.
4. Run:

   ```sh
   make mission-control-display-disposition-closure-check
   make mission-control-display-response-dry-run
   make mission-control-display-response-application-record-check
   make mission-control-display-response-application-playbook-check
   ```

5. If the closure gate is favorable, create a committed design-only decision record using
   `mission-control-display-decision-record-skeleton.md`.
6. Update only the allowed status/evidence documents named in the playbook.
7. Add or update reviewer finding files for every `EXT-MC-DISPLAY-###` finding.
8. Preserve every blocked runtime boundary.
9. Regenerate release and review evidence:

   ```sh
   make review-run-manifest-refresh
   make release-check
   make review-candidate
   ```

## Allowed Committed Outcome

If and only if all preconditions are met, this response-application process may support the following
future planning disposition:

```text
ERG-002: planning_only -> ready_for_design_only_decision_record
```

That state means only that Mission Control display/import planning evidence is favorable enough for a
future design-only decision record. It does not authorize Mission Control runtime importer behavior,
Mission Control execution authority, Mission Control policy authority, Mission Control approval
authority, Mission Control audit authority, API callbacks, polling or mutating Ithildin APIs, local
model invocation, sandbox orchestration, trusted-host promotion, SIEM adapter behavior, or any
additional Ithildin authority.

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
- Decision record path if a favorable response is applied.

## Fail-Closed Outcomes

Do not apply a disposition if:

- the normalized response is absent, malformed, stale, or hash-mismatched;
- source access is insufficient for the claim being made;
- any critical/high finding exists;
- any finding uses a namespace outside `EXT-MC-DISPLAY-###`;
- the reviewer approves or implies Mission Control runtime importer behavior;
- the closure gate reports `closure_ready: false`;
- the update would touch runtime surfaces, manifests, policy rules, API/MCP behavior, approval/audit
  logic, UI runtime behavior, Mission Control runtime behavior, sandbox/VM runtime behavior, local
  model invocation, trusted-host promotion, SIEM/telemetry, identity, storage, remote services, or
  public/security-product positioning.

## Boundaries That Must Remain Blocked

- Mission Control runtime importer behavior;
- Mission Control execution authority;
- Mission Control policy authority;
- Mission Control approval authority;
- Mission Control audit authority;
- API callbacks;
- polling or mutating Ithildin APIs;
- local model invocation;
- sandbox orchestration;
- trusted-host promotion;
- SIEM adapter behavior;
- new governed tool powers;
- production identity;
- runtime Postgres;
- hosted telemetry;
- remote MCP;
- compliance automation;
- public/security-product positioning.

## Validation

Run:

```sh
make mission-control-display-response-application-record-check
make mission-control-display-response-application-playbook-check
make mission-control-display-disposition-closure-check
make mission-control-display-response-dry-run
```
