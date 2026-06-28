# Mission Control Display Response Application Preflight

Status: checked preflight for applying a real `ERG-002` external response.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Current `ERG-002` status before real reviewer disposition: `planning_only`.

Run:

```sh
make mission-control-display-response-application-preflight-check
```

This preflight proves the ERG-002 response-application path is aligned before any real reviewer
response is used to support a design-only decision record. It does not normalize responses, does
not write normalized response files, does not mutate findings, does not record external review,
does not close `ERG-002`, and does not approve runtime behavior. Mission Control runtime importer
behavior remains blocked.

Required invariant: does not write normalized response files.

## Path Contract

Use the all-lane enterprise response inbox for the raw reviewer transcript:

```text
var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-002.md
```

Normalize the real response only to the ERG-002 lane-local normalized-response path:

```text
var/review-runs/mission-control-display/normalized-response.json
```

The normalization area and finding namespace must remain:

- reviewed area: `mission-control-display`;
- finding namespace: `EXT-MC-DISPLAY-###`.

The operator command source is the checked [Enterprise Response Command Matrix](enterprise-response-command-matrix.md):

```sh
make enterprise-response-command-matrix
```

## Required Current State

Before applying a real response:

- `make enterprise-response-command-matrix` must report `ERG-002` with the raw response path above;
- `make mission-control-display-disposition-closure-check` must report `closure_ready: false`
  while no real normalized response is present;
- `make mission-control-display-response-dry-run` must prove favorable fixtures can become
  closure-ready and unfavorable fixtures fail closed;
- `make mission-control-display-response-kit-check` must keep the response-intake kit bounded;
- `make mission-control-display-external-response-intake-check` must keep the intake template
  bounded;
- `make mission-control-display-decision-record-skeleton-check` must keep the only allowed future
  decision outcome bounded to `approved_for_planning`.

## Apply Sequence After A Real Response Arrives

1. Run `make enterprise-response-inbox`.
2. Paste the real reviewer response into:

   ```text
   var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-002.md
   ```

3. Run the ERG-002 normalizer command from `ENTERPRISE_RESPONSE_INBOX.md` or
   [Enterprise Response Command Matrix](enterprise-response-command-matrix.md), using the exact
   reviewed packet hash from the generated inbox.
4. Run:

   ```sh
   make mission-control-display-disposition-closure-check
   make mission-control-display-response-dry-run
   make mission-control-display-response-kit-check
   make mission-control-display-decision-record-skeleton-check
   ```

5. If and only if the closure gate reports `closure_ready: true`, a later manager-owned decision
   record may use [Mission Control Display Decision Record Skeleton](mission-control-display-decision-record-skeleton.md)
   to support this future transition:

   ```text
   ERG-002: planning_only -> ready_for_design_only_decision_record
   ```

`ready_for_design_only_decision_record` means only that Mission Control-side display/importer
design planning may continue. Runtime importer behavior remains blocked.

Required invariant: runtime importer behavior remains blocked.

## Boundaries That Remain Blocked

- runtime implementation;
- Mission Control runtime importer behavior;
- Mission Control execution authority;
- Mission Control policy authority;
- Mission Control approval authority;
- Mission Control audit authority;
- API callbacks;
- polling or mutating Ithildin APIs;
- local model invocation;
- VM/container lifecycle management;
- sandbox orchestration;
- trusted-host promotion;
- SIEM adapter behavior;
- production identity;
- runtime Postgres;
- hosted telemetry;
- remote delivery;
- new governed tool powers;
- public/security-product positioning.

## Validation

Run:

```sh
make mission-control-display-response-application-preflight-check
make enterprise-response-command-matrix
make mission-control-display-disposition-closure-check
make mission-control-display-response-dry-run
make mission-control-display-response-kit-check
make mission-control-display-decision-record-skeleton-check
```

`make release-check` includes this preflight so the ERG-002 raw-response path, normalized-response
path, command matrix, closure gate, dry-run, response kit, decision-record skeleton, current
planning-only state, and blocked runtime boundaries cannot quietly drift.
