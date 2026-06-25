# Sandbox/VM Static Preflight Internal Source Review

Status: internal source-review pass complete for continued local-preview development.

This review inspected the CLI-only static sandbox/VM profile preflight runner. It does not approve
live VM/container inspection, sandbox orchestration, Mission Control runtime behavior, local model
invocation, trusted-host promotion, network expansion, API/MCP behavior, new governed tools, or
production/security-product positioning.

## Scope

- Runner: `scripts/sandbox_vm_static_preflight.py`.
- Negative transcript generator: `scripts/sandbox_vm_static_preflight_negative_transcripts.py`.
- Boundary gate: `scripts/sandbox_vm_static_preflight_implementation_gate.py`.
- Fixture contract and negative fixtures:
  `scripts/sandbox_vm_static_profile_fixture_contract_check.py`,
  `scripts/sandbox_vm_static_profile_negative_fixtures_check.py`, and
  `docs/codex/fixtures/sandbox-vm-static-profile.local-preview.example.json`.
- Source-review packet generator:
  `scripts/sandbox_vm_static_preflight_source_review_packet.py`.
- Focused tests: `tests/test_release_readiness.py`.

## Claims Tested

- The runner reads only a supplied static JSON fixture and does not inspect live VM/container,
  Mission Control, local model, network, or governed tool state.
- Output is secret-free and limited to safe labels, counts, decision status, warning labels, false
  authority flags, safe reason labels, and explicit output-policy metadata.
- Unsafe fixture posture fails closed with `decision: no_go`.
- The committed local-preview fixture remains valid but produces `decision: review_required`, not
  `go`.
- Raw path-shaped labels, broad network posture, Mission Control authority claims, local model
  invocation claims, and trusted-host promotion claims are denied or suppressed.
- The source-review packet includes implementation, tests, contracts, command evidence, negative
  transcripts, and artifact hashes for reviewer handoff.

## Implementation Evidence

- `sandbox_vm_static_preflight.build_report` loads bounded UTF-8 JSON fixtures, rejects oversized,
  malformed, non-object, unsupported-encoding, and unreadable fixtures with safe reason labels.
- The runner delegates fixture semantics to the static fixture contract and converts validation
  failures into coarse reason labels.
- The output policy explicitly records that raw paths, file contents, model prompts/outputs, shell
  output, network endpoints, secret values, runtime sandbox inspection, Mission Control runtime
  calls, local model invocation, and trusted-host promotion are absent.
- The negative transcript generator mutates fixture copies in an ignored output directory and
  records observed denials without preserving the temporary fixture bodies.
- `make sandbox-vm-static-preflight`, `make sandbox-vm-static-preflight-negative-transcripts`,
  `make sandbox-vm-static-preflight-implementation-gate`, and
  `make sandbox-vm-static-preflight-source-review-packet-check` are release-wired.

## Finding

| Finding ID | Severity | Area | Affected files/functions | Blocking status | Disposition | Recommended fix |
| --- | --- | --- | --- | --- | --- | --- |
| XH-SANDBOX-PREFLIGHT-001 | medium | sandbox VM static preflight | `scripts/sandbox_vm_static_preflight.py` `_safe_labelish` | should-fix | fixed | Reject raw path-shaped echoed labels beyond the narrow sensitive-pattern list while still allowing safe URI-like labels such as `sandbox://demo`. |

## Verification Notes

`XH-SANDBOX-PREFLIGHT-001` was fixed by making `_safe_labelish` reject leading `/`, `~`, and
backslash-containing values, while allowing only bounded scheme labels of the form
`scheme://label` or simple alphanumeric labels. Regression coverage now proves that a fixture with
`workspace_id: /opt/demo/workspace` does not echo that raw path in the report.

## Residual Risk

The preflight runner is a local CLI evidence helper over static fixtures, not an enforcement point.
It can help operators and reviewers detect obvious profile overclaims before a future sandbox or
Mission Control display integration, but it cannot prove live VM isolation, live mount state,
network confinement, cleanup behavior, or model behavior. Those remain future separately gated
implementation/review lanes.

## Follow-Up Queue

- No critical or high findings were found.
- `XH-SANDBOX-PREFLIGHT-001` is fixed.
- The static preflight lane is locally reviewed for continued local-preview development only.
- External/source review remains pending before stronger claims or runtime integration.
- Mission Control display/import remains metadata-only, and live sandbox/VM orchestration remains
  blocked.

## Verification

Run:

```bash
make sandbox-vm-static-preflight
make sandbox-vm-static-preflight-negative-transcripts
make sandbox-vm-static-preflight-implementation-gate
make sandbox-vm-static-preflight-source-review-packet-check
uv run pytest tests/test_release_readiness.py::test_sandbox_vm_static_preflight_runner_and_transcripts_are_safe -q
make release-check
```
