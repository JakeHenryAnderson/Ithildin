# Ithildin Local v1.0 Completion Contract

Status: active fixed-scope delivery contract.

- Active delivery target: `Ithildin Local v1.0`
- Current governed tool count: `24`
- Release outcomes complete: `6/8`
- Critical-path milestones complete: `7/8`
- Latest completed milestone: `LV1-006`
- Active next action: `LV1-007`
- Local-v1 release gate: `blocked`
- Human UAT: `not_started`
- Release acceptance: `false`

This is the authoritative product-control surface for Local v1.0. Outcome counts, not percentage
bands, are the active delivery forecast. Historical enterprise estimates and artifacts remain
lineage, but they do not set the Local-v1 critical path.

Recording or validating this contract does not authorize runtime execution, a new governed power,
release, promotion, external-system action, credential custody, or UAT completion.

## Product Definition

Ithildin Local v1.0 is a self-hosted, single-operator governance gateway and operations cockpit for
a technically capable, security-conscious user. It lets configured local agents use Ithildin's
bounded 24-tool surface, mediates their governed activity, authenticates an optional local Node,
preserves approvals and reviewable evidence, and fails closed across restart, replay, and partition
conditions. It does not sandbox the host, control arbitrary processes, or prove that an agent
cannot act outside Ithildin.

The trust ceiling is activity mediated through Ithildin. Gateway policy, approval, execution, and
audit remain authoritative. Node connectivity, runner-reported state, and model-provider state are
separate observations and must not overwrite Gateway truth.

## Fixed Release Outcomes

An outcome is `complete` only when its operator-visible acceptance evidence is bound to the
candidate being evaluated. Existing component evidence may inform a milestone without closing an
integrated outcome.

| ID | Outcome | Status | Done when |
| --- | --- | --- | --- |
| `O1` | Fresh local installation | `complete` | From documented prerequisites, an operator initializes isolated local state, starts Gateway and Command Center, verifies health, and stops cleanly without using undocumented review machinery. |
| `O2` | Real agent connection | `not_started` | A pinned operator-managed agent uses the existing MCP surface and the operator can distinguish allowed, denied, and approval-required activity. |
| `O3` | Authenticated Node | `complete` | One optional local Node enrolls with a one-time code, receives Gateway-derived identity and workspace assignment, consumes signed configuration, reports bounded connectivity, and can be revoked. |
| `O4` | One real constrained mission | `complete` | A server-owned mission reaches an operator-managed runner through the authenticated Node path and performs a governed operation with server-derived identity and workspace boundaries. |
| `O5` | Failure and recovery scenario | `complete` | One coherent scenario demonstrates restart continuity, replay rejection, partition failure, revocation, stale-configuration rejection, and documented manual rollback. |
| `O6` | Perceivable Command Center | `complete` | A first-time operator can find the mission, understand what happened and why, inspect approval/evidence, and distinguish Gateway, Node, runner, and model-provider truth with accessible interaction. |
| `O7` | Local operations | `complete` | Backup/restore, update/rollback, recovery-required behavior, diagnostics, ports, data ownership, and cleanup are documented and exercised for the supported local topology. |
| `O8` | Exact-candidate review and human UAT | `not_started` | One frozen candidate passes the dedicated Local-v1 gate and independent high-effort review, then a human operator completes the golden scenario and explicitly records acceptance or findings. |

## Golden Scenario

The final Local-v1 candidate must support this repeatable operator journey:

1. Start from documented local prerequisites and initialize isolated Ithildin state.
2. Start Gateway and Command Center, verify health, and identify the trusted local boundary.
3. Connect a pinned real MCP agent and observe allowed, denied, and approval-required activity.
4. Enroll an optional Node with Gateway-derived identity, signed configuration, and bounded
   workspace assignment.
5. Admit and claim one server-owned mission, perform one governed operation, and inspect the
   resulting mission, approval, audit, and evidence views.
6. Demonstrate restart, replay, temporary partition, revocation, stale-configuration, and rollback
   behavior without converting runner or provider reports into Gateway truth.
7. Export bounded evidence, perform the documented backup/update/restore-or-rollback procedure,
   then stop and clean up safely.

At `LV1-001`, the real Hermes MCP leg and the authenticated Node/Mission Command leg may be composed
as explicitly separate existing demonstrations. That milestone must not claim a real
Hermes-through-Node mission. `O4` cannot close until the bounded runner seam is separately
authorized, implemented, and evidenced.

## Fixed Critical Path

| Milestone | Scope | Status | Exit |
| --- | --- | --- | --- |
| `LV1-000` | Product-control pivot | `complete` | This contract, navigation, count-based status, fail-closed Local-v1 gate topology, disposition binding, and drift tests pass exact independent review. No release outcome closes. |
| `LV1-001` | Golden local path assembly | `complete` | Assemble a reproducible operator-facing install/start/exercise/evidence/stop path from existing Gateway, UI, real Hermes MCP, and synthetic authenticated Node/Mission Command parts while preserving their truth separation. |
| `LV1-002` | Authenticated Node journey | `complete` | Close the enrollment, signed-configuration, identity, connectivity, and revocation experience required by `O3`. |
| `LV1-003` | Real constrained mission seam | `complete` | Make and review the bounded capability decision required before implementing the smallest fixed runner bridge and closing `O4`. |
| `LV1-004` | Failure and recovery | `complete` | Bind the integrated restart/replay/partition/revocation/stale-configuration/rollback scenario required by `O5`. |
| `LV1-005` | Command Center comprehension | `complete` | Close the golden-path information architecture, truth-source separation, evidence navigation, and accessibility criteria required by `O6`. |
| `LV1-006` | Local operations | `complete` | Close installation hardening, backup/restore, update/rollback, diagnostics, data ownership, and cleanup required by `O1` and `O7`. |
| `LV1-007` | Candidate freeze and UAT | `not_started` | Close remaining outcomes, freeze an exact candidate, run the dedicated release gate and independent review, then stop for genuine human UAT and an explicit release decision. |

The exact `LV1-000` candidate
`bb306a0e3698fb19293061c2760f9781cc6de395` received an independent Sol xhigh `GO` with zero
Critical, High, Medium, or Low findings. The durable disposition is
`docs/codex/local-v1-lv1-000-exact-review.md`.

The exact `LV1-001` candidate
`1e5f02b762022b305e69c7223a21092e06b49b13` received an independent Sol high `GO` with zero
Critical, High, Medium, or Low findings. The durable disposition is
`docs/codex/local-v1-lv1-001-exact-review.md`. Completing this assembly milestone does not assert
that a human operator has executed the walkthrough or close a release outcome.

`LV1-002` and `O3` are complete. Exact runtime-evidence candidate
`fabdba7ee81d4ecca4353559dd109ff0008d8091` passed the bounded synthetic authenticated Node journey
and its success-only checker. Independent Sol xhigh review returned `GO` with zero Critical, High,
Medium, or Low findings. The durable review and evidence binding is
`docs/codex/local-v1-lv1-002-exact-review.md`.
The deliberate live journey reached the repository's repeated-gate stop condition at exact
candidate `f1fd02821706af691c0c933457f9fb6e5ce05af5`; see
`docs/codex/local-v1-lv1-002-repeated-live-gate-disposition.md`. A fourth attempt is not authorized
in that recovery sprint.
The subsequently resumed fresh recovery added exact-reviewed closed diagnostics and authorized one
new local-only retry at candidate `7f7b5fde932fd678afd465924e7dcbe936fbcfb2`. That retry failed
closed before enrollment with only the authenticated system-status probe invalid; cleanup completed
and all authority remained false. See
`docs/codex/local-v1-lv1-002-fresh-recovery-disposition.md`. No additional retry was authorized in
that recovery task. The subsequent bounded projection-and-review recovery produced the successful
exact run above. Those failed-attempt stop lines remain historical evidence; they did not authorize
or prove the later successful run. No additional LV1-002 retry is needed or justified.

`LV1-003` and `O4` are complete. Exact consumed-success candidate
`cd267b4454af3e28f71d0f7c2e065d6e28c2d55c` produced the separately checked, digest-safe
integrated mission evidence bound by
`docs/codex/local-v1-lv1-003-o4-attempt-021-disposition.md`. Gateway lifecycle truth is
`runner_reported_succeeded`; runner state remains `runner_reported_only`; model-provider state is
unknown. This closes only O4/LV1-003 and grants no release, production, UAT, or successor authority.
`LV1-004` and `O5` are complete. Exact evidence candidate
`b77d53562229026e932ec554fda5caca84c9642e` passed the integrated isolated loopback journey and
its no-follow, candidate-bound checker. The digest-only evidence binding is
`docs/codex/local-v1-lv1-004-disposition.md`. Restart continuity, replay rejection, partition
failure, revocation, stale-configuration rejection, and manual rollback all passed.
Configuration remains `stored_not_enforced`; runner state remains `runner_reported_only`; model-
provider state remains unknown. The earlier reviewed trust-boundary candidate received independent
Sol-high `GO` with zero findings; the final candidate adds only the tested regular-file probe repair
needed after the first checker invocation exposed a permission-bit classification bug. That first
run is not claimed as passing evidence. All live execution authority remains false. The ordered
next milestone is `LV1-005`; no release, promotion, production, or UAT authority is granted.

`LV1-005` and `O6` are complete. Exact implementation candidate
`6f33c4bb715a23b16e3894c1d22e5fb5c4c5b813` adds a keyboard-accessible first-time-operator path
from selected mission context through recorded decision and reason, matching approval, evidence
closeout, and the separate Gateway, Node, runner, and model-provider truth sources. The durable
candidate binding and proportional validation record is
`docs/codex/local-v1-lv1-005-disposition.md`. This presentation-only change adds no API, mutation,
runtime behavior, governed power, or tool. Automated interaction evidence is not human UAT or an
accessibility certification. The ordered next milestone is `LV1-006`; all release, production,
promotion, external-system, and UAT authority remains false.

`LV1-006`, `O1`, and `O7` are complete. Exact evidence candidate
`0c9fd49c2124b0d642bf07fbfa4a1aaa769dc950` passed the isolated loopback-only install,
health, clean-stop, stopped-backup, fixed failed-update, fresh-directory restore, recovered-health,
owner-only-state, and exact-cleanup rehearsal. Its candidate-bound checker passed against the sole
mode-`0600` safe report. One reused Sol-high reviewer returned final `GO` with zero findings after
the bounded repair lineage; no xhigh reviewer was used. The durable digest-only binding is
`docs/codex/local-v1-lv1-006-disposition.md`. The optional Node and model provider were excluded,
all authority remains false, and the tool count remains 24. The ordered next milestone is
`LV1-007`; this evidence is not release acceptance, production durability, or human UAT.

The first bounded `LV1-007` O2 recovery task reached the repository's repeated-live-gate stop
condition after three exact-candidate rehearsals. The final candidate
`00473f8a8e7ad16b15733a7476948c78646ea26f` failed closed at
`gateway_o2_evidence_invalid`; exact cleanup completed and no success report was retained. `O2` and
`LV1-007` remain `not_started`, no fourth attempt is authorized in that task, and all authority
remains false. The durable safe disposition is
`docs/codex/local-v1-lv1-007-o2-repeated-live-gate-disposition.md`.

The next automatic goal continuation started one fresh bounded O2 recovery and consumed exactly one
new rehearsal on reviewed candidate `69de21a2526fa481972188e5624f27e90c4cff29`. The safe Gateway
bitmap `110011` proved the allowed read, denied-before-execution read, fixed stdio identity, and
valid audit chain, but Hermes did not invoke the approval-required write. Cleanup completed, no
success report was retained, and no second rehearsal is authorized in that fresh recovery task.
`O2` and `LV1-007` remain `not_started`; all authority remains false. The durable disposition is
`docs/codex/local-v1-lv1-007-o2-fresh-recovery-disposition.md`.

Historical `LV1-003` lineage follows.
`MCC-007` exact reviewed candidate is authorized for code use only. Independent Sol xhigh review of
candidate `da5fd021bddb48ad663aa0a409da036bc854b516` returned `GO` with zero Critical, High, Medium,
or Low findings after the complete remediation lineage recorded in
`docs/codex/local-v1-lv1-003-exact-review.md`. The candidate-bound authorization is
`docs/codex/mission-command-runner-bridge-authorization-record.md`. The now-consumed execution gate
is `docs/codex/local-v1-lv1-003-o4-execution-authorization.md`; its budget is zero and all live
authority is false.

The current implementation candidate is
`docs/codex/local-v1-golden-path.md`, validated by `make local-v1-golden-path-check`. Its two
operator-visible legs remain explicitly separate, so assembling and validating the walkthrough does
not itself complete another outcome or milestone. `O4`/`LV1-003` closure comes only from the
separate Attempt 021 disposition.

## Explicitly Deferred From Local v1.0

- production PostgreSQL, production identity, enterprise tenancy, and multi-user RBAC;
- production credential, hosted trust, or signing-key custody;
- hosted or remote-operation claims;
- managed fleet rollout or Node self-update;
- SIEM custody integrations, compliance automation, or compliance claims;
- VM/container lifecycle management or sandbox orchestration;
- filesystem non-bypass, host-compromise prevention, or whole-host isolation claims;
- arbitrary shell, process, browser, network, or broad filesystem authority;
- Kubernetes or Docker-socket control;
- `ERG-009`, PIS completion, enterprise completion, and public security-product claims.

The PIS external target and signed-receipt wait remains valid enterprise lineage, but it does not
block Local v1.0. No Local-v1 outcome may imply that the deferred PIS or enterprise work occurred.

## Scope And Authority Control

Proposed work must be classified as `required_for_local_v1`, `post_v1`, `optional`, or
`externally_blocked`. Only `required_for_local_v1` work may enter this critical path.

A scope change must identify the affected outcome, the missing operator behavior or trust-boundary
proof, the smallest proposed change, validation impact, and what will be removed or deferred to keep
the release finite. Changing the eight-outcome denominator, the 24-tool surface, a governed power
class, or the authority ceiling requires a separately reviewed product/capability decision and
explicit user direction. Discovery alone does not expand the release.

All runtime, release, promotion, credential-custody, external-system, and UAT authorities remain
false unless their separate gate is satisfied. Tests and generated evidence prove only what they
observe; they do not grant those authorities.

## Release Disposition Evidence

`docs/codex/local-v1-release-disposition.json` is the sole machine-readable release disposition
record. Status prose cannot qualify a candidate or authorize release. Its evidence and authority
fields begin false or null and must ultimately bind:

- the frozen candidate commit and a candidate-bound clean-tree identity observation;
- the candidate-gate transcript path, SHA-256 digest, successful return code, and candidate commit;
- an independent `GO` review record, exact reviewed candidate, digest, and finding counts;
- a genuine human UAT result, tested candidate, record, and digest;
- explicit human acceptance of that same candidate, with a record and digest; and
- the exact declared commit lineage between the frozen candidate and the disposition parent.

The disposition parent is the immediate parent of the commit carrying the final record, avoiding
an impossible self-referential commit hash. Every intervening candidate descendant must be declared
exactly once as a candidate-gate, independent-review, human-UAT, or human-acceptance record. The
validator compares that declaration to Git ancestry and rejects undeclared descendants. Candidate
cleanliness is historical evidence bound through the candidate-gate transcript; the disposition
record does not pretend that a later worktree observation proves the earlier candidate was clean.
Declared evidence descendants may change only `docs/codex/local-v1-*` records. The final
disposition commit must directly follow the declared parent, may change only this contract and the
JSON disposition, and is validated from a clean current checkout.

## Validation Topology

- Inner loop: `make local-v1-inner-check` validates this contract, its focused tests, the manifest
  lock, exact 24-tool surface, and no-new-powers guardrail.
- Milestone checkpoint: `make local-v1-milestone-check` adds agent-workflow, release-readiness
  wiring, the focused `make local-v1-golden-path-check`, and docs-site checks. Run it after a
  coherent Local-v1 batch.
- Candidate tier: after `O1`-`O7` are complete and the frozen candidate moves `O8` into progress,
  `make local-v1-candidate-check` requires a clean checkout, emits exact candidate markers, runs the
  milestone gate, and executes a fixed target inventory. The inventory explicitly covers policy,
  auth, approval, audit, redaction, security, migrations, hardening, Node evidence, Mission Command
  evidence and focused gates, the Hermes evidence path, UI accessibility tests, the production UI
  build, docs, exact tool count, and no-new-powers checks. Evidence checkers do not reproduce live
  evidence; the live POC commands are intentionally absent. Passing it is candidate evidence only.
- Release tier: `make local-v1-release-check` validates the current milestone wiring and the bound
  historical candidate disposition; it does not rerun candidate qualification against a later
  disposition commit. It is intentionally fail-closed until all eight outcomes, genuine human UAT,
  and explicit release acceptance are recorded.
- Full governance integrity: `make release-check` remains the broad historical/enterprise gate.
  Run it only for deliberate full-integrity checkpoints or changes to that governance surface.

While any required outcome remains incomplete, a nonzero `make local-v1-release-check` result is
expected. It must not be relabeled as release proof, UAT readiness, or acceptance.
