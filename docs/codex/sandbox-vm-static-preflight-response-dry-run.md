# Sandbox/VM Static Preflight Response Dry Run

Status: temporary-fixture validation for `ERG-003` normalized response handling.

Validate with:

```sh
make sandbox-vm-static-preflight-response-dry-run
```

This dry run exercises the static sandbox/VM preflight disposition closure gate with temporary
ignored normalized-response fixtures. It does not record external review, mutate reviewer findings,
close `ERG-003`, approve runtime behavior, or change the product boundary.

Current governed tool count: `24`.

Current selected capability: `not selected`.

## What It Verifies

The dry run temporarily writes and then restores:

```text
var/review-runs/sandbox-vm-static-preflight/normalized-response.json
```

It verifies:

- absent normalized response keeps `closure_ready: false`;
- source-level or packet-and-source response shape with no findings can make the closure gate
  report `closure_ready: true` for later committed triage;
- packet-only evidence is rejected for closure;
- malformed packet hashes are rejected;
- mismatched packet hashes are rejected;
- critical/high findings are rejected;
- responses that try to close external review directly are rejected;
- the original ignored response path is restored after the run.

## What It Does Not Prove

The dry run is fixture evidence only. It does not prove that an external reviewer has inspected the
static preflight implementation, and it does not mean the lane is closed.

It also does not approve:

- live VM/container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- Mission Control runtime behavior;
- local model invocation;
- trusted-host promotion;
- network expansion;
- API/MCP profile loading;
- new governed tool powers;
- production identity;
- SIEM delivery;
- compliance automation;
- public/security-product positioning.

## Relationship To ERG-003

`ERG-003` remains `external_review_required` unless a real normalized response is recorded, the
closure gate reports `closure_ready: true`, and a later committed triage update records the
reviewer, source access, reviewed commit, packet hash, findings, matrix changes, and release gates.
The packet hash must match the SHA-256 digest of the current ERG-003 external-review artifact-hash
manifest.

Run this dry run alongside:

```sh
make sandbox-vm-static-preflight-external-response-intake-check
make sandbox-vm-static-preflight-disposition-closure-check
make sandbox-vm-static-preflight-disposition-plan-check
```
