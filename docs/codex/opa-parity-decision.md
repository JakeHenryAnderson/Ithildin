# OPA Parity Decision

Task 097 records the v0.3-prep decision for optional OPA policy support:

**YAML remains the canonical local-preview policy engine for parity and release gates. OPA remains an
optional sidecar/evidence prototype until it has its own fixture runner or controlled test server
that can execute the same policy parity cases as YAML.**

Short form: OPA remains an optional sidecar/evidence prototype, not the canonical parity engine.

## Current OPA Guarantees

When `ITHILDIN_POLICY_ENGINE=opa` is selected, Ithildin:

- requires `ITHILDIN_OPA_URL`;
- verifies `policies/opa/bundle.lock.json` before startup;
- pins local Rego source hashes and bundle metadata;
- reports bundle version, entrypoint, bundle hash, source hashes, and verified state through
  policy/system status;
- fails closed if the sidecar request fails, returns malformed data, or returns an invalid decision;
- uses verified bundle evidence as fallback policy version/hash evidence when OPA does not return a
  policy version.

## Current OPA Non-Guarantees

OPA mode does not currently:

- run the committed `policies/tests/default.yaml` YAML policy fixtures;
- run `policies/tests/parity.yaml`;
- prove semantic equivalence with `policies/default.yaml`;
- make OPA the source of truth for local-preview policy claims;
- add hosted policy distribution, remote policy management, or production authorization semantics.

## Required Before OPA Can Become Canonical

OPA can become canonical only after a future task adds at least one of:

- an OPA fixture runner that evaluates the same policy input cases as `make policy-test`;
- an OPA parity harness that compares `/policy/preview` and governed runtime evidence through a
  controlled OPA test server or mocked OPA transport;
- explicit policy migration docs explaining which YAML rules are replaced, how rule evidence maps to
  OPA package/rule IDs, and how release gates fail closed on drift.

Until then, `make policy-test` and `make policy-parity` are YAML-engine assurance gates. OPA is
valuable local evidence and fail-closed prototype support, not a semantic parity claim.
