# Trusted-Host Promotion Governance-Binding Internal Review

Status: `implementation_candidate_ready_for_independent_re_review`.

Current response-intake state: `runtime_source_review_ready_for_triage`.

Review date: `2026-07-18`.

Implementation candidate reviewed: `cc6ec9dd6808907efb5455d67f1f06477d7c4b92`.

Finding namespace: `EXT-TRUSTED-HOST-RUNTIME-###`.

This record closes the internal source-review portion of `TGB-006`. It does not record external
review, normalize an external response, close `EXT-TRUSTED-HOST-RUNTIME-002` or
`EXT-TRUSTED-HOST-RUNTIME-006`, authorize broad host promotion, approve release, or replace later
operator UAT.

## Scope Reviewed

The main implementation owner and an independent read-only Sol xhigh reviewer inspected the
staging-only trusted-host promotion slice across:

- server-derived requester, approver, and executor identity;
- complete `Admin` plus `Approver` decision authority without changing generic Admin
  authentication;
- principal, workspace, sandbox, trusted-host, policy, manifest, schema, runtime-candidate, and
  approval binding and drift handling;
- version-2 migration, downgrade denial, restart behavior, transaction boundaries, replay, and
  concurrency;
- descriptor-relative, create-exclusive single-artifact placement and source-object validation;
- audit completion ordering, terminal stale/recovery states, diagnostics, safe errors, and UI
  consumption;
- the ten-row observed governance-drift matrix; and
- exact-candidate packet freshness, bundle equivalence, closed inventory, evidence semantics, and
  redaction.

No Sol Ultra review was requested or run.

## Findings And Remediation

### EXT-TRUSTED-HOST-RUNTIME-009

The first exact-candidate review found a high-severity decision-authority defect: a server-derived
principal with `Admin` and `Auditor`, but without the required `Approver` role, could approve and
complete placement. The remediation now enforces the complete role set before trusted-host approve
and deny transitions, at production readiness, and again at apply time. The negative proof shows
the approval remains pending, no attempt is recorded, and no staging effect occurs. Generic Admin
authentication remains separately bounded to `Admin`.

Disposition: `fixed` and independently rechecked on the implementation candidate.

### EXT-TRUSTED-HOST-RUNTIME-010

The next review found that the public packet checker could accept an internally rehashed but altered
source bundle or incomplete runtime inventory. Follow-up review then found ambiguous duplicate JSON
members and duplicate index labels were still accepted. The final checker requires bundle-to-HEAD
byte equality, the exact ordered runtime inventory and count, fixed candidate and detached review
semantics, recursive duplicate-key rejection for packet JSON, unique canonical index/commit labels,
and candidate/index digest agreement.

Observed regressions now reject:

- a bundled required-role weakening with refreshed artifact hashes;
- an omitted runtime inventory path with recomputed candidate and review digests;
- conflicting duplicate `review_scope` and `release_artifact_domain` JSON members;
- a conflicting duplicate candidate-inventory digest label; and
- a duplicate reviewed-commit marker.

Disposition: `fixed` and independently rechecked on the implementation candidate.

## Validation Evidence

- Full Python suite: `1331 passed`.
- UI suite: `53 passed`.
- Policy parity: `24/24 passed`.
- Governed tool count: `24`.
- `make lint`: passed.
- `make typecheck`: passed.
- `make release-check`: passed with recorded `returncode=0`.
- `make review-candidate`: passed.
- Exact runtime-focused packet suite: `104 passed`.
- Packet regression cases used by final re-review: `9 passed`.
- Packet artifact hashes: match.
- Packet bundle-to-HEAD equivalence: valid.
- Candidate digest and closed inventory: valid with `103` paths.
- Candidate index evidence: valid.
- Packet redaction scan: `0` findings.
- Governed power expansion: none.

The packet generated after this review record is committed must be checked again against its own
exact clean commit. That packet refresh proves final record/packet identity; it does not convert this
internal review into external response intake.

## Independent Re-Review Addendum

Independent Sol xhigh packet-and-source re-review of exact clean commit
`919858e8d5886129d7c1fefc730795380cd45f73` and focused packet manifest
`sha256:02b060bb65d41b317b3a426cd1ad9786d101683303622cb9eedb34436bb9ed16` reported no
new findings in the requested remediation scope and dispositioned
`EXT-TRUSTED-HOST-RUNTIME-002` and `EXT-TRUSTED-HOST-RUNTIME-006` as `fixed`.

The normalized response passed the exact runtime closure preflight with
`disposition_outcome: runtime_findings_closed` and
`runtime_source_review_status: runtime_source_review_ready_for_triage`. The preflight kept
`ERG-005` blocked and every runtime, promotion, host-write, release, UAT, and new-power authority
false. This addendum records independent source-finding disposition; it does not rewrite the
historical internal disposition or claim external enterprise-lane closure.

## Internal Disposition

`TGB-001` through `TGB-006` are internally implemented and evidence-complete for the bounded
staging-only slice. The allowed next state is only:

`implementation_candidate_ready_for_independent_re_review`

The following remain false:

```text
external_review_complete: false
authorization_record_created_for_runtime_candidate: false
trusted_host_promotion_broadly_allowed: false
new_governed_tool_allowed: false
release_approved: false
uat_accepted: false
```

`EXT-TRUSTED-HOST-RUNTIME-002` and `EXT-TRUSTED-HOST-RUNTIME-006` are fixed after exact-candidate
independent response intake. `ERG-005`, trusted-host promotion authority, release approval, and UAT
remain separately blocked.
