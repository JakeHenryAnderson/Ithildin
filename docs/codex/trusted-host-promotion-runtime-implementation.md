# Trusted-Host Promotion Runtime Implementation

Status: staging-only local-preview runtime slice implemented for `ERG-005`.

Current governed tool count: `24`.

Run:

```sh
make trusted-host-promotion-negative-transcripts
```

This implementation keeps trusted-host promotion narrow:

```text
one stored sandbox artifact -> one operator-approved host staging placement -> one read-only evidence record
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

Promotion proposal and approval evidence bind:

- promotion proposal ID and proposal hash;
- workspace ID;
- sandbox descriptor ID and descriptor hash;
- sandbox ID;
- source artifact label;
- host staging label;
- artifact SHA-256;
- artifact size;
- artifact media label;
- one-time approval ID, status, request hash, and expiry through the existing approval store.

Before staging, the runtime re-reads the source artifact and rejects stale artifact hashes. Replayed
approvals fail closed through the existing compare-and-set approval execution path.

## Output Policy

Responses and audit metadata include only IDs, labels, hashes, sizes, statuses, and output-policy
flags. They do not include file contents, raw host paths, raw source paths, diffs, prompts, model
outputs, shell output, environment values, registry URLs, dependency names, package scripts, private
keys, or secrets.

## Staging Behavior

The staging destination is derived from an operator-reviewed `host-staging://` label and the local
`ITHILDIN_TRUSTED_HOST_STAGING_ROOT` setting, defaulting to `var/trusted-host-staging`. The API does
not accept raw host paths. Existing destinations are never overwritten.

This is still local-preview staging evidence. It is not a final approved-output transfer, custody
system, SIEM adapter, sandbox boundary, or compliance automation.

## Diagnostics

`GET /trusted-host-promotions/diagnostics` is read-only. It reports `clean`, `ambiguous`, or
`recovery_required` with safe metadata and an operator recommendation. It does not repair, retry,
roll back, complete approvals, delete files, or mutate staged artifacts.
