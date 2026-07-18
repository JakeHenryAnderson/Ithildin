# Trusted-Host Promotion Runtime Implementation

Status: `TGB-005` implementation candidate. Version-2 authority binding, descriptor-relative
placement, completion evidence, read-only diagnostics, and the Command Center evidence consumer are
implemented. Exact-candidate adversarial proof and independent source review remain pending in
`TGB-006`.

Current governed tool count: `24`.

Run:

```sh
make trusted-host-promotion-negative-transcripts
```

The current runtime boundary is:

```text
incomplete or unverified runtime posture -> proposal/apply denied

fully verified local runtime posture -> one authority-bound proposal and approval -> atomic execution reservation
  -> descriptor-relative create-exclusive staging -> append-only completion audit -> completed
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
- source artifact label in persistence and binding; review/API output exposes only its reference hash;
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
reservation. Normal runtime proposal/apply remains unavailable unless every non-environment
readiness component is verified. There is no request field, environment toggle, or operator override
that can waive a missing component.

An explicit internal test fixture additionally opens and retains the pre-provisioned staging-root
descriptor. In one SQLite `BEGIN IMMEDIATE` transaction it compare-and-sets the approved approval
and approval-required proposal to `executing` and inserts exactly one `prepared` attempt. Placement
then traverses only descriptor-relative, no-follow directory components and creates the leaf with
`O_CREAT | O_EXCL | O_NOFOLLOW`. It writes, hashes, and flushes through the same descriptor and
never reopens a path to claim success. Successful staging first records
`completion_evidence_pending`. The append-only completion event must then be serialized onto the
current audit-chain head and durably written before the attempt and proposal may become `completed`.
An audit failure leaves completion pending and never claims success. Concurrent and sequential
replay cannot reserve a second attempt or create a second leaf; concurrent audit appends are
serialized in the same SQLite transaction that reads the chain head.

## Output Policy

Responses and audit metadata include only bounded IDs, the closed host-staging label, hashes, sizes,
statuses, versions, and output-policy flags. The persisted source label is represented to operators
only by `source_artifact_reference_hash`. Responses do not include file contents, raw host paths,
raw source labels or paths, diffs, prompts, model outputs, shell output, environment values,
registry URLs, dependency names, package scripts, private keys, bearer material, policy documents,
candidate locations, stack traces, or secrets.

## Placement Fence

The proposal API accepts only a closed `host-staging://` label and never a raw host path. Normal
runtime placement is ready only when all of the following are independently verified: current
runtime candidate and detached operator authorization, current database contract, YAML policy,
on-disk enforced principal/workspace/trusted-host registries, the exact 24-tool manifest lock,
version-2 proposal schema, descriptor-relative platform primitives, an openable staging-root
descriptor, and disabled internal fixtures. Any false component keeps proposal/apply unavailable.

The internal fixture must be selected when constructing a test app and cannot be enabled by an
operator request, environment toggle, governed tool call, or route payload.

The internal fixture requires a pre-provisioned staging root and the reviewed `O_DIRECTORY`,
`O_NOFOLLOW`, and `dir_fd` primitives. It keeps placement Manager-local, one artifact, at most `4096`
bytes, and create-exclusive. A staging-root namespace change after writing produces terminal
`placement_evidence_recovery_required`; no completion is claimed and no automatic deletion, retry,
or repair occurs.

This is authority and downgrade evidence only. It is not staging evidence, a final approved-output
transfer, custody system, SIEM adapter, sandbox boundary, or compliance automation.

## Diagnostics

`GET /trusted-host-promotions/diagnostics` is read-only. A fully verified local runtime reports
`availability: ready` and `placement_available: true`; incomplete, invalid-candidate, unenforced
registry, unverified-manifest, fixture-enabled, or OPA postures retain their bounded unavailable
reasons. Diagnostics distinguish clean, stale, legacy, incomplete, approval-terminal, and
recovery-required evidence. Malformed persisted authority evidence is rendered as invalid/stale
rather than raising or returning its raw content. Denied, expired, and superseded approvals are
shown as terminal without implying that placement or completion began. The Command Center consumer
uses the server-returned effective status, deciding principal, decision hash, readiness components,
and recommendations; it does not reconstruct authority or offer retry/repair controls.

Diagnostics can still describe migrated historical attempts and `prepared`, `staged`, failed,
completion-pending, or recovery-required attempts. They do not repair, retry, roll back, complete
approvals, delete files, or mutate staged artifacts.

This candidate remains a self-hosted local-preview capability, not proof of production deployment
security, host-compromise resistance, custody-grade evidence, SIEM delivery, compliance
automation, or external review closure.
