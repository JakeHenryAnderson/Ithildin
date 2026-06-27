# Mission Control Handoff Reference Validator

Status: reference validator for Mission Control handoff display/import fixtures.

Run:

```sh
make mission-control-handoff-reference-validator
```

The validator is a display-only validation oracle for the future Mission Control importer. It
generates or reads the Mission Control handoff fixture pack, accepts the single metadata-only
fixture `MC-HANDOFF-VALID-001`, rejects `MC-HANDOFF-NEG-001` through `MC-HANDOFF-NEG-014`, and
checks that the observed safe reason labels match the fixture summary.

It does not call Mission Control, call Ithildin APIs, start services, invoke a model, create
approvals, write audit events, start a VM/container, orchestrate a sandbox, promote artifacts to the
trusted host, and does not approve Mission Control runtime importer behavior.

## Purpose

The reference validator gives Mission Control-side work a compact local oracle:

- positive handoff payloads may be displayed as metadata-only evidence;
- negative handoff payloads must be rejected or warning-only with stable reason labels;
- Mission Control must not infer execution, policy, approval, audit, sandbox, VM, or host-promotion
  authority from imported evidence.

The validator intentionally mirrors the existing Ithildin fixture rules rather than implementing a
Mission Control runtime importer. Mission Control may use the same fixture pack and expected reason
labels in its own tests, but runtime importer behavior remains blocked until a separate
Mission-Control-side implementation plan and source-review lane approve it.

## CLI Forms

Validate a temporary fixture pack:

```sh
make mission-control-handoff-reference-validator
```

Validate an existing generated fixture directory:

```sh
uv run python scripts/mission_control_handoff_reference_validator.py \
  --fixture-dir var/review-packets/v3/mission-control-handoff-fixtures
```

Emit machine-readable evidence:

```sh
uv run python scripts/mission_control_handoff_reference_validator.py --json
```

## Boundary

This check is reference evidence only. It does not approve Mission Control runtime importer
behavior, callbacks into Ithildin, bidirectional API integration, policy authority transfer,
approval authority transfer, audit authority transfer, local model invocation, sandbox
orchestration, trusted-host promotion, SIEM adapters, compliance automation, public/security-product
positioning, or new governed tool powers.
