# Trusted-Host Promotion Runtime Implementation

Status: version-2 authority binding and descriptor-relative placement slice implemented behind an
explicit internal test fixture; production proposal/apply readiness remains unavailable pending
`TGB-005` and `TGB-006`.

Current governed tool count: `24`.

Run:

```sh
make trusted-host-promotion-negative-transcripts
```

The current runtime boundary is:

```text
one stored sandbox artifact -> one authority-bound proposal and approval -> production placement denied

internal test fixture only -> atomic execution reservation -> descriptor-relative create-exclusive staging -> completion evidence pending
```

It adds one canonical YAML rule for the internal action, but does not add an MCP tool, governed tool
manifest, Mission Control runtime authority,
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
- exact trusted-host, workspace, and sandbox authority generations;
- YAML policy document/version/digest, `require_approval` decision, matched rule, and bounded
  obligations;
- the exact 24-tool manifest-lock version and digest;
- the closed version-2 proposal-input schema ID and digest;
- the verified runtime-candidate identity, inventory/dependency/release/review evidence, and
  operator authorization ID;
- required approver roles, a versioned authority snapshot hash, and decision hash.

The proposal and approval are inserted in one SQLite coordinator transaction. A creation-audit
failure terminally marks the proposal `approval_evidence_failed` and supersedes the pending
approval. OPA is unsupported only for these routes and returns
`unsupported_policy_engine_for_promotion`; YAML deny, plain allow, incomplete evidence, changed
authority, duplicate evidence, and unknown obligations fail closed.

Apply reconstructs the complete in-memory authority snapshot, verifies the bound approval decision,
and reopens the source exactly once through the descriptor-bound no-follow reader. Authority,
approval-decision, or source drift terminally marks the proposal `authority_stale` before execution
reservation. Production calls still return a conflict before approval consumption, attempt creation,
or filesystem placement.

An explicit internal test fixture additionally opens and retains the pre-provisioned staging-root
descriptor. In one SQLite `BEGIN IMMEDIATE` transaction it compare-and-sets the approved approval
and approval-required proposal to `executing` and inserts exactly one `prepared` attempt. Placement
then traverses only descriptor-relative, no-follow directory components and creates the leaf with
`O_CREAT | O_EXCL | O_NOFOLLOW`. It writes, hashes, and flushes through the same descriptor and
never reopens a path to claim success. Successful staging stops at `completion_evidence_pending`;
it does not emit or claim completion. Concurrent and sequential replay cannot reserve a second
attempt or create a second leaf.

## Output Policy

Responses and audit metadata include only IDs, labels, hashes, sizes, statuses, and output-policy
flags. They do not include file contents, raw host paths, raw source paths, diffs, prompts, model
outputs, shell output, environment values, registry URLs, dependency names, package scripts, private
keys, or secrets.

## Placement Fence

The proposal API accepts only a closed `host-staging://` label and never a raw host path. During
`TGB-004`, normal runtime calls still stop at the explicit placement-unavailable fence. The internal
fixture must be selected when constructing a test app and cannot be enabled by an operator request,
environment toggle, governed tool call, or production route payload.

The internal fixture requires a pre-provisioned staging root and the reviewed `O_DIRECTORY`,
`O_NOFOLLOW`, and `dir_fd` primitives. It keeps placement Manager-local, one artifact, at most `4096`
bytes, and create-exclusive. A staging-root namespace change after writing produces terminal
`placement_evidence_recovery_required`; no completion is claimed and no automatic deletion, retry,
or repair occurs.

This is authority and downgrade evidence only. It is not staging evidence, a final approved-output
transfer, custody system, SIEM adapter, sandbox boundary, or compliance automation.

## Diagnostics

`GET /trusted-host-promotions/diagnostics` is read-only. A verified YAML-bound runtime reports
`availability: ready` and `placement_available: false`; unreviewed/local, incomplete, invalid
candidate, or OPA postures retain their bounded unavailable reasons. Diagnostics can still describe
migrated historical attempts and internal-fixture `prepared`, `staged`, failed, or recovery-required
attempts. It does not repair, retry, roll back, complete approvals, delete files, or mutate staged
artifacts.
