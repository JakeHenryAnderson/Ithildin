# Trusted-Host Promotion Zone Contract

Status: design-only source/destination zone contract for `ERG-005` and `PRD-TRUSTED-HOST-001`.

Current governed tool count: `24`.

Current `ERG-005` status: `blocked`.

Current selected capability: `not selected`.

This contract defines future source, staging, and approved-output zone labels for trusted-host
promotion planning. It does not approve runtime behavior, direct host writes, overwrite/delete/move
behavior, broad archive extraction, automatic promotion, promotion without exact artifact hash
binding, promotion without approval evidence, API/MCP behavior, Mission Control runtime behavior,
local model invocation, VM/container lifecycle management, sandbox orchestration, SIEM adapters,
production identity, runtime Postgres, hosted telemetry, shell, Docker/Kubernetes/browser governed
powers, arbitrary HTTP, broad filesystem writes, compliance automation, or public/security-product
claims.

Validate this zone contract with:

```sh
make trusted-host-promotion-zone-contract-check
```

The matching implementation-plan skeleton is
[trusted-host-promotion-implementation-plan.md](trusted-host-promotion-implementation-plan.md),
validated with `make trusted-host-promotion-implementation-plan-check`.

## Zone Vocabulary

Current runtime/demo evidence may only report `promotion_status: not_promoted`. The labels below are
future evidence identifiers, not filesystem authority.

| Zone | Label prefix | Future role | Current posture |
| --- | --- | --- | --- |
| Sandbox artifact source | `sandbox://` | Artifact created inside an operator-managed sandbox or local-preview sandbox-labeled workspace. | evidence label only |
| Host staging | `host-staging://` | Reviewed staging label on the trusted host before final approved output. | design-only |
| Approved output | `approved://` | Final approved-output label after explicit approval and hash-bound promotion. | design-only |
| Evidence record | `evidence://` | Non-content evidence pointer for audit/export/review packet records. | evidence label only |

Raw filesystem paths are forbidden in promotion evidence. A future implementation may resolve labels
to actual storage only after a separate implementation decision, source review, approval binding
model, negative transcript coverage, and release readiness gate approve the exact path.

## Zone Movement Rules

Future promotion planning may model only this movement:

```text
sandbox://artifact -> host-staging://artifact -> approved://artifact
```

Every future movement must be one artifact, one approval, and one bounded destination label. The
source artifact hash, staging hash, and approved-output hash must match before any completion state
can be recorded.

The following movements remain forbidden:

- `sandbox://` directly to arbitrary host path;
- `sandbox://` directly to `approved://` without staging evidence;
- `host-staging://` to overwrite, delete, move, chmod, archive extraction, or directory merge;
- any label to `.git`, hidden, symlink, hardlink, directory, binary target, unsupported type, or
  broad archive target;
- any path or label containing absolute paths, parent traversal, encoded traversal,
  URL-shaped destinations, Unicode ambiguity, control characters, raw host paths, or raw sandbox-internal paths;
- any automatic promotion, batch promotion, wildcard promotion, recursive promotion, or promotion
  without operator acknowledgement.

## Label Shape

Future labels must be stable, normalized, and non-secret:

```json
{
  "schema_version": "1",
  "source_artifact_label": "sandbox://demo/output.txt",
  "host_staging_label": "host-staging://demo/output.txt",
  "approved_host_label": "approved://demo/output.txt",
  "evidence_label": "evidence://promotion/promotion_fixture",
  "source_artifact_sha256": "sha256:...",
  "host_staging_sha256": "sha256:...",
  "approved_host_sha256": "sha256:...",
  "promotion_status": "not_promoted",
  "runtime_promotion_performed": false,
  "trusted_host_write_performed": false
}
```

Labels must not contain file contents, prompts, diffs, response bodies, raw host paths, raw
sandbox-internal paths, usernames, home directories, VM logs, shell output, package script values,
dependency names, environment names or values, registry URLs, tokens, private keys, stack traces, or
model outputs.

## Required Future Evidence

Any future implementation plan must bind the zone labels to:

- promotion ID, request hash, one-time scope hash, approval ID, and approval expiry;
- workspace ID, sandbox ID, operator principal, policy hash, manifest hash, schema/tool version,
  and reviewed packet commit;
- source artifact label and hash;
- host staging label and expected hash;
- approved-output label and expected hash;
- warning-state acknowledgement and conflict/replay/stale evidence denial transcripts;
- read-only recovery diagnostic shape for any incomplete attempt.

## Current Implementation Boundary

This contract is a planning and review artifact. It does not implement trusted-host promotion,
host-placement attempts, repair, rollback, reconciliation, promotion diagnostics, Mission Control
runtime behavior, local model invocation, VM/container lifecycle management, sandbox orchestration,
SIEM adapters, production identity, runtime Postgres, hosted telemetry, shell execution, Docker or
Kubernetes control, browser automation, arbitrary HTTP, broad filesystem writes, compliance
automation, or public/security-product posture.

Current outputs must continue to report:

- decision record required: `true`;
- implementation approved: `false`;
- runtime changes allowed: `false`;
- trusted-host promotion allowed: `false`;
- direct host writes allowed: `false`;
- overwrite/delete/move allowed: `false`;
- broad archive extraction allowed: `false`;
- automatic promotion allowed: `false`;
- promotion without exact artifact hash binding allowed: `false`;
- promotion without approval evidence allowed: `false`;
- Mission Control runtime allowed: `false`;
- local model invocation allowed: `false`;
- sandbox orchestration allowed: `false`;
- SIEM adapter allowed: `false`;
- new power classes allowed: `false`;
- public/security-product positioning allowed: `false`.
