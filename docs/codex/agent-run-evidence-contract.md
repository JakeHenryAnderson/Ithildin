# Agent Run Evidence Contract

Status: evidence-contract preparation. This document does not add runtime behavior, API endpoints,
MCP tools, tool manifests, policy rules, executors, sandbox controls, SIEM adapters, or new governed
tool powers.

This contract defines the stable, secret-free evidence shape Ithildin should use when reconstructing
an agent run timeline from existing local-preview records.

## Evidence Events

Agent Run evidence should cover:

- run created;
- tool call correlated;
- approval correlated;
- audit event correlated;
- export correlated;
- run completed;
- run failed;
- recovery required.

## Stable Fields

Each evidence record should use only safe metadata:

- `run_id`;
- `principal_id`;
- `workspace_id`;
- optional `sandbox_id`;
- `model_client_label`;
- `status`;
- correlation IDs for request, tool call, approval, audit event, export, and recovery diagnostics;
- `policy_hash`;
- `manifest_lock_hash`;
- event timestamp;
- safe status metadata.

These fields are evidence and correlation aids. They do not authorize execution, substitute for
policy, prove actions outside Ithildin-mediated tools, or provide production identity.

## Timeline Reconstruction

A run timeline should be reconstructable from Agent Run records and audit events without exposing
raw tool arguments, prompts, model output, file contents, diffs, response bodies, package script
values, dependency names, credentials, or secrets.

The timeline may show event type, timestamp, short IDs/hashes, principal, workspace, tool name,
decision, approval status, audit event hash, export hash, redaction summary, and recovery status.

## Status Values

Recommended status values are:

- `active`;
- `completed`;
- `failed_closed`;
- `recovery_required`;
- `aborted`;
- `paused`.

`paused` and `aborted` are future state names only unless a later reviewed implementation adds
explicit run-control behavior. This contract does not add pause, abort, kill, repair, or replay
controls.

## Non-Goals

This contract does not provide:

- a sandbox or OS isolation boundary;
- process supervision or lifecycle control;
- SIEM-grade custody;
- compliance automation;
- production identity;
- remote MCP hosting;
- hosted telemetry;
- proof of activity outside Ithildin-mediated tools.

## Verification

Run:

```bash
make agent-run-evidence-contract-check
```

The gate validates that this contract is present, linked from the local preview docs, included in
review materials, and aligned with the current no-new-powers boundary.
