# Mission Control Enterprise Status Reference Validator

Status: reference validator for Mission Control enterprise status display/import fixtures.

Run:

```sh
make mission-control-enterprise-status-reference-validator
```

The validator is a display-only validation oracle for the future Mission Control enterprise status
importer. It generates or reads the Mission Control enterprise status fixture pack, accepts the
single display-only fixture `MC-STATUS-VALID-001`, rejects `MC-STATUS-NEG-001` through
`MC-STATUS-NEG-010`, and checks that the observed safe reason labels match the fixture summary.

It does not call Mission Control, call Ithildin APIs, start services, invoke a model, create
approvals, write audit events, start a VM/container, inspect live VM state, orchestrate a sandbox,
promote artifacts to the trusted host, and does not approve Mission Control enterprise status
importer implementation.

This validator does not approve Mission Control enterprise status importer implementation.

## Purpose

The reference validator gives Mission Control-side work a compact local oracle:

- positive enterprise status payloads may be displayed as non-authoritative, display-only status;
- negative enterprise status payloads must be rejected or warning-only with stable reason labels;
- Mission Control must not infer execution, policy, approval, audit, lane closure, sandbox, VM,
  SIEM, compliance, host-promotion, or capability-expansion authority from imported status
  evidence.

The validator intentionally mirrors the existing Ithildin enterprise status fixture rules rather
than implementing a Mission Control runtime importer. Mission Control may use the same fixture pack
and expected reason labels in its own tests, but runtime importer behavior remains blocked until a
separate Mission-Control-side implementation plan and source-review lane approve it.

## CLI Forms

Validate a temporary fixture pack:

```sh
make mission-control-enterprise-status-reference-validator
```

Validate an existing generated fixture directory:

```sh
uv run python scripts/mission_control_enterprise_status_reference_validator.py \
  --fixture-dir var/review-packets/v3/mission-control-enterprise-status-fixtures
```

Emit machine-readable evidence:

```sh
uv run python scripts/mission_control_enterprise_status_reference_validator.py --json
```

## Boundary

This check is reference evidence only. It does not approve Mission Control runtime importer
behavior, callbacks into Ithildin, polling or mutating Ithildin APIs, bidirectional API
integration, policy authority transfer, approval authority transfer, audit authority transfer,
local model invocation, live VM/container inspection, sandbox orchestration, trusted-host
promotion, SIEM adapters, compliance automation, public/security-product positioning, or new
governed tool powers.
