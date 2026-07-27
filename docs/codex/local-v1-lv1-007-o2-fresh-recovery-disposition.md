# LV1-007 O2 Fresh-Recovery Disposition

Status: `STOP — fresh recovery attempt failed closed`

- Local-v1 milestone: `LV1-007`
- Release outcome: `O2`
- Attempted candidate: `69de21a2526fa481972188e5624f27e90c4cff29`
- Attempted tree: `a56d40bf8313651216643a415889669396a12467`
- Safe failure: `gateway_o2_evidence_invalid`
- Required-observation bitmap: `110011`
- Bounded audit-event count: `5`
- Milestone status: `not_started`
- Outcome status: `not_started`
- Current progress: `6/8` outcomes and `7/8` milestones complete
- Governed tool count: `24`
- Runtime, release, promotion, production, and UAT authority: `false`
- Second live rehearsal in this fresh recovery task: `not_authorized`

This record follows the earlier repeated-gate disposition at
`docs/codex/local-v1-lv1-007-o2-repeated-live-gate-disposition.md`. The automatic goal continuation
started a new bounded recovery task; it did not retroactively authorize a fourth attempt in the
stopped task. This fresh task authorized and consumed exactly one new live rehearsal.

This failure does not complete `O2`, start `O8`, qualify a Local-v1 candidate, authorize human UAT,
or change the 24-tool and no-arbitrary-host-control boundaries.

## Exact Candidate And Review

Candidate `69de21a2526fa481972188e5624f27e90c4cff29` aligned the rehearsal with the fixed O2 completion
contract:

- one in-scope `fs.read` allowed and completed;
- one out-of-scope `fs.read` denied before any execution lifecycle event;
- one synthetic write classified `require_approval`, with exactly one approval left pending and no
  execution lifecycle event;
- fixed local stdio identity on governed events; and
- a valid authoritative Gateway audit chain.

The removed directory-list and HTTP-denial observations were extra behaviors outside the stated O2
contract. Their removal did not weaken the required allowed, denied, or approval behavior.

The same existing Sol-high reviewer returned `GO` with zero Critical, High, Medium, or Low
findings. The reviewer confirmed that runtime and checker requirements share one observation
definition, denied and pending requests remain disjoint from started, completed, and failed
execution, and the diagnostic projection can emit only six fixed bits plus an integer event count
bounded from zero through one million. No xhigh or Ultra reviewer was used.

Focused validation passed before the run: `20` tests, Ruff, strict mypy, the Local-v1 contract
check, docs-site tests, and exact diff/cleanliness checks. The known non-failing pytest temporary
cleanup warnings were the only warnings.

## Safe Failure Meaning

The bitmap order is:

1. `allowed_read_completed`
2. `out_of_scope_read_denied_before_execution`
3. `approval_required_observed`
4. `approval_pending_without_execution`
5. `fixed_stdio_identity_observed`
6. `audit_chain_valid`

`110011` therefore proves that the pinned Hermes agent produced the allowed read, the denied
out-of-scope read, fixed identity, and a valid five-event audit chain. It did not invoke the
approval-required write, so the approval-required and approval-pending observations correctly
remained false.

This classification contains no event payload, model output, prompt, fixture content, path,
request, approval, run, container, session, environment, or credential value. The harness discarded
Hermes prose and did not infer the missing write from the requested query.

## Cleanup Verification

The success-only harness retained no report. Independent sanitized queries after the failure
observed:

- zero containers matching the fixed O2 container namespace;
- zero images matching the fixed O2 image namespace;
- zero Local-v1 real-agent success reports; and
- a clean tracked checkout at the attempted candidate.

The exact container, exact candidate image, extracted candidate tree, candidate archive, copied
analysis evidence, and private runtime state were removed before the command returned. There is no
ambiguous live resource or retained private evidence requiring recovery.

## Resume Boundary

A later fresh O2 recovery should not ask one model turn to complete all three activity classes.
Instead, it should use the same pinned Hermes image, fixed stdio identity, confined synthetic
Gateway state, and exact operator-managed lifecycle to execute three fixed single-purpose Hermes
turns in order:

1. allowed in-scope read;
2. denied out-of-scope read; and
3. approval-required synthetic write.

The harness must attempt all three fixed turns even if an earlier runner process exits nonzero.
Each runner exit remains observation only. The combined authoritative Gateway audit must still
prove all six required bits, exactly one pending approval, valid chain, no denied or pending
execution lifecycle, and exact cleanup. The runner must receive no Docker socket, credentials,
ambient state, new tools, generic command surface, or arbitrary host control.

That candidate should receive focused validation and one proportional Sol-high review because the
runner orchestration and audit aggregation change. A later fresh task may authorize at most one new
live rehearsal. It must stop on a Critical/High finding, unsafe diagnostic requirement, cleanup
ambiguity, product-boundary expansion, or its own repeated-gate condition.
