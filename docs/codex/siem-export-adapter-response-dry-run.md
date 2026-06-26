# SIEM Export Adapter Response Dry Run

Status: temporary-fixture validation for planning-only `ERG-008` normalized response handling.

This dry run exercises the SIEM export adapter disposition closure gate with temporary
normalized-response fixtures. It restores
`var/review-runs/siem-export-adapter/normalized-response.json` to its original state before
exiting. It does not record external review, mutate committed findings, close `ERG-008`, record
architecture planning, approve implementation planning, approve runtime implementation, approve
SIEM adapter behavior, approve hosted telemetry, approve remote delivery, or approve custody-grade
audit claims.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Run:

```sh
make siem-export-adapter-response-dry-run
```

## What It Proves

The dry run verifies that:

- an absent normalized response keeps `closure_ready: false`;
- a source-level favorable response with `disposition_outcome: continue_architecture_planning` can
  become `closure_ready: true` for later committed triage consideration;
- packet-only evidence is rejected for closure;
- malformed packet hashes are rejected;
- critical/high findings are rejected;
- responses that try to close external review directly are rejected;
- the ignored normalized-response path is restored after the dry run.

## What It Does Not Prove

It does not prove that an external reviewer has inspected the SIEM export adapter evidence. It does
not close `ERG-008`. It does not approve implementation planning, runtime implementation, SIEM
adapter behavior, hosted telemetry, remote delivery, custody-grade audit claims, external
notarization, immutable storage, production identity, runtime Postgres, compliance automation,
security-operations control-plane claims, hosted control plane behavior, sandbox orchestration,
local model invocation, trusted-host promotion, shell/Docker/Kubernetes/browser governed powers,
arbitrary HTTP, broad filesystem writes, plugin SDK behavior, new governed tool powers, or
public/security-product positioning.

## Relationship To ERG-008

`ERG-008` remains `planning_only` unless a real normalized response is recorded, the closure gate
reports `closure_ready: true`, and a later committed triage update records the reviewer response,
findings, reviewed commit, reviewed packet hash, and decision-record status. Even then, the only
supported next state is architecture decision consideration; SIEM adapter runtime behavior, hosted
telemetry, remote delivery, custody-grade audit claims, external notarization, immutable storage,
and security-operations control-plane claims remain blocked until separate explicit implementation
decisions exist.

Recommended focused sequence:

```sh
make siem-export-adapter-external-response-intake-check
make siem-export-adapter-disposition-closure-check
make siem-export-adapter-response-dry-run
make siem-export-adapter-disposition-packet-check
make siem-export-adapter-architecture-check
```
