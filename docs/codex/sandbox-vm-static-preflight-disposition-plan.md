# Sandbox/VM Static Preflight External Disposition Plan

Status: external-disposition planning packet for `ERG-003`.

This plan defines how Ithildin should intake and record an external/source-review response for the
CLI-only sandbox/VM static preflight lane. It does not close the lane by itself. It does not approve
live VM/container inspection, sandbox orchestration, Mission Control runtime behavior, local model
invocation, trusted-host promotion, network expansion, API/MCP behavior, new governed tools,
production identity, runtime Postgres, hosted telemetry, remote MCP, SIEM adapters, compliance
automation, or public/security-product positioning.

Current governed tool count: `24`.

Current selected capability: `not selected`.

## Disposition Scope

The disposition applies only to:

- the static profile fixture contract;
- the committed local-preview static profile example;
- negative static profile fixtures;
- the CLI-only fixture preflight runner;
- generated safe-label preflight output;
- observed negative transcripts;
- source-review handoff packet contents;
- internal finding `XH-SANDBOX-PREFLIGHT-001` and its verification.

It does not apply to:

- live VM or container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- local model invocation;
- Mission Control runtime behavior;
- trusted-host artifact promotion;
- network enforcement;
- runtime API/MCP profile loading;
- production deployment or compliance claims.

## Required External Reviewer Disposition

An external/source reviewer response must answer all of these questions:

1. Did the reviewer inspect the static preflight source-review packet and the source files named in
   that packet?
2. Does the CLI-only fixture runner stay within the approved boundary?
3. Are the static profile fixture contract and negative fixtures sufficient for local-preview
   planning evidence?
4. Are safe-label and safe-error expectations strong enough for packet/display use?
5. Does `XH-SANDBOX-PREFLIGHT-001` appear fixed for the local-preview fixture lane?
6. Are there any critical/high findings?
7. If there are no critical/high findings, can `ERG-003` move from `external_review_required` to
   `closed_local_preview_static_preflight`?
8. Does the reviewer explicitly avoid approving live VM/container control, Mission Control runtime
   behavior, local model invocation, trusted-host promotion, or production/security-product claims?

## Allowed Outcomes

The intake result may be one of:

- `external_review_requested`: packet is ready but no external response has been recorded.
- `external_review_changes_requested`: reviewer found blocking or should-fix issues.
- `closed_local_preview_static_preflight`: reviewer accepts the CLI-only static preflight lane for
  local-preview evidence only.
- `accepted_deferred`: reviewer accepts a documented residual risk for local-preview evidence only.
- `blocked`: reviewer found a critical/high issue or a boundary contradiction.

Only `closed_local_preview_static_preflight` may support changing `ERG-003` out of
`external_review_required`, and even that outcome does not approve live sandbox/VM runtime work.

## Required Evidence To Record Closure

Before `ERG-003` can move out of `external_review_required`, record:

- reviewer name/model or human reviewer label;
- review date;
- reviewed commit;
- source-review packet path and artifact hash manifest;
- response transcript path;
- finding IDs and severities;
- explicit answer to every required disposition question;
- verification command list;
- accepted-risk impact;
- statement that broader runtime sandbox/VM work remains blocked.

Use [sandbox-vm-static-preflight-external-response-intake.md](sandbox-vm-static-preflight-external-response-intake.md)
to normalize the raw reviewer response into intake evidence before any committed triage update. The
intake template does not mutate findings, close external review, or move `ERG-003` by itself.

## Post-Disposition Boundary

If an external reviewer accepts this lane, the only allowed stronger statement is:

> The CLI-only static sandbox/VM profile preflight lane is externally reviewed for local-preview
> fixture evidence.

The following remain blocked after a favorable disposition:

- live VM/container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- local model invocation;
- Mission Control runtime behavior;
- trusted-host promotion;
- network expansion;
- API/MCP profile loading;
- production identity;
- SIEM delivery;
- compliance automation;
- public/security-product positioning.

## Validation

Run:

```sh
make sandbox-vm-static-preflight-disposition-plan-check
make sandbox-vm-static-preflight-external-response-intake-check
make sandbox-vm-static-preflight-source-review-packet-check
make enterprise-readiness-gap-matrix-check
```
