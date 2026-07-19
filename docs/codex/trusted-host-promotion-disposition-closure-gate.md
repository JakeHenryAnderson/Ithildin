# Trusted-Host Promotion Disposition Closure Gate

Status: fail-closed closure gate for blocked `ERG-005`.

This gate records the minimum evidence required before a later committed triage update may move
`ERG-005` away from `blocked`. It does not close `ERG-005` by itself. It does not approve
implementation planning, runtime implementation, trusted-host promotion, direct host writes,
overwrite/delete/move behavior, broad archive extraction, automatic promotion, promotion without
exact artifact hash binding, promotion without approval evidence, Mission Control runtime behavior,
local model invocation, VM/container lifecycle management, sandbox orchestration, SIEM adapter
behavior, production identity, runtime Postgres, hosted telemetry, remote MCP, compliance
automation, new governed tool powers, or public/security-product positioning.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Validation command:

```sh
make trusted-host-promotion-disposition-closure-check
```

## Required Normalized Response

The gate looks for this ignored/local evidence file:

```text
var/review-runs/trusted-host-promotion/normalized-response.json
```

The response must be produced from
[trusted-host-promotion-external-response-intake.md](trusted-host-promotion-external-response-intake.md)
using the external response normalizer. The expected response shape is:

- response type: `ithildin.external_review.normalized_response`;
- reviewed area: `trusted-host-promotion`;
- runtime reviewed area: `trusted-host-promotion-runtime`;
- source access: `source-level` or `packet-and-source`;
- finding namespace: `EXT-TRUSTED-HOST-###`;
- runtime finding namespace: `EXT-TRUSTED-HOST-RUNTIME-###`;
- for a runtime response, the full exact reviewed commit must match `source_commit` in the focused
  runtime candidate review packet;
- for a runtime response, `reviewed_packet_hash` must equal the actual focused runtime packet manifest digest computed from
  `trusted-host-promotion-runtime-source-review-artifact-hashes.json`;
- reviewed packet hash: `sha256:<64 lowercase hex chars>`;
- `can_close_source_rows: true`;
- `mutates_findings: false`;
- `closes_external_review: false`;
- no unresolved critical/high findings;
- design disposition: `disposition_outcome: continue_design_only`; or
- runtime disposition: `disposition_outcome: runtime_findings_closed`, with both
  `EXT-TRUSTED-HOST-RUNTIME-002` and `EXT-TRUSTED-HOST-RUNTIME-006` explicitly recorded as
  `fixed`.

The area and namespace must be a matching pair. The design-level packet uses
`trusted-host-promotion` with `EXT-TRUSTED-HOST-###`; the implemented staging-only runtime packet
uses `trusted-host-promotion-runtime` with `EXT-TRUSTED-HOST-RUNTIME-###`. Runtime findings must not
be relabeled into the design namespace to pass intake.

If that file is absent, malformed, packet-only/docs-only, missing the allowed disposition outcome,
contains a missing, abbreviated, stale, or mismatched runtime review identity, or contains
critical/high findings, the gate must report:

```text
closure_ready: false
erg_005_status: blocked
implementation_planning_allowed: false
trusted_host_promotion_allowed: false
```

## Allowed Closure Readiness Result

For the design-level area, the only readiness result this gate can support is:

```text
ready_for_design_only_decision_record
```

That result does not approve runtime implementation. It means a later committed post-RC decision
record may consider whether to move from blocked status to design-only continuation for
trusted-host promotion planning.

For the runtime area, the only readiness result is:

```text
runtime_source_review_ready_for_triage
```

That result means only that a later committed triage update may disposition the exact deferred
runtime finding records. `ERG-005` remains blocked, and the result does not authorize placement,
release, promotion, UAT, or production use.

## Required Later Triage Update

If the closure gate eventually reports `closure_ready: true`, a separate committed triage update
must still:

- record the raw reviewer response and normalized response path;
- record reviewer label, source access, reviewed commit, and reviewed packet hash;
- add or update the matching `EXT-TRUSTED-HOST-###` or
  `EXT-TRUSTED-HOST-RUNTIME-###` finding files;
- update [enterprise-readiness-gap-matrix.md](enterprise-readiness-gap-matrix.md);
- update [post-rc-decision-register.md](post-rc-decision-register.md);
- update [enterprise-sandbox-control-plane-readiness.md](enterprise-sandbox-control-plane-readiness.md);
- preserve implementation status as design-only unless a later implementation sprint is explicitly
  approved;
- rerun `make release-check`;
- rerun `make review-candidate`.

## Boundaries That Remain Blocked

This closure gate must not approve:

- implementation planning;
- runtime implementation;
- trusted-host promotion;
- direct host writes;
- overwrite/delete/move behavior;
- broad archive extraction;
- automatic promotion;
- promotion without exact artifact hash binding;
- promotion without approval evidence;
- Mission Control runtime behavior;
- local model invocation;
- VM/container lifecycle management;
- sandbox orchestration;
- SIEM adapter behavior;
- production identity;
- runtime Postgres;
- hosted telemetry;
- remote MCP;
- compliance automation;
- new governed tool powers;
- public/security-product positioning.
