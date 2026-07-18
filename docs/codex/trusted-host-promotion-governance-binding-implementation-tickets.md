# Trusted-Host Promotion Governance-Binding Implementation Tickets

Status: approved bounded execution packet for `PRD-TRUSTED-HOST-BINDING-001`.

Current governed tool count: `24`.

Current product boundary: one-artifact, create-exclusive, Manager-local host-staging placement.

Current decision status: `approved_for_bounded_implementation`.

Run:

```sh
make trusted-host-promotion-governance-binding-implementation-tickets-check
```

This packet converts the reviewed architecture in
`docs/codex/trusted-host-promotion-governance-binding-architecture.md` into six bounded implementation
tickets. It names current source anchors, proposed file ownership, sequencing, acceptance evidence,
and stop conditions. Its bound authorization record permits the public-contract, database, policy,
persistence, and placement implementation changes required by those tickets. It does not itself
change runtime behavior, enable the live promotion route, close `EXT-TRUSTED-HOST-RUNTIME-002`,
close `EXT-TRUSTED-HOST-RUNTIME-006`, or close `ERG-005`.

## Authorization Scope

The direct user instruction recorded on `2026-07-18`, together with the standing project authority
in `AGENTS.md`, authorizes tickets `TGB-001` through `TGB-006` in order. The user does not need to
repeat a technical approval formula for changes already bounded by this architecture and ticket
packet.

Authorization is limited to these tickets. It does not authorize a new
MCP tool, a new API route, Node-side placement, runner control, arbitrary host writes, production
identity, runtime Postgres, OPA-backed promotion, SIEM delivery, or public security-product claims.
The live trusted-host promotion route remains unavailable until the `TGB-005` gates pass.

## Current Source Baseline

These are observed current-state facts at planning commit `31f85dc`; they identify the intended
change points but are not defects newly discovered by this packet:

| Boundary | Current source anchor | Required version-2 outcome |
| --- | --- | --- |
| Admin authentication | `ithildin_api.auth.require_admin_token` validates the bearer and returns `None` | return a server-derived `AdminPrincipalContext` resolved from the enabled `admin:local-ui` registry record |
| Proposal identity | `TrustedHostPromotionProposalInput.principal` accepts caller JSON | remove the field and reject it as unknown input |
| Approval attribution | `ApprovalDecisionPayload.decided_by`, `ApprovalService.approve`, and `ApprovalService.deny` accept caller attribution | derive requester, approver, and executor from authenticated server context |
| UI approval consumer | `App.tsx::decideApproval` sends `decided_by: DECIDED_BY` | send only decision and bounded optional reason |
| Approval persistence | `ApprovalStore.initialize` creates an unversioned `approvals` table | rebuild versioned approval storage with decision hash and conditional status constraints |
| Promotion persistence | `TrustedHostPromotionStore.initialize` creates proposal and attempt tables independently | migrate proposal, approval, and attempt tables in one transaction and coordinate reservations in one database transaction |
| Policy | `TrustedHostPromotionService` has no `PolicyEngine` dependency | require the canonical YAML engine and bind a `require_approval` decision for internal action `trusted_host.promotion.stage` |
| Authority evidence | proposal scope binds artifact and sandbox descriptor facts only | bind the canonical `PromotionAuthoritySnapshot` across proposal, approval, attempt, audit, and diagnostics |
| Runtime candidate | no reviewed installed-file verifier gates promotion | require a detached, acyclic reviewed inventory and fail closed as `unreviewed_local` otherwise |
| Destination placement | `_destination_for` and `_copy_without_overwrite` operate on paths | use descriptor-relative, no-follow, create-exclusive placement anchored to retained directory descriptors |

The implementation owner must refresh this baseline before editing. If any anchor has moved or its
semantics have changed, update the ticket packet first or stop for architecture review; do not
silently reinterpret the ticket.

## Ownership And Commit Discipline

- One Sol implementation owner holds all runtime edits and integration decisions.
- A read-only Sol high/xhigh reviewer may inspect trust-boundary slices after focused tests.
- Luna/Terra implementers may only suggest mechanical fixture, inventory, or documentation changes;
  they do not edit runtime authority, policy, migration, approval, or placement code.
- Sol Ultra is not used without the user's prior approval.
- Each ticket lands as a separately reviewable commit. A ticket may depend on earlier commits, but it
  must not opportunistically begin the next ticket.
- Promotion stays disabled until `TGB-005` is complete and independently reviewed. Passing model,
  schema, migration, policy, or placement tests alone never enables production-route placement.
- No ticket changes `tool-manifests.lock.json`, any governed tool manifest, `apps/node/`, the MCP
  server, runner launch/control, or model-provider behavior.

## Dependency Graph

```text
TGB-001 authority foundation and verified candidate
  -> TGB-002 version-2 contracts and migration
    -> TGB-003 policy and approval binding
      -> TGB-004 atomic revalidation and descriptor-relative placement
        -> TGB-005 evidence, diagnostics, and UI consumer
          -> TGB-006 adversarial proof and exact-candidate source review
```

No ticket may be skipped. `TGB-006` is evidence and review, not a substitute for any implementation
slice.

## TGB-001 — Authority Foundation And Verified Candidate

### Objective

Introduce closed, immutable authority models and startup-only registries without changing public
request shapes, database schemas, approval semantics, or filesystem placement logic. As the first
approved implementation action, proposal/apply must fail closed while the version-2 binding is
incomplete; promotion remains disabled through `TGB-003`.

### Owned existing files

- `apps/api/src/ithildin_api/auth.py`
- `apps/api/src/ithildin_api/identity.py`
- `apps/api/src/ithildin_api/workspaces.py`
- `apps/api/src/ithildin_api/sandbox_descriptors.py`
- `apps/api/src/ithildin_api/config.py`
- `apps/api/src/ithildin_api/app.py`
- `principals/local.yaml`
- `workspaces/local.yaml`
- `.dockerignore`
- `.gitignore`
- `deploy/Dockerfile.api`
- `deploy/docker-compose.yml`
- `deploy/README.md`
- `tests/test_identity.py`
- `tests/test_workspaces.py`
- `tests/test_api_service.py`

### Proposed new files

- `apps/api/src/ithildin_api/promotion_authority.py`
- `apps/api/src/ithildin_api/trusted_host_registry.py`
- `apps/api/runtime_candidate_bootstrap.py`
- `apps/api/verified_launch.py`
- `schemas/runtime-candidate-authorization.schema.json`
- `scripts/runtime_candidate_authorization_record.py`
- `trusted-hosts/local.yaml`
- `tests/test_promotion_authority.py`
- `tests/test_trusted_host_registry.py`
- `tests/test_runtime_candidate_bootstrap.py`

### Required changes

1. Add immutable `AdminPrincipalContext`, workspace/sandbox/host authority records,
   `RuntimeCandidateRecord`, and `PromotionAuthoritySnapshot` with canonical JSON hashing.
2. Introduce an internal version-2 readiness state that is false until `TGB-005` constructs every
   reviewed dependency. Proposal/apply return one safe unavailable reason and cause no approval,
   database, audit-completion, or filesystem effect while false. This is not an operator-controlled
   environment bypass.
3. Make the admin dependency resolve exactly one enabled `admin:local-ui` record, require `Admin`,
   and return a context containing a canonical principal-registry generation digest. Do not change
   route request bodies in this ticket.
4. Add a read-only `TrustedHostDescriptorRegistry` with schema version `2`, duplicate/unknown-field
   rejection, one workspace and staging-label resolution path, and no mutation API.
5. Add stable workspace-record and sandbox-descriptor hashes/generations using existing registry and
   descriptor stores; never expose roots or raw payloads.
6. Add detached runtime-candidate inventory domains:
   - reviewed inventory digest over canonical relative paths and file digests;
   - dependency-lock digest over `uv.lock`;
   - release-artifact digest over the immutable package/image input domain;
   - candidate ID over source commit plus those core digests and schema versions;
   - review-packet digest generated later over a packet that names the candidate ID.
7. `apps/api/verified_launch.py` must run the stdlib-only bootstrap verifier before importing `ithildin_api.app`
   or Uvicorn application code. The verified result is passed in memory to app
   construction; an environment value or unverified metadata file cannot assert reviewed posture.
8. Add a detached operator authorization record with closed schema fields for authorization ID,
   candidate ID, reviewed commit, inventory schema/digest, dependency-lock digest, release-artifact
   digest, review-packet digest, authorized-at timestamp, and record hash. The record is generated
   only by the post-review operator promotion command and is not copied into the candidate image.
9. Add `Settings.runtime_candidate_authorization_path`. Compose mounts the operator-created record
   from gitignored and Docker-build-excluded `runtime-authority/` to
   `/run/ithildin-authority/api-candidate.json:ro`. An environment value may select that path but may
   not provide, override, or bypass any identity/digest/authorization field. Bootstrap validates the
   closed record, file ownership/mode, read-only runtime posture, record hash, and equality with the
   independently verified candidate before making reviewed posture available in memory.
10. `scripts/runtime_candidate_authorization_record.py` consumes the exact reviewed packet and
    candidate manifest, validates their hashes, and writes the detached record only after an explicit
    operator `--authorize` action. It cannot run in the container entrypoint, cannot authorize a
    dirty candidate, and cannot read candidate claims as authorization.
11. Direct source-checkout startup remains supported as `unreviewed_local`, but trusted-host
   promotion stays unavailable outside explicit test fixtures.
12. Version the local descriptor fixture and document why `host_write_allowed: false` coexists with
   the single `staging_create_exclusive_allowed: true` permission.

### Focused acceptance evidence

- Canonicalization is deterministic across key order and rejects unknown/missing fields, duplicate
  rules, duplicate obligations, malformed hashes, and tool counts other than `24`.
- Disabled/missing/non-admin local principals fail authentication without creating a proposal.
- Duplicate, wrong-workspace, disabled, unsafe, or raw-path trusted-host descriptors fail closed.
- Candidate inventory, dependency lock, release artifact, candidate metadata, and packet digests
  cannot form a hash cycle.
- Missing, malformed, self-authored, image-baked, writable, wrong-owner, stale, dirty-candidate,
  packet-mismatched, environment-only, and path-substituted authorization records fail promotion
  closed.
- A launcher-order test proves the verifier completes before `ithildin_api.app` enters
  `sys.modules`.
- Direct `uvicorn ithildin_api.app:app` posture reports `unreviewed_local` and cannot promote.
- Proposal/apply during `TGB-001` through `TGB-003` return the safe incomplete-binding reason and
  create no approval, promotion row, attempt, completion event, or staging-root effect.

### Validation

```sh
uv run pytest tests/test_identity.py tests/test_workspaces.py \
  tests/test_promotion_authority.py tests/test_trusted_host_registry.py \
  tests/test_runtime_candidate_bootstrap.py -q
make lint
make typecheck
make tool-surface-invariant-gate
make no-new-powers-guardrail
```

### Stop conditions

Stop if candidate verification requires secrets, code signing claims, remote attestation, mutable
host registration, package-root writes by the runtime, a dependency, or weakening direct-source
startup semantics outside promotion availability.

## TGB-002 — Version-2 Contracts And Transactional Migration

### Objective

Remove caller-controlled identity/approval attribution and migrate proposal, approval, and attempt
storage atomically while placement remains disabled.

### Owned existing files

- `apps/api/src/ithildin_api/app.py`
- `apps/api/src/ithildin_api/approvals.py`
- `apps/api/src/ithildin_api/database.py`
- `apps/api/src/ithildin_api/trusted_host_promotions.py`
- `packages/schemas/src/ithildin_schemas/models.py`
- `apps/ui/src/App.tsx`
- `apps/ui/src/App.test.tsx`
- `tests/test_api_service.py`
- `tests/test_approval_workflow.py`
- `tests/test_core_schemas.py`
- `tests/test_governed_tool_calls.py`
- `tests/test_mcp_integration_flow.py`
- `tests/test_security_regressions.py`

### Proposed new files

- `apps/api/src/ithildin_api/trusted_host_promotion_v2_migration.py`
- `tests/test_trusted_host_promotion_v2_migration.py`
- `scripts/trusted_host_promotion_v2_downgrade_evidence.py`

### Required changes

1. Remove `principal` from `TrustedHostPromotionProposalInput`. Strict unknown-field rejection must
   make every legacy principal payload a `400`.
2. Inject `AdminPrincipalContext` into proposal and apply routes and service calls. Persist requester,
   approver, and executor as distinct server-derived principal IDs/generations.
3. Remove `decided_by` from `ApprovalDecisionPayload` and UI request bodies. Reject, rather than
   ignore, legacy attribution fields. Update approve and deny service entry points to require the
   authenticated context.
4. Rebuild proposal, approval, and attempt tables in one `BEGIN IMMEDIATE` migration transaction.
   Store a non-null approval-contract version for every new approval, require non-null promotion
   authority/request bindings when `tool_name` is `trusted_host.promotion.stage`, retain readable
   historical rows, and add a schema/minimum-writer record. Other approval types keep their existing
   one-time-scope semantics and must not receive a fabricated promotion-authority hash.
5. Use conditional table constraints: every migrated status uses a closed `legacy_*` vocabulary that
   the previous `ApprovalStatus`/promotion implementation cannot parse, and every new row uses only
   the closed `v2_*` vocabulary. API serializers may map both to bounded display labels. All new
   approval decisions use the version-2 server-derived attribution contract, including approvals for
   patch apply and other existing consumers.
6. Add approval decision time, bounded reason hash, server-derived deciding principal generation,
   authority snapshot hash, and `decision_hash`. Decision text remains bounded; raw reason text must
   not enter audit metadata.
7. Mark every pre-version-2 nonterminal proposal `legacy_unbound`; it cannot be applied, retried,
   upgraded, or rebound.
8. Replace independent startup initialization with one migration coordinator before either store is
   used. Replace `database.initialize_database`'s unconditional schema-version overwrite with a
   compare/upgrade/minimum-writer contract that rejects newer or unsupported schemas. Interrupted
   migration must roll back without a mixed schema.
9. Keep placement unavailable throughout this ticket even when a v2 approval is approved.
10. Extend shared approval response models and schema tests with safe decision attribution/hash
    fields. Update direct approval users in governed tool calls, MCP integration, API routes, and UI
    to construct authenticated principal contexts; no string-attribution compatibility overload is
    allowed.

### Previous-binary downgrade proof

- Record the exact pre-migration implementation baseline commit in the approved decision record.
- Unit tests use a frozen version-1 writer fixture whose source hash is bound to that baseline.
- The release evidence script builds or loads the previous API artifact, opens a migrated database,
  and attempts proposal insertion, approve, deny, apply, and attempt creation against both migrated
  legacy nonterminal rows and newly created version-2 rows.
- Every old-writer mutation must fail. Every old apply path must stop before any staging-root
  filesystem effect.
- Rollback to the previous binary remains disabled unless this evidence passes against the exact
  migrated schema.

### Focused acceptance evidence

- API and UI tests prove `principal` and `decided_by` are absent and rejected if supplied.
- Patch-apply and every other approval consumer still approve/deny with server-derived attribution.
- Migration covers empty, legacy pending, legacy completed, v2, interrupted, restart, and corrupt
  database fixtures.
- A previous binary cannot write a legacy status onto a version-2 row.
- The migration never synthesizes an authority snapshot for historical rows.

### Validation

```sh
uv run pytest tests/test_core_schemas.py tests/test_approval_workflow.py \
  tests/test_governed_tool_calls.py tests/test_mcp_integration_flow.py \
  tests/test_security_regressions.py tests/test_trusted_host_promotion_v2_migration.py \
  tests/test_api_service.py -q
npm run test --prefix apps/ui
uv run python scripts/trusted_host_promotion_v2_downgrade_evidence.py
make lint
make typecheck
```

### Stop conditions

Stop on data loss, a non-atomic mixed schema, previous-binary mutation success, an approval consumer
that cannot derive identity, or a required compatibility mode that accepts caller attribution.

## TGB-003 — YAML Policy And Approval-Scope Binding

### Objective

Construct and persist one complete `PromotionAuthoritySnapshot`, evaluate the internal staging action
through canonical YAML policy, and bind the exact result into one-time approval evidence. Placement
remains disabled.

### Owned existing files

- `apps/api/src/ithildin_api/app.py`
- `apps/api/src/ithildin_api/trusted_host_promotions.py`
- `apps/api/src/ithildin_api/approvals.py`
- `apps/api/src/ithildin_api/policy.py`
- `apps/api/src/ithildin_api/registry.py`
- `policies/default.yaml`
- `policies/tests/default.yaml`
- `tests/test_api_service.py`
- `tests/test_policy_evaluator.py`
- `tests/test_policy_parity.py`

### Required changes

1. Inject `PolicyEngine`, workspace registry, principal registry, manifest-lock evidence, trusted-host
   registry, input-schema evidence, and verified runtime-candidate evidence into the promotion
   service.
2. Add one exact YAML rule for internal action `trusted_host.promotion.stage`. It must return
   `require_approval`, never plain `allow`, with only allowlisted bounded obligations.
3. If configured policy engine is OPA, make only trusted-host proposal/apply routes unavailable with
   safe reason `unsupported_policy_engine_for_promotion`; do not alter other OPA prototype behavior.
4. Bind principal, workspace, sandbox descriptor, trusted-host descriptor, policy decision,
   manifest lock, input schema, runtime candidate, and their generations/digests into canonical
   `PromotionAuthoritySnapshot` JSON and hash.
5. Bind request-specific artifact/source/destination evidence plus the authority snapshot hash into
   the proposal hash. Bind the complete proposal evidence, required approver roles, and authority
   hash into the one-time approval scope.
6. Create proposal and approval evidence atomically or terminally mark
   `approval_evidence_failed`; a partially bound pair can never become applicable.
7. Approval review surfaces may expose safe IDs, hashes, versions, decisions, rules, obligations,
   and posture labels only.

### Focused acceptance evidence

- Every authority component changed after approval makes the proposal terminally stale in a dry-run
  revalidation with no placement.
- YAML `deny`, plain `allow`, incomplete evidence, unknown obligation, duplicate evidence, and OPA
  configuration fail closed.
- Tool count remains `24`; `trusted_host.promotion.stage` is not added to any governed tool manifest
  or MCP list.
- Approval copies, mismatched proposals, wrong requester generations, changed required roles, and
  request/scope hash drift are rejected.

### Validation

```sh
uv run pytest tests/test_policy_evaluator.py tests/test_policy_parity.py \
  tests/test_approval_workflow.py tests/test_api_service.py -q
make policy-test
make policy-parity
make manifest-lock-check
make tool-surface-invariant-gate
make no-new-powers-guardrail
```

### Stop conditions

Stop if the internal action must become an MCP tool, OPA must authorize promotion, policy evidence
cannot be made immutable for one process generation, or approval scope would expose raw policy,
paths, artifacts, authentication material, or candidate locations.

## TGB-004 — Atomic Revalidation And Descriptor-Relative Placement

### Objective

Implement the existing one-artifact Manager-local placement path behind the still-false internal
readiness state, with immediate authority/source revalidation and one atomic execution reservation.
Production routes remain unavailable until `TGB-005` completes.

### Owned existing files

- `apps/api/src/ithildin_api/trusted_host_promotions.py`
- `apps/api/src/ithildin_api/approvals.py`
- `apps/api/src/ithildin_api/app.py`
- `apps/api/src/ithildin_api/filesystem_contract.py`
- `tests/test_api_service.py`
- `tests/test_security_regressions.py`

### Proposed new files

- `apps/api/src/ithildin_api/trusted_host_placement.py`
- `tests/test_trusted_host_placement.py`
- `tests/test_trusted_host_promotion_governance_drift.py`

### Required changes

1. Recompute every server-owned authority component immediately before reservation and compare the
   canonical snapshot/hash with proposal and approval evidence.
2. Open the source exactly once through the existing descriptor-bound no-follow reader, verify its
   object type, size, and digest, and retain those bytes as the only placement buffer.
3. In one SQLite `BEGIN IMMEDIATE` transaction, compare-and-set approval `v2_approved` to
   `v2_executing`, proposal `v2_approval_required` to `v2_executing`, and insert exactly one prepared
   attempt carrying `authority_snapshot_hash`.
4. Any pre-reservation mismatch terminally changes the proposal to `authority_stale`; returning to
   earlier configuration never revives it.
5. Replace path-based destination creation with descriptor-relative traversal from a retained,
   no-follow staging-root descriptor. Use `dir_fd`/`mkdirat`/`openat` equivalents,
   `O_NOFOLLOW`, `O_CREAT`, and `O_EXCL`; verify every ancestor and the single-link regular leaf with
   `fstat`.
6. Compare the current staging-root namespace entry to the retained root immediately before the
   first effect. A pre-write mismatch produces no placement.
7. Write, hash, and flush through the same destination descriptor and flush its parent. Never reopen
   a path to claim success.
8. Recheck the namespace entry after writing. Drift cannot redirect the descriptor-anchored write,
   but it may leave an effect in the originally opened directory; record terminal
   `placement_evidence_recovery_required` and never claim completion.
9. Keep one-artifact, maximum `4096` bytes, create-exclusive, no-overwrite, Manager-local staging.
10. Exercise placement only through explicit internal test fixtures in this ticket. The production
    proposal/apply readiness state remains false even after all `TGB-004` tests pass.

### Focused acceptance evidence

- Sequential and concurrent replay produce at most one attempt and one destination file.
- Every authority component, source object, source byte, and approval decision drift case produces
  no placement.
- Symlink, hardlink, directory, traversal, destination conflict, root replacement before write,
  ancestor substitution, unsupported no-follow primitives, and wrong object type fail closed.
- A controlled post-write namespace change produces recovery evidence and no completion claim.
- No raw exception, root, source path, artifact content, or private candidate metadata enters API or
  audit output.

### Validation

```sh
uv run pytest tests/test_trusted_host_placement.py \
  tests/test_trusted_host_promotion_governance_drift.py \
  tests/test_security_regressions.py tests/test_api_service.py -q
make filesystem-contract-check
make trusted-host-promotion-negative-transcripts
make lint
make typecheck
```

### Stop conditions

Stop if the platform lacks the reviewed descriptor-relative primitives, if atomic reservation cannot
share one SQLite transaction, if a race can redirect placement, if any failure path overwrites or
deletes content, or if the implementation needs arbitrary paths or broader host operations.

## TGB-005 — Evidence, Diagnostics, And UI Consumer

### Objective

Make the version-2 authority and recovery state safely legible to operators without turning Command
Center into an independent authority or exposing sensitive evidence. Enable the production
proposal/apply readiness state only after this ticket's API, audit, UI, accessibility, and review
gates pass.

### Owned existing files

- `apps/api/src/ithildin_api/app.py`
- `apps/api/src/ithildin_api/approvals.py`
- `apps/api/src/ithildin_api/trusted_host_promotions.py`
- `apps/ui/src/App.tsx`
- `apps/ui/src/App.test.tsx`
- `packages/audit-core/src/ithildin_audit_core/writer.py` only if an existing safe event cannot carry
  the required bounded metadata
- `tests/test_api_service.py`
- `tests/test_approval_workflow.py`

### Required changes

1. Return safe requester, approver, executor, host descriptor, policy, manifest, schema, candidate,
   proposal, approval-decision, and authority hashes/versions in proposal review and diagnostics.
2. Keep raw paths, source labels that reveal private structure, contents, prompts, model responses,
   bearer material, policy documents, environment data, candidate locations, and stack traces out.
3. Preserve completion evidence ordering: placement yields `completion_evidence_pending`; append-only
   completion audit succeeds; only then may attempt/proposal become `completed`.
4. Show `legacy_unbound`, `authority_stale`, `approval_evidence_failed`,
   `completion_evidence_pending`, and `placement_evidence_recovery_required` with plain-language
   operator guidance and no retry button.
5. Remove the UI's `DECIDED_BY` constant and caller-attribution body. Display the server-returned
   deciding principal and decision hash only after the decision exists.
6. Command Center consumes Gateway truth; it does not infer policy validity, approval authority,
   placement success, Node ownership, or runner/model state.
7. Preserve keyboard operation, focus visibility, semantic status text, and non-color-only state
   cues for every new or changed UI surface.
8. After focused API/audit/UI/accessibility tests and one Sol high/xhigh read-only review report no
   unresolved critical/high/claim-affecting-medium finding, construct the non-environment readiness
   state from the verified runtime candidate, detached operator authorization, v2 schema, YAML
   policy, registries, and descriptor-relative placement capability. No operator toggle may skip a
   missing component.

### Focused acceptance evidence

- API redaction tests cover each allowed and forbidden evidence field.
- Audit failure after placement cannot produce completed state.
- Diagnostics distinguish clean, stale, legacy, incomplete, and recovery-required states without
  suggesting automatic repair.
- UI request tests prove no caller attribution is sent and stale/concurrent actions remain disabled.
- Accessibility tests cover names, focus, state text, disabled actions, and recovery guidance.

### Validation

```sh
uv run pytest tests/test_approval_workflow.py tests/test_api_service.py -q
npm run test --prefix apps/ui
npm run typecheck --prefix apps/ui
npm run build --prefix apps/ui
make audit-diagnostics
make lint
```

### Stop conditions

Stop if operator comprehension requires exposing raw authority inputs, if the UI must reconstruct
Gateway decisions, if recovery becomes an automatic retry, or if a new audit event/API route is
required without a separate reviewed contract update.

## TGB-006 — Adversarial Proof And Exact-Candidate Review

### Objective

Prove the complete binding on one clean candidate, obtain independent source review, and update
finding status only from observed evidence.

### Owned existing files

- `scripts/trusted_host_promotion_negative_transcripts.py`
- `scripts/trusted_host_promotion_runtime_source_review_bundle.py`
- `docs/codex/v3-trusted-host-promotion-runtime-internal-review.md`
- `docs/codex/trusted-host-promotion-runtime-source-review.md`
- `docs/codex/v3-trusted-host-promotion-runtime-local-disposition.md`
- `docs/codex/trusted-host-promotion-external-response-intake.md`
- `docs/codex/findings/ext-trusted-host-runtime-002-governance-bindings.md`
- `docs/codex/findings/ext-trusted-host-runtime-006-adversarial-coverage.md`
- `tests/test_release_readiness.py`

### Proposed new files

- `scripts/trusted_host_promotion_governance_drift_transcripts.py`
- `docs/codex/v3-trusted-host-promotion-governance-binding-internal-review.md`

### Required changes

1. Generate observed negative transcripts for every row of the architecture adversarial matrix,
   including all authority drifts after approval and every previous-binary downgrade path.
2. Build the runtime source-review bundle from a clean exact commit with current gate evidence,
   candidate inventory digest, dependency-lock digest, release-artifact digest, review-packet digest,
   migration evidence, placement-race evidence, and redaction scan.
3. Run one Sol high/xhigh internal source review focused on identity, approval, migration,
   transactionality, policy, candidate verification, path safety, audit ordering, and safe errors.
4. Remediate all critical/high findings before independent handoff. Medium findings that affect the
   trust claim also block; unrelated low advisories may remain explicit. Internal completion may
   record only `implementation_candidate_ready_for_independent_re_review` in verification notes.
5. Send the exact clean source/packet candidate to an independent reviewer. No Sol Ultra review may
   be requested without the user's prior approval. Normalize and validate the response through the
   trusted-host response-intake contract; extend that contract first if it cannot bind the runtime
   governance packet, exact commit, packet hash, source-access level, and finding namespace.
6. Change `EXT-TRUSTED-HOST-RUNTIME-002` from deferred only after independent response intake accepts
   exact evidence proving every binding. Change `EXT-TRUSTED-HOST-RUNTIME-006` only after the same
   independent response accepts the observed, packet-bound governance-drift transcripts.
7. Do not treat internal review, generated packets, green gates, packet upload, or response receipt
   as external approval, finding disposition, or UAT.

### Exact-candidate acceptance gates

```sh
make trusted-host-promotion-governance-binding-architecture-check
make trusted-host-promotion-governance-binding-implementation-tickets-check
make trusted-host-promotion-negative-transcripts
uv run python scripts/trusted_host_promotion_governance_drift_transcripts.py
make trusted-host-promotion-runtime-source-review-bundle
make trusted-host-promotion-runtime-source-review-bundle-check
make tool-surface-invariant-gate
make no-new-powers-guardrail
make release-check
make review-candidate
```

The final candidate must be clean, tool count must be `24`, policy parity must be `24/24`, packet
hashes must match files, and the independent review must report no unresolved critical/high
implementation finding.

### Stop conditions

Stop on any critical/high trust-boundary finding, three repetitions of the same gate failure,
candidate/packet identity mismatch, redaction failure, tool-count change, or evidence that a claimed
binding is indirect rather than observed.

## Required Cross-Ticket Test Matrix

The implementation owner must maintain a matrix with one positive and at least one negative proof
for each category:

| Category | Minimum proof |
| --- | --- |
| Identity | server-derived requester/approver/executor plus rejection of caller `principal`, roles, tenant, workspace authority, and `decided_by` |
| Host registry | exact workspace/label resolution plus missing, duplicate, wrong workspace, unsafe posture, raw path, and generation drift |
| Workspace/sandbox | active record and descriptor hashes plus disabled, missing, mismatched, and post-approval drift |
| Policy | YAML `require_approval` plus deny, plain allow, OPA, rule, obligation, document, and digest drift |
| Manifest/schema | exact 24-tool lock and input schema plus version/digest/tool-count/unknown-field drift |
| Candidate | verified inventory plus inventory schema, installed file, dependency lock, artifact, packet, allowlist, writable-root, and metadata spoof failures |
| Approval | exact scope and decision hash plus copied, expired, wrong role, wrong proposal, replayed, and concurrent decisions |
| Migration | clean/legacy/interrupted/restart plus old proposal/approve/deny/apply/attempt denial |
| Source/destination | retained source buffer and descriptor-relative create-exclusive write plus object, traversal, link, conflict, and namespace race failures |
| Evidence | completion audit ordering, safe diagnostics, redaction, recovery state, exact-candidate freshness, and packet hashes |

## Explicit Non-Goals

These tickets do not implement or approve:

- Node-side or remote host placement;
- runner launch, stop, mutation, credential brokering, inference, or sandbox orchestration;
- arbitrary paths, overwrite, delete, move, chmod, recursion, directory copy, or archive extraction;
- automatic, wildcard, batch, or approval-free promotion;
- a 25th tool, MCP exposure, a new executor power class, or plugin SDK behavior;
- OPA-backed promotion, policy distribution, production IAM/RBAC, runtime Postgres, hosted telemetry,
  remote MCP, SIEM delivery, compliance automation, or public security-product claims;
- code signing, remote attestation, HSM/TPM custody, endpoint-security equivalence, or proof that a
  privileged host cannot bypass Ithildin.

## UAT Boundary

No human UAT is required to execute `TGB-001` through `TGB-006`. After the exact candidate is green
and independently source-reviewed, operator UAT may assess whether the authority evidence, stale
states, recovery guidance, and approval flow feel clear and trustworthy. UAT does not replace any
automated, migration, adversarial, or source-review gate above.

## Packet Completion Definition

This approved ticket packet is complete when:

- all six tickets name exact objectives, owners, source files, acceptance evidence, validation, and
  stop conditions;
- the architecture checker, this packet checker, live tool-surface gate, and live no-new-powers gate
  pass;
- authorization remains bounded to the runtime/API/schema/policy/persistence/placement changes
  named by `TGB-001` through `TGB-006`;
- current decision remains `approved_for_bounded_implementation`.

Packet completion means the implementation path is authorized and reviewable. It does not mean the
implementation is complete, the live route is enabled, findings are closed, the candidate is
externally accepted, the product is released, or UAT has passed.
