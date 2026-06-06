# Agent Run Model Contract

Status: implemented local-preview observability foundation.

This document records the first Agent Run model for Ithildin. It adds durable, read-only
correlation records for governed tool-call sessions so the review console can show a timeline of
agent actions mediated by Ithildin. It does not add a sandbox, process control, agent lifecycle
manager, SIEM backend, production identity, remote MCP, or new governed tool powers.

## Purpose

An Agent Run is a local observability record that groups governed tool-call audit events by trusted
principal, session ID, and workspace label. It lets an operator answer:

- which local principal initiated a sequence of governed tool calls;
- which workspace label the sequence was associated with;
- which requests and audit events belong to the same run;
- what policy/execution events occurred in order.

The run model is deliberately diagnostic. It does not authorize execution and does not replace the
existing registry, schema validation, policy, approval, executor, redaction, or audit gates.

## Runtime Records

The API stores run records in SQLite under the existing local runtime database. Run IDs use the
`run_` prefix. A run record includes:

- `run_id`;
- trusted `principal_id`, `principal_type`, and principal roles;
- `workspace_id` or a conservative non-filesystem label such as `network` or `unscoped`;
- `session_id`;
- status, currently `active`;
- created and updated timestamps;
- last request ID;
- tool-call count;
- latest policy hash;
- latest tool name and tool manifest hash;
- safe metadata.

The store uses one record per `(principal_id, session_id, workspace_id)` tuple. Repeated governed
tool calls with the same tuple update the same run and increment its call count.

## Audit Correlation

When Agent Run tracking is configured, governed tool-call audit metadata includes:

- `run_id`;
- `session_id`;
- `workspace_id`;
- `principal_id`.

The first correlated call also writes an `agent.session.started` audit event with safe metadata. The
run timeline is reconstructed from audit events whose metadata contains the run ID. Timeline entries
include event type, timestamp, request ID, tool name, decision, event hash, resource evidence, and
safe metadata. They do not include raw tool arguments, file contents, unified diffs, response bodies,
prompts, secrets, or model output.

## API Surface

The local admin API exposes:

- `GET /runs`
- `GET /runs/{run_id}`

Both require the existing local admin bearer token. They are read-only. They do not create, mutate,
cancel, replay, repair, approve, or execute anything.

## Review Console Surface

The review console shows a compact Agent Runs panel:

- recent runs by principal, workspace, session, status, and call count;
- selected run timeline with correlated audit events;
- short IDs and hashes for scanning.

The panel is a governance dashboard surface, not an execution control surface.

## Guarantees

For local preview, Agent Runs provide:

- durable SQLite correlation records;
- stable run IDs attached to governed tool-call audit metadata;
- read-only admin APIs;
- timeline reconstruction from existing audit events;
- no new MCP tools, tool manifests, policy rules, approval behavior, or executor capabilities.

## Non-Guarantees

Agent Runs do not provide:

- a kernel sandbox or VM/container isolation;
- process supervision or kill/restart controls;
- independent SIEM-grade custody;
- regulated-retention audit guarantees;
- production identity or enterprise RBAC;
- cross-host distributed tracing;
- protection against host compromise;
- proof that actions outside Ithildin-mediated tools did or did not happen.

Future sandbox demos, SIEM-shaped export adapters, or process lifecycle controls must receive their
own proposals, contracts, tests, and review gates.

## Verification

Focused verification includes:

- governed-call tests proving run records are created and audit metadata carries `run_id`;
- API tests proving `/runs` and `/runs/{run_id}` require admin auth and return safe timeline data;
- UI tests proving the Agent Runs panel renders;
- full gates through `make release-check`.
