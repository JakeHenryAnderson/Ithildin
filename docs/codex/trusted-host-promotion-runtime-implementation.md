# Trusted-Host Promotion Runtime Implementation

Status: version-2 authority/persistence slice implemented; trusted-host placement intentionally
unavailable pending `TGB-003` through `TGB-006`.

Current governed tool count: `24`.

Run:

```sh
make trusted-host-promotion-negative-transcripts
```

The current runtime boundary is:

```text
one stored sandbox artifact -> one authority-bound proposal and approval -> placement denied with no attempt or filesystem effect
```

It does not add an MCP tool, governed tool manifest, policy rule, Mission Control runtime authority,
local model invocation, VM/container lifecycle control, sandbox orchestration, SIEM adapter,
production identity, runtime Postgres, hosted telemetry, remote MCP, shell, Docker, Kubernetes,
browser automation, arbitrary HTTP, broad filesystem writes, broad host writes, automatic promotion,
approved-output publishing, compliance automation, or public/security-product claims.

## Runtime Surfaces

- Admin-only `POST /trusted-host-promotions/proposals`
- Admin-only `GET /trusted-host-promotions/proposals`
- Admin-only `GET /trusted-host-promotions/proposals/{proposal_id}`
- Admin-only `POST /trusted-host-promotions/proposals/{proposal_id}/apply`
- Admin-only `GET /trusted-host-promotions/diagnostics`
- `/system/status.trusted_host_promotions` read-only status label

The runtime uses the existing approval service. The approval `tool_name` is
`trusted_host.promotion.stage`, but no governed tool manifest or MCP exposure is added.

## Binding Model

The version-2 proposal and approval records bind:

- promotion proposal ID and proposal hash;
- workspace ID;
- sandbox descriptor ID and descriptor hash;
- sandbox ID;
- source artifact label;
- host staging label;
- artifact SHA-256;
- artifact size;
- artifact media label;
- one-time approval ID, status, request hash, and expiry through the existing approval store;
- server-derived requester and deciding-principal identity generations;
- a versioned authority snapshot hash and decision hash.

The complete policy, manifest, schema, runtime-candidate, and operator-authorization snapshot is not
yet assembled. The test-only `TGB-002` fixture cannot authorize placement. Apply requests therefore
return a conflict before approval consumption, attempt creation, execution audit events, source
re-read, or filesystem placement. Stale-source, replay-consumption, atomic-placement, and completion
evidence claims remain owned by later tickets.

## Output Policy

Responses and audit metadata include only IDs, labels, hashes, sizes, statuses, and output-policy
flags. They do not include file contents, raw host paths, raw source paths, diffs, prompts, model
outputs, shell output, environment values, registry URLs, dependency names, package scripts, private
keys, or secrets.

## Placement Fence

The proposal API accepts only a closed `host-staging://` label and never a raw host path. During
`TGB-002`, the apply route always stops at the explicit placement-unavailable fence. It creates no
promotion attempt, emits no tool-execution start/completion claim, and writes no staging artifact.

This is authority and downgrade evidence only. It is not staging evidence, a final approved-output
transfer, custody system, SIEM adapter, sandbox boundary, or compliance automation.

## Diagnostics

`GET /trusted-host-promotions/diagnostics` is read-only and reports
`availability: governance_binding_incomplete`. It can still describe migrated historical attempts,
but current `TGB-002` apply calls create none. It does not repair, retry, roll back, complete
approvals, delete files, or mutate staged artifacts.
