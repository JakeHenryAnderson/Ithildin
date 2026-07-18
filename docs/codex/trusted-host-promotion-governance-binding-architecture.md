# Trusted-Host Promotion Governance-Binding Architecture

Status: proposed architecture decision for `ERG-005`; explicit implementation approval required.

Decision ID: `PRD-TRUSTED-HOST-BINDING-001`.

Current governed tool count: `24`.

Current runtime boundary: one-artifact, create-exclusive, Manager-local host-staging placement.

Proposed decision outcome: `approve_governance_binding_implementation_plan`.

This packet proposes the smallest architecture intended to close
`EXT-TRUSTED-HOST-RUNTIME-002` and the dependent governance-drift portion of
`EXT-TRUSTED-HOST-RUNTIME-006`. It does not change an API, database schema, manifest, policy,
executor, deployment mode, or runtime behavior. It does not close either finding and it does not
approve implementation by itself.

Validate the proposal with:

```sh
make trusted-host-promotion-governance-binding-architecture-check
```

## Decision Summary

The proposed architecture introduces one immutable `PromotionAuthoritySnapshot` created entirely
from server-owned state. A proposal, its one-time approval, its placement attempt, and its audit
evidence must all bind the exact same snapshot hash.

The snapshot binds:

- a server-derived requesting principal;
- a server-resolved trusted-host descriptor ID and hash;
- the active workspace and sandbox descriptor identities;
- policy engine, document version, version, digest, decision, matched rules, and obligations;
- the exact 24-tool manifest-lock version, digest, and tool count;
- the closed promotion input-schema version and digest;
- an immutable reviewed runtime-candidate identity and digest;
- the authority snapshot hash is then included in the proposal hash and approval scope alongside
  the source artifact, destination label, and other request-specific evidence already required by
  the current staging-only runtime.

Immediately before placement, the Gateway must recompute the server-owned authority snapshot and
compare it with the stored proposal snapshot. Any mismatch terminally invalidates the proposal as
`authority_stale`; returning later to the old configuration must not make the proposal usable again.

## Why This Is The Next Control-Plane Foundation

The current runtime safely proves one bounded artifact can be staged without overwrite after a
one-time approval. It cannot yet prove that the caller, destination host posture, policy, governed
surface, schema, or reviewed implementation is the same authority an operator reviewed.

Closing that gap creates a reusable control-plane primitive:

```text
authenticated actor
  + server-owned destination posture
  + exact policy/configuration generation
  + reviewed runtime identity
  + one-time approval
  -> one bounded action with reconstructable evidence
```

That primitive is required before Ithildin can honestly expand from local Manager staging toward
Node-mediated placement, fleet operations, or enterprise deployment. It is not itself remote fleet
management.

## Authority Boundaries

| Component | Authoritative for | Explicitly not authoritative for |
| --- | --- | --- |
| Gateway | authenticated principal, proposal, approval binding, policy decision, workspace state, manifest/schema/candidate snapshot, attempt state, audit evidence | model inference, runner health, Node-local enforcement claims |
| Manager-local trusted-host registry | bounded staging label resolution and operator-reviewed local host posture | automatic enrollment, remote attestation, host security certification |
| Ithildin Node | its enrolled machine identity, signed request possession, stored configuration acknowledgment | Manager-local placement, operator identity, policy authorship, runner/model state |
| External runner | correlation labels and runner-reported state | principal identity, workspace authority, policy result, approval authority |
| Command Center | presentation of Gateway truth and safe operator actions | independent runtime or approval authority |
| Model provider | inference | tool authorization, host placement, audit custody |

The first implementation must not attach a Node ID to a Manager-local placement merely to make the
evidence look fleet-aware. A future Node-side placement capability requires a separate architecture,
transport, authorization, executor, interruption, and non-bypass review.

## Server-Derived Principal

### Local-preview principal context

The admin authentication dependency should return an immutable `AdminPrincipalContext` rather than
only succeeding or raising. For the current local-preview bearer-token boundary, the context is
server-derived:

```json
{
  "principal_id": "admin:local-ui",
  "principal_type": "admin",
  "roles": ["Admin", "Approver", "Auditor"],
  "authentication_method": "local_admin_bearer",
  "identity_source": "principal_registry",
  "identity_generation": "sha256:..."
}
```

The concrete first-slice identity is the existing enabled `admin:local-ui` registry record.
`identity_generation` is the canonical digest of that enabled record and its principal-registry
document generation. `require_admin_principal` must validate the bearer token, resolve that record
from the application registry, require the `Admin` role, and return this context. Authentication
success without an enabled registry record fails closed.

The proposal body must no longer accept `principal`, roles, identity source, or authentication
method. Unknown-field rejection makes caller-supplied identity a `400` schema error. The route
passes `AdminPrincipalContext` directly to `TrustedHostPromotionService.create_proposal`.

This is not production identity or enterprise RBAC. A later production authentication adapter may
construct the same internal context only after its own `ERG-006` decision and implementation gate.

### Attribution rules

- Requesting principal is captured when the proposal is created.
- Approving principal is derived by the same dependency and separately captured by the approval
  system; an approval decision body cannot supply it.
- Apply-route principal is captured for execution attribution and must be an enabled admin, but it
  need not equal the requester unless policy explicitly requires that obligation.
- Requester, approver, and executor identities remain distinct in evidence.
- Caller-supplied identity, role, tenant, workspace authority, or approval attribution is rejected.

### Approval decision attribution

The generic local-preview approve and deny routes are part of this authority boundary. Their closed
request body must change from caller-supplied `decided_by` to:

```json
{
  "decision": "approve",
  "reason": "optional bounded operator reason"
}
```

The route passes `AdminPrincipalContext.principal_id` to `ApprovalService`. Approval storage must
persist and safely return `decided_by`, decision time, and a `decision_hash` over approval ID,
approval request hash, decision, server-derived deciding principal, bounded reason hash, and
authority snapshot hash when present. The approval scope binds required approver roles; the later
decision record binds the actual approver. Apply must validate both. Accepting and ignoring a legacy
`decided_by` field is forbidden.

## Server-Owned Trusted-Host Descriptor

### First-slice descriptor registry

The current `trusted-host-descriptor-contract.md` is design-only evidence. The implementation plan
should introduce a read-only `TrustedHostDescriptorRegistry` loaded and validated at Gateway startup
from operator-controlled configuration. It must not add a host-registration or mutation API.

Each record must contain only secret-free bounded fields:

- `descriptor_schema_version: "2"` and a registry-schema digest;
- `descriptor_id` and canonical descriptor hash;
- supported local-preview OS/filesystem posture;
- operator review status and evidence timestamp;
- workspace binding;
- one `host-staging://` label;
- an internal staging-root resolver reference that is never returned in API or audit output;
- `staging_create_exclusive_allowed: true` only for the existing bounded operation;
- `host_write_allowed: false` under the broader descriptor-contract meaning;
- `broad_host_write_allowed: false`;
- descriptor generation and source digest.

The proposal request supplies only the destination label. The Gateway resolves exactly one active
descriptor from that label and workspace. Zero matches or multiple matches fail closed. The request
cannot supply a descriptor ID, descriptor hash, raw root, relative destination path, Node ID, host
identifier, or posture claim.

The registry is immutable for the lifetime of a Gateway process. A configuration change requires a
validated restart, which produces a new descriptor generation/hash. This makes the snapshot stable
during one placement attempt and prevents an in-process descriptor time-of-check/time-of-use race.

Version 2 is a new runtime registry schema. It consumes the safe posture vocabulary from the
planning-only version-1 descriptor contract but does not relabel that fixture as runtime authority.
Its checker must prove the schema/version transition, `host_write_allowed: false`, the singular
create-exclusive staging permission, and rejection of every forbidden descriptor field.

### Relationship to Node enrollment

Node enrollment already gives the Gateway a server-issued Node and principal identity plus a
descriptor hash. Those records may inform a later Node-host trust decision, but they do not prove
that the current Manager-local staging root belongs to that Node. The first governance-binding slice
therefore uses a Manager-local trusted-host descriptor and does not require or fabricate a Node
binding.

## Promotion Authority Snapshot

The internal closed model should be versioned independently from the public request:

```json
{
  "authority_schema_version": "1",
  "requesting_principal": {
    "principal_id": "admin:local-ui",
    "principal_type": "admin",
    "roles": ["Admin", "Approver", "Auditor"],
    "authentication_method": "local_admin_bearer",
    "identity_source": "principal_registry",
    "identity_generation": "sha256:..."
  },
  "workspace": {
    "workspace_id": "default",
    "registry_generation": "sha256:...",
    "workspace_record_hash": "sha256:...",
    "active": true
  },
  "sandbox_descriptor": {
    "descriptor_id": "sbd_...",
    "descriptor_hash": "sha256:...",
    "sandbox_id": "sandbox_...",
    "workspace_id": "default"
  },
  "trusted_host": {
    "descriptor_id": "thd_manager_local_preview",
    "descriptor_hash": "sha256:...",
    "descriptor_generation": "1",
    "workspace_id": "default",
    "host_staging_label": "host-staging://artifact"
  },
  "policy": {
    "engine": "yaml",
    "document_version": "1",
    "policy_version": "...",
    "policy_digest": "sha256:...",
    "decision": "require_approval",
    "matched_rules": ["..."],
    "obligations": {
      "approval_mode": "one_time",
      "placement_mode": "create_exclusive",
      "zone": "host_staging"
    }
  },
  "manifest": {
    "lock_version": "1",
    "lock_digest": "sha256:...",
    "tool_count": 24
  },
  "input_schema": {
    "schema_id": "ithildin.trusted_host_promotion_proposal",
    "schema_version": "2",
    "schema_digest": "sha256:..."
  },
  "runtime_candidate": {
    "candidate_id": "sha256:...",
    "source_commit": "...",
    "source_dirty": false,
    "inventory_schema_version": "1",
    "reviewed_inventory_digest": "sha256:...",
    "dependency_lock_digest": "sha256:...",
    "release_artifact_digest": "sha256:...",
    "review_packet_digest": "sha256:...",
    "evidence_schema_version": "1"
  }
}
```

`authority_snapshot_hash` is the SHA-256 digest of canonical JSON for this model. Every list must be
sorted and deduplicated before hashing. Unknown fields, missing evidence, unsafe labels, non-canonical
hashes, duplicate rules/obligations, or a tool count other than `24` fail closed.

Request-specific artifact identity, source path label, destination label, proposal ID/hash, approval
ID/request hash, and later approval-decision hash remain outside the reusable authority snapshot.
The proposal hash binds those fields together with `authority_snapshot_hash`; the approval scope
binds the resulting proposal hash and the same constituent evidence. This separation is normative,
not an omission from the sample snapshot.

## Policy And Manifest Semantics

Trusted-host staging remains an internal admin API action, not a 25th governed MCP tool. The policy
snapshot must therefore use a dedicated internal action identifier,
`trusted_host.promotion.stage`, without adding it to `tool-manifests.lock.json` or exposing it over
MCP.

The policy layer must return a closed decision record:

- actual `PolicyDecisionValue` semantics: `deny` or `require_approval`; `allow` is invalid for this
  action;
- exact engine, document version, policy version, and digest;
- bounded matched-rule IDs;
- bounded obligation keys from an allowlist;
- no caller-supplied policy evidence;
- no raw policy document or sensitive context in output.

The manifest binding records the exact existing 24-tool lock because the operator is authorizing a
promotion within that governed system state. It does not claim the promotion action is an MCP tool.
Any manifest digest or tool-count change makes an existing proposal stale.

The first implementation slice supports only the canonical local-preview YAML engine, which is
loaded once and immutable for one Gateway process generation. If the configured engine is OPA,
trusted-host proposal and apply routes fail closed with `unsupported_policy_engine_for_promotion`.
OPA is a remote mutable decision source even when its bundle manifest is verified; supporting it for
promotion requires a separate design for decision receipts, bundle/response identity, availability,
and revalidation atomicity. Other existing OPA prototype behavior is unchanged.

YAML policy, manifest, workspace registry, and descriptor state must be immutable in memory for one
Gateway process generation. If future hot reload is introduced, the reload path must serialize with
proposal revalidation and placement or use an equivalent immutable-generation lease.

## Reviewed Runtime-Candidate Identity

Git state discovered at request time and allowlisted metadata are not sufficient trust roots. The
proposed first slice requires a closed candidate file inventory produced by the exact-candidate
packaging flow. A minimal `RuntimeCandidateVerifier` must verify that inventory before importing the
API runtime and re-hash it immediately before placement. The verified inventory covers Ithildin
application packages, schemas, migrations, manifest lock, canonical YAML policy, and candidate
metadata; it also binds the dependency lock and release artifact digest.

Only verifier output may construct `RuntimeCandidateRecord`. It binds:

- clean source commit;
- reviewed inventory schema version and digest;
- dependency-lock digest;
- release artifact digest;
- trusted-host runtime review-packet digest;
- evidence schema version;
- a stable candidate ID derived from the source commit, inventory schema/digest, dependency-lock
  digest, release-artifact digest, and evidence-schema version.

The digest domains must be detached and acyclic. `reviewed_inventory_digest` covers the canonical
path-and-file-digest inventory for runtime files and the dependency lock, excluding generated
candidate metadata, the release container, and review-packet files. `release_artifact_digest`
covers the immutable packaged artifact that embeds that inventory manifest, excluding the separate
candidate record and review packet. `candidate_id` hashes the candidate core fields listed above.
The separately generated review packet then names that candidate ID, and `review_packet_digest`
hashes the packet manifest and files. The authority snapshot binds both the candidate ID and review
packet digest; neither digest is defined in terms of the final authority snapshot.

The operator configuration must name the allowed candidate ID and reviewed inventory digest.
Startup fails closed for promotion if inventory verification fails, the package root is writable by
an unexpected identity, the record is missing/malformed/dirty, or the result is not allowlisted.
Local developer/source-checkout runs may report `unreviewed_local`, but promotion routes remain
unavailable in that posture except inside explicit test fixtures. An environment variable or
allowlisted metadata record alone cannot assert reviewed status. Any pre-placement file-inventory
drift terminally stales the proposal.

Within the documented local-host threat model, this verifies that the on-disk runtime inventory used
for placement matches the reviewed artifact. It does not prove in-memory integrity against a
privileged hostile host and does not provide general code signing, supply-chain attestation, remote
attestation, or production deployment trust. Any stronger claim requires a separate packaging and
platform trust decision.

## Proposed Public Request Contract

The version-2 proposal body remains closed:

```json
{
  "workspace_id": "default",
  "sandbox_descriptor_id": "sbd_...",
  "sandbox_id": "sandbox_...",
  "source_artifact_path": "outputs/report.txt",
  "host_staging_label": "host-staging://artifact",
  "artifact_media_label": "text/plain",
  "operator_note_label": "reviewed-output"
}
```

Changes from the current request contract:

- remove `principal` completely;
- retain strict unknown-field rejection;
- do not add policy, manifest, schema, candidate, trusted-host descriptor, Node, host, or raw-path
  fields;
- return safe `authority_snapshot_hash`, requesting-principal ID, descriptor ID/hash, and bounded
  policy/candidate status labels in proposal detail;
- never return the internal staging root, source path, policy document, raw authentication data, or
  candidate filesystem location.

The generic approval decision contract also removes `decided_by` and adds safe server-derived
decision attribution as described above. Both changes are explicit public-contract changes covered
by the approval gate.

This is an intentional breaking change for clients that send `principal`. There is no compatibility
mode that accepts and ignores it, because doing so would preserve ambiguous trust semantics.

## Proposal And Approval Flow

### Proposal creation

1. Authenticate and derive `AdminPrincipalContext`.
2. Validate the closed version-2 request.
3. Resolve active workspace and sandbox descriptor from server stores.
4. Safely open and hash the source artifact through the existing descriptor-bound reader.
5. Resolve exactly one active trusted-host descriptor from workspace and staging label.
6. Evaluate the internal staging policy and require `require_approval`.
7. Read immutable manifest, input-schema, and runtime-candidate evidence.
8. Canonicalize and hash `PromotionAuthoritySnapshot`.
9. Include `authority_snapshot_hash` in the proposal hash and store the proposal plus snapshot
   before creating approval.
10. Create exactly one approval whose request hash and one-time scope include the snapshot hash and
    every safe binding needed for independent review.
11. Bind the created approval ID to the proposal.

If approval creation or binding fails, the proposal becomes terminal `approval_evidence_failed` and
cannot be reused.

### Approval scope additions

The one-time scope must add:

- `authority_snapshot_hash`;
- requesting principal ID and identity generation;
- trusted-host descriptor ID, hash, and generation;
- policy engine, document version, version, digest, decision, matched rules, and obligations;
- manifest-lock version, digest, and tool count;
- input-schema ID, version, and digest;
- runtime-candidate ID, source commit, release artifact digest, and review-packet digest;
- runtime-candidate inventory schema/digest and dependency-lock digest.

The scope also binds required approver roles. After decision, the stored approval decision record
adds the actual server-derived approving principal and `decision_hash`; apply revalidates that record
without rewriting the original one-time scope.

The approval review surface should show these as safe IDs, hashes, versions, and bounded labels. It
must not expose bearer material, raw policies, raw host paths, artifacts, prompts, responses, or
private runtime metadata.

## Immediate Pre-Placement Revalidation

Before `ApprovalService.begin_execution`, the service must:

1. load the proposal and require persisted `v2_approval_required` (presented through the API as the
   bounded state label `approval_required`);
2. verify the exact bound approval identity and existing request/scope hashes;
3. derive the apply-route principal from authentication and verify current admin eligibility;
4. recompute the complete server-owned authority snapshot;
5. re-open the source artifact once through the descriptor-bound no-follow reader, verify its exact
   digest and bounded object type, and retain those exact bytes as the only placement buffer;
6. compare the recomputed snapshot and source evidence with the stored proposal and approval scope;
7. use one SQLite `BEGIN IMMEDIATE` coordinator transaction to compare-and-set the approval from
   persisted `v2_approved` to `v2_executing`, compare-and-set the proposal from persisted
   `v2_approval_required` to `v2_executing`, and insert the single prepared attempt;
8. perform only the existing create-exclusive staging placement with the already revalidated source
   bytes.

Any mismatch must atomically transition the proposal to terminal `authority_stale` before returning
a safe conflict. The approval is not consumed, but that approval/proposal pair can never become
usable again. A new proposal and approval are required under current authority.

The current process-lifetime descriptor, policy, manifest, schema, and candidate generations are
immutable. That is the first-slice protection against authority changing between revalidation and
placement. A later hot-reload design must add an immutable-generation lease or serialize reload
with placement.

The approval, proposal, and attempt stores currently use the same SQLite database. The implementation
must not emulate the coordinator with independent store calls or compensating updates. If those
records do not share one transactional database in a future deployment, implementation must stop
until a separately reviewed durable transaction/outbox protocol exists.

### Descriptor-relative destination placement

Authority revalidation does not make path-based destination creation safe. The runtime descriptor
must open the configured staging root through no-follow descriptor traversal, capture its device and
inode identity, and retain a directory file descriptor for placement. Destination directories and
the leaf must be created relative to verified directory descriptors using `dir_fd`/`mkdirat` and
`openat` equivalents, with `O_NOFOLLOW`, `O_CREAT`, and `O_EXCL` where supported. Every opened
ancestor must be `fstat`-verified as the expected directory object; the new leaf must be a regular
single-link file. Placement writes and hashes the retained source buffer through the same opened
destination descriptor, flushes the file and parent directory, and never reopens a path to verify
success.

Immediately before the first filesystem effect, the runtime re-resolves the staging-root namespace
entry relative to its retained trusted parent descriptor and compares that entry's device/inode to
the retained root descriptor. Pre-write mismatch, symlink substitution of any ancestor, directory
alias ambiguity, or unsupported no-follow primitives fails before placement. Descriptor anchoring
then guarantees that a later namespace replacement cannot redirect the write to a substituted
directory; it does not guarantee that the retained directory remains reachable under the original
name.

After the write and directory flush, the runtime repeats the namespace-entry comparison. If the
entry changed after the pre-write check, a filesystem effect may already exist in the originally
opened directory. The attempt must become terminal `placement_evidence_recovery_required`, must not
claim completion, and must emit only safe recovery evidence for operator reconciliation. A no-effect
guarantee against a privileged actor concurrently renaming the trusted root would require a
separately reviewed namespace-control primitive and stronger local-host threat model. A platform
without the reviewed descriptor-relative primitives remains unsupported for promotion.

## Persistence And Migration Contract

This architecture proposes a versioned SQLite table-rebuild migration, but does not authorize it:

- add `authority_schema_version`;
- add canonical `authority_snapshot_json`;
- add indexed, non-unique `authority_snapshot_hash` per proposal record;
- copy `authority_snapshot_hash` into each attempt;
- rebuild approval storage with non-null authority-version/request-binding fields for version-2
  approvals and a decision hash populated only by the authenticated decision path;
- add explicit proposal states `legacy_unbound`, `approval_evidence_failed`, and `authority_stale`;
- preserve existing proposal, attempt, approval, and audit identifiers.

Existing proposals have no trustworthy authority snapshot. Migration must label every pre-version-2
nonterminal proposal `legacy_unbound`; it must not synthesize missing evidence from current state.
Legacy proposals and approvals cannot be applied, retried, or upgraded. Completed historical rows
remain readable with `authority_binding_status: legacy_unbound` and no broader claim.

The implementation plan must include forward migration, interrupted migration, restart, rollback,
and old-binary behavior. Rollback may restore the previous binary only after proving it cannot apply
version-2 or `legacy_unbound` proposals. If that cannot be proven, rollback remains disabled and the
operator must restore from a pre-migration local-preview backup.

The migration must technically fence downgrade, not rely on operator instructions. Inside one
transaction it rebuilds the proposal, approval, and attempt tables with non-null version-2 authority
columns, uses version-2 persisted status labels such as `v2_approval_required`, `v2_pending`,
`v2_approved`, and `v2_denied`, enforces those vocabularies with table constraints, and records a
schema-version/minimum-writer row. API serializers may map those values to existing bounded display
labels, but storage and compare-and-set logic use only the version-2 vocabulary.

The constraints are conditional on the non-null row authority version: migrated legacy rows may use
only a closed legacy vocabulary and version-2 rows may use only the closed `v2_*` vocabulary. This
allows historical reads without allowing a previous binary to write a legacy status onto a
version-2 row.

An old binary cannot insert a new proposal or approval because its inserts omit required authority
columns; it cannot approve or deny a version-2 approval because its legacy status writes violate
the approval-table constraint; it cannot apply migrated/new rows because it does not recognize their
proposal statuses; and it cannot create an attempt because the version-2 attempt table requires
`authority_snapshot_hash`. The version-2 authenticated decision path alone writes deciding-principal
identity, decision time, reason hash, and `decision_hash` while transitioning `v2_pending` to a
terminal version-2 decision state. Tests must execute the previous binary contract against the
migrated fixture and prove proposal insertion, approve, deny, apply, attempt creation, and every
placement path fail before filesystem effects.

## Evidence And Audit Contract

Safe proposal, attempt, and audit evidence may contain:

- proposal, approval, attempt, request, workspace, sandbox, and descriptor IDs;
- artifact, proposal, request, approval-scope, authority-snapshot, policy, manifest, schema,
  candidate, and staged-output hashes;
- policy/candidate/schema versions and bounded rule/obligation labels;
- candidate inventory schema/digest and dependency-lock digest;
- requester, approver, and executor principal IDs;
- state, reason, redaction, and warning labels;
- timestamps, safe counts, and staging-only/create-exclusive booleans.

It must exclude raw host paths, internal staging roots, artifact contents, file contents, diffs,
prompts, model responses, policy documents, bearer tokens, session material, private keys, raw IdP
claims, environment values, stack traces, or runner/model inference data.

Terminal completion remains evidence-gated: placement produces `completion_evidence_pending`, the
append-only completion event must succeed, and only then may proposal/attempt state become
`completed`.

## Fail-Closed State And Reason Matrix

| Condition | Proposal state | Approval consumed | Placement | Safe reason |
| --- | --- | --- | --- | --- |
| Authentication cannot derive principal | no proposal | no | no | `identity_unavailable` |
| Principal disabled or not admin | no proposal | no | no | `principal_not_authorized` |
| Host descriptor absent/ambiguous | no proposal | no | no | `trusted_host_unavailable` |
| Policy denial or incomplete evidence | no proposal | no | no | `policy_denied` |
| Manifest/schema/candidate evidence unavailable | no proposal | no | no | `authority_evidence_unavailable` |
| Approval creation/binding failure | `approval_evidence_failed` | no | no | `approval_evidence_failed` |
| Any snapshot drift before apply | `authority_stale` | no | no | `authority_snapshot_mismatch` |
| Source artifact drift/unsafe object | `authority_stale` | no | no | `source_evidence_mismatch` |
| Legacy proposal | `legacy_unbound` | no | no | `legacy_authority_unbound` |
| Concurrent/replayed apply | existing terminal/reserved state | at most once | at most once | `proposal_not_applicable` |
| Placement succeeds but completion audit fails | `completion_evidence_pending` | yes | exactly once | `completion_evidence_incomplete` |
| Staging-root namespace changes after write begins | `placement_evidence_recovery_required` | yes | possible in retained original directory | `staging_root_namespace_drift` |

Errors exposed through API or diagnostics must use reviewed safe labels. Raw exception text must not
be copied into audit metadata or public responses.

## Adversarial Validation Matrix

The implementation plan must include direct tests and generated evidence for:

| Category | Required negative proof |
| --- | --- |
| Identity | caller-supplied principal/role/`decided_by` rejected; missing/invalid admin token; absent/disabled registry principal; approve and deny attribution server-derived; UI and other approval consumers updated; requester/approver/executor remain distinct |
| Host descriptor | missing, duplicate, wrong workspace, rejected review status, changed generation/hash, unsupported filesystem posture, raw path injection |
| Policy | YAML `deny`, plain `allow`, required `require_approval`, OPA rejected for this slice, digest/version/document drift, changed rule/obligation set, duplicate or unsorted evidence |
| Manifest | lock digest drift, version drift, tool count not 24, manifest changed after approval |
| Schema | unknown request fields, legacy principal field, schema version/digest drift, old client payload |
| Candidate | absent inventory, dirty source, wrong allowlisted candidate, inventory-schema/reviewed-inventory/installed-file/commit/artifact/packet/dependency digest drift, digest-domain cycle rejection, writable package root, environment-only or metadata-only spoof |
| Approval | copied approval, wrong proposal, wrong snapshot, wrong requester, expiry, replay, sequential and concurrent double apply |
| Source/destination | retained exact source buffer, symlink, hardlink, directory, stale hash, destination conflict, traversal, sensitive label, overwrite, pre-write staging-root replacement, post-write namespace drift recovery state, ancestor-symlink race, unsupported no-follow primitives |
| Migration | legacy rows, partial table rebuild, restart between steps, new binary/old database, previous binary proposal/approve/deny/apply/attempt paths technically denied against migrated database, rollback denial |
| Evidence | completion-audit interruption, malformed snapshot JSON, safe diagnostics, packet redaction, exact-candidate packet freshness |

At least one test must change each authority component after approval and prove placement does not
occur. `EXT-TRUSTED-HOST-RUNTIME-006` remains deferred until this governance-drift matrix exists as
observed evidence, not only as a plan.

## Bounded Implementation Slices

If explicitly approved, one implementation owner should execute these slices in order:

1. **Foundation models and fixtures** — `AdminPrincipalContext`, read-only trusted-host registry,
   verified runtime-candidate inventory, authority snapshot canonicalization, safe reason enum; no
   route change.
2. **Proposal v2 and migration** — remove request principal, persist snapshot, mark legacy proposals,
   derive generic approval decisions from authenticated principal, add downgrade fencing, and expand
   safe proposal/approval detail; no placement change yet.
3. **Policy/approval binding** — internal action policy decision and complete approval-scope binding;
   keep placement disabled until focused review passes.
4. **Pre-placement revalidation** — terminal stale-state transition, exact snapshot/source comparison,
   one-attempt reservation, existing create-exclusive placement only.
5. **Evidence and diagnostics** — audit metadata, safe failure labels, migration/recovery diagnostics,
   governance-drift transcripts.
6. **Exact-candidate source review** — focused packet, independent review, finding intake, remediation,
   release-check, and review-candidate evidence.

Each slice must pass focused tests before the next begins. A critical/high trust-boundary finding or
three repetitions of the same gate failure stops implementation.

## Implementation Acceptance Gates

Implementation is not approved by this document. A later explicit decision must authorize the
public request and persistence changes above. Once authorized, completion requires:

- no caller-supplied principal field anywhere in the proposal route or service;
- no caller-supplied `decided_by` field in approval decision routes or service calls;
- one canonical authority snapshot shared by proposal, approval, attempt, audit, and diagnostics;
- immediate pre-placement server-side revalidation of every snapshot component;
- terminal stale/legacy semantics that cannot become valid again after rollback;
- observed negative evidence for every row in the adversarial matrix;
- no new API route, MCP exposure, executor class, governed tool manifest, or tool-count change;
- `make agent-workflow-check`;
- focused API, migration, policy, audit, and release-readiness tests;
- `make release-check` and `make review-candidate` on the exact clean candidate;
- independent source review with no unresolved critical/high implementation finding;
- finding `002` changed only after evidence proves every binding;
- finding `006` changed only after observed governance-drift evidence exists.

## Explicit Non-Goals And Stop Lines

This architecture does not approve or implement:

- Node-side or remote host placement;
- runner launch, stop, mutation, credential brokering, or sandbox orchestration;
- arbitrary paths, overwrite, delete, move, chmod, recursion, directory copy, or archive extraction;
- automatic, wildcard, batch, or approval-free promotion;
- a 25th governed tool, MCP exposure, plugin behavior, or a new executor power class;
- production IAM, enterprise RBAC, TLS/mTLS, remote administration, runtime Postgres, hosted
  telemetry, remote MCP, SIEM runtime integration, compliance automation, or public security claims;
- code signing, remote attestation, HSM/TPM custody, or supply-chain certification;
- proof of runner enforcement, model inference visibility, filesystem non-bypass, or endpoint
  security equivalence.

Stop and require a new decision if implementation needs any of those capabilities, changes the
24-tool surface, makes the trusted-host registry mutable over an API, permits hot reload without an
immutable-generation safety design, or cannot fail closed when candidate/policy/manifest evidence
is unavailable.

## Approval Gate

The current decision remains `proposed_for_explicit_approval`.

The required approval statement is:

```text
Approve PRD-TRUSTED-HOST-BINDING-001 for bounded implementation, including the version-2 trusted-host
promotion and approval-decision requests plus the versioned SQLite table-rebuild migration, while
preserving the 24-tool, staging-only,
Manager-local boundary and every stop line in the architecture packet.
```

Until that approval is recorded, runtime API, schema, policy, persistence, and placement behavior
remain unchanged.
