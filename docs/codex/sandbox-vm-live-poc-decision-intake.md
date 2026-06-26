# Sandbox/VM Live POC Decision Intake

Status: decision-intake planning packet for `ERG-004`.

Current governed tool count: `24`.

Current `ERG-004` status: `blocked`.

Current selected capability: `not selected`.

This document defines the evidence required before Ithildin may even plan a live
sandbox/VM worker proof of concept. It does not approve live VM/container inspection, does not
approve sandbox orchestration, does not approve local model invocation, does not approve Mission
Control runtime behavior, and does not approve trusted-host promotion.

Requires favorable `ERG-003` disposition before implementation planning. The static
preflight lane must be externally/source reviewed first, and any critical/high findings must be
resolved or explicitly stop the live POC lane.

This intake does not approve sandbox orchestration.

This intake does not approve Mission Control runtime behavior.

## Required Decision Record

A future post-RC decision record must exist before `ERG-004` can move out of `blocked`. That record
must name the reviewed commit, reference this intake packet, and state whether the live POC remains
blocked, may move to implementation planning, or must be split into smaller decision records.
The future decision record must use
[sandbox-vm-live-poc-decision-record-skeleton.md](sandbox-vm-live-poc-decision-record-skeleton.md)
so any movement is limited to implementation-planning-only status and keeps live runtime behavior
blocked.

The decision record must include:

- the favorable `ERG-003` disposition evidence;
- an operator-managed VM profile;
- a network/mount/root contract;
- preflight safety checks;
- a cleanup transcript;
- a failure transcript;
- the Ithildin-governed tool boundary;
- the Mission Control display-only boundary if Mission Control is involved;
- a local model invocation plan that remains blocked until the decision explicitly authorizes a
  later implementation plan;
- external/source review requirements;
- stop conditions for ambiguous sandbox, host, identity, audit, or product-positioning claims.

## Boundary Requirements

Any future planning packet must preserve these boundaries:

- no shell;
- no Docker socket;
- no Kubernetes;
- no browser automation;
- no arbitrary HTTP;
- no broad filesystem writes;
- no production identity;
- no SIEM adapter;
- no compliance automation;
- no remote MCP hosting;
- no plugin SDK;
- public/security-product positioning remains blocked.

The live POC, if later approved for planning, must be framed as an operator-managed lab exercise. It
must not describe the host as untrusted, must not promote a sandbox artifact into trusted host space,
and must not claim OS isolation beyond the operator-managed VM/container layer being observed.

## Evidence Shape

The live POC planning evidence must be secret-free and should use stable labels rather than raw
host-specific paths where practical.

Minimum evidence fields:

- `decision_record_id`;
- `erg_id: ERG-004`;
- `prior_lane: ERG-003`;
- `operator_vm_profile_id`;
- `workspace_id`;
- `sandbox_id`;
- `network_posture`;
- `mount_root_posture`;
- `artifact_ingress_posture`;
- `artifact_egress_posture`;
- `mission_control_role`;
- `ithildin_role`;
- `local_model_role`;
- `cleanup_transcript_status`;
- `failure_transcript_status`;
- `external_review_status`;
- `implementation_approved: false`.

## Stop Conditions

Stop the lane and keep `ERG-004` blocked if any of these are true:

- the `ERG-003` static preflight disposition is missing, unfavorable, or contains unresolved
  critical/high findings;
- the future plan requires Ithildin to manage a VM/container lifecycle directly;
- the future plan requires Mission Control to execute, approve, or govern actions;
- the future plan requires local model invocation before a separate implementation plan exists;
- the future plan changes the trusted-host boundary;
- the future plan requires broad writes, arbitrary network, shell, Docker socket, Kubernetes, or
  browser automation;
- the future plan implies production deployment, compliance automation, SIEM custody, or public
  security-product positioning.

## Allowed Output

The only allowed output of this intake lane is a decision-intake-ready status for a future
post-RC decision record. It is not an implementation approval, not a runtime profile loader, not a
live preflight runner, not a Mission Control integration, and not a local model worker.

Validate the intake and decision-record skeleton with:

```sh
make sandbox-vm-live-poc-decision-intake-check
make sandbox-vm-live-poc-decision-record-skeleton-check
```
