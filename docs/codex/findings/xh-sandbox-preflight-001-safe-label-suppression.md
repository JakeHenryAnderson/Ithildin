# XH-SANDBOX-PREFLIGHT-001 Safe Label Suppression

- Finding ID: XH-SANDBOX-PREFLIGHT-001
- Severity: medium
- Area: sandbox VM static preflight
- Affected files/functions: scripts/sandbox_vm_static_preflight.py `_safe_labelish`; tests/test_release_readiness.py `test_sandbox_vm_static_preflight_runner_and_transcripts_are_safe`
- Claim being tested: The CLI-only static preflight report should not echo raw filesystem paths or path-shaped labels while claiming `raw_paths_included: false`.
- Observed behavior: Internal review found `_safe_labelish` rejected several sensitive path patterns but still allowed generic slash-containing values such as `/opt/demo/workspace` for echoed fields like `workspace_id`.
- Risk: A malformed or adversarial fixture could cause the preflight report to echo raw path-shaped metadata, weakening the secret-free evidence contract and confusing downstream Mission Control display/import planning.
- Recommended fix: Fixed by making `_safe_labelish` reject leading `/`, `~`, and backslash-containing values while preserving bounded URI-like labels such as `sandbox://demo`.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `tests/test_release_readiness.py::test_sandbox_vm_static_preflight_runner_and_transcripts_are_safe` now verifies that `/opt/demo/workspace` is suppressed from the report, and `make sandbox-vm-static-preflight`, `make sandbox-vm-static-preflight-implementation-gate`, and `make release-check` cover the runner and boundary wiring.
