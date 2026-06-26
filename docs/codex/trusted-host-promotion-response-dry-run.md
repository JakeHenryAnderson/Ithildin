# Trusted-Host Promotion Response Dry Run

Status: temporary-fixture validation for blocked `ERG-005` normalized response handling.

This dry run exercises the trusted-host promotion disposition closure gate with temporary
normalized-response fixtures. It restores
`var/review-runs/trusted-host-promotion/normalized-response.json` to its original state before
exiting. It does not record external review, mutate committed findings, close `ERG-005`, approve
implementation planning, approve runtime implementation, or approve trusted-host promotion.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Run:

```sh
make trusted-host-promotion-response-dry-run
```

## What It Proves

The dry run verifies that:

- an absent normalized response keeps `closure_ready: false`;
- a source-level favorable response with `disposition_outcome: continue_design_only` can become
  `closure_ready: true` for later committed triage consideration;
- packet-only evidence is rejected for closure;
- malformed packet hashes are rejected;
- critical/high findings are rejected;
- responses that try to close external review directly are rejected;
- the ignored normalized-response path is restored after the dry run.

## What It Does Not Prove

It does not prove that an external reviewer has inspected trusted-host promotion evidence. It does
not close `ERG-005`. It does not approve implementation planning, runtime implementation,
trusted-host promotion, direct host writes, overwrite/delete/move behavior, broad archive
extraction, automatic promotion, promotion without exact artifact hash binding, promotion without
approval evidence, Mission Control runtime behavior, local model invocation, VM/container lifecycle
management, sandbox orchestration, SIEM adapter behavior, production identity, runtime Postgres,
hosted telemetry, remote MCP, compliance automation, new governed tool powers, or
public/security-product positioning.

## Relationship To ERG-005

`ERG-005` remains `blocked` unless a real normalized response is recorded, the closure gate reports
`closure_ready: true`, and a later committed triage update records the reviewer response, findings,
reviewed commit, reviewed packet hash, and decision-record status. Even then, the only supported
next state is design-only decision consideration; runtime trusted-host promotion remains blocked
until a separate explicit implementation decision exists.

Recommended focused sequence:

```sh
make trusted-host-promotion-external-response-intake-check
make trusted-host-promotion-disposition-closure-check
make trusted-host-promotion-response-dry-run
make trusted-host-promotion-disposition-packet-check
```
