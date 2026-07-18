# Mission Command Control Plane Implementation Tickets

Status: ordered bounded implementation packet. No mission route is enabled merely because this
packet exists.

Current governed tool count: `24`.

## Authorization Scope

The capability decision and active enterprise goal authorize `MCC-001` through `MCC-006` in order.
One Sol implementation owner controls changes. Sol xhigh may perform independent read-only trust
review; Sol Ultra is not used without the user's prior approval.

The ticket sequence changes administrative and Node REST APIs plus SQLite persistence, but it adds
no MCP tool, tool manifest, governed power class, arbitrary host control, or model-provider custody.

## Dependency Graph

```text
MCC-001 mission authority model and fail-closed persistence
  -> MCC-002 authenticated admission and operator reads
    -> MCC-003 signed Node claim
      -> MCC-004 runner-report lifecycle and cancellation races
        -> MCC-005 Command Center mission and fleet cockpit
          -> MCC-006 restart/replay/partition POC and exact-candidate review
```

## MCC-001 — Mission Authority Foundation

Objective: define immutable mission/request/report models, closed enums, canonical hashing, and a
transactional SQLite store while all public mission routes remain absent.

Acceptance evidence:

- Gateway derives mission IDs, requester attribution, workspace, Node principal, configuration
  generation/digest, policy digest, manifest digest, template registry generation/payload digest,
  and envelope digest;
- duplicate `client_request_id` is idempotent only within the exact server-derived requester
  principal/identity-generation namespace and for an exact canonical request;
- invalid legacy/caller authority fields are rejected;
- the coordinated SQLite migration bumps schema/minimum-writer version to `4`, verifies all mission
  constraints in the central transaction, emits a pre-migration backup receipt, rolls back an
  interrupted upgrade, makes the previous writer refuse the upgraded database, and proves
  restore-only downgrade;
- each transition durably stages without changing authoritative lifecycle state, writes staged
  audit evidence, finalizes by binding audit event ID/hash, and preserves the prior lifecycle state
  on every interruption;
- no envelope or terminal response is returned before evidence finalization;
- focused model, storage, migration, downgrade, and interruption tests pass; tool count remains
  `24`.

Stop if the model needs arbitrary command, path, environment, URL, provider secret, caller-authored
objective/summary, or runner executable fields.

## MCC-002 — Authenticated Admission And Operator Reads

Objective: add Admin-authorized create/list/detail/cancel endpoints and append-only admission evidence
while keeping Node delivery disabled.

Acceptance evidence:

- current server-derived Admin context is required;
- target Node must be active, recently observed, current-configured, and read-only ready;
- admission accepts only the startup registry's `synthetic_read_review_v1` template ID; caller
  objective/title/summary fields are rejected;
- safe responses omit template payload text from inventory, detail, audit, logs, errors, telemetry,
  and evidence exports;
- cancellation of queued work is atomic, idempotent, and cannot imply runner stop;
- unauthorized, stale, revoked, drifted, below-minimum, and evidence-incomplete cases have zero
  mission effects;
- API tests cover duplicate-key JSON rejection and unknown-field rejection.

## MCC-003 — Signed Node Claim

Objective: let only the assigned Node claim one queued mission through the existing signed-request
contract, with a bounded durable claim-expiry attention timer and no runner launch.

Acceptance evidence:

- current Node/configuration/policy/manifest/workspace bindings are revalidated atomically;
- nonce replay remains denied across Gateway restart;
- concurrent claims yield one claim and one delivered envelope;
- another Node, revoked/stale Node, expired claimant, partitioned Node, or stale configuration cannot
  claim, and claim expiry enters `claim_expired_review_required` without requeue;
- claim audit failure exposes no completed claim or envelope;
- returned envelope contains no host-control field.

## MCC-004 — Runner-Reported Lifecycle And Cancellation

Objective: accept closed Node-signed runner reports, preserve their source, and make cancellation
races explicit without treating them as Gateway execution truth.

Acceptance evidence:

- report IDs are idempotent for identical bodies and conflicting for drifted bodies;
- every report binds mission ID, claim ID, envelope digest, expected lifecycle revision, and the
  signing key actually verified;
- authenticated receipt is separate from lifecycle advancement; stale, revoked, drifted,
  below-minimum, partition-recovering, or otherwise ineligible reports are durably quarantined with
  receipt-time posture and never advance Gateway state;
- lifecycle transitions follow the architecture state machine;
- no automatic reassignment occurs after a claim, running report, or ambiguous evidence state;
- output is limited to closed outcome/reason codes and digest references; free-form summaries are
  rejected;
- the Node polls a signed `continue` or `cancel_requested` control decision bound to claim ID,
  envelope digest, and lifecycle revision, then acknowledges the exact decision revision;
- cancellation request, cancellation observation, late success, failure, restart, partition, key
  rotation, and revocation transcripts are deterministic and auditable.

## MCC-005 — Command Center Mission And Fleet Cockpit

Objective: make Command Center the authoritative operator surface for mission admission, delivery,
and truth-source-aware fleet correlation.

Acceptance evidence:

- a dedicated new-mission flow targets one eligible Gateway Node and one server-owned synthetic
  template;
- mission inventory distinguishes Gateway state, Node delivery, quarantined evidence, runner report,
  governed Agent Runs, and unknown provider state;
- cancel controls explain recorded, observed, and runner-reported states without process-stop claims;
- stale, evidence-incomplete, config-drift, claim-expiry, quarantine, and report-conflict states
  route into Attention with keyboard-accessible remediation guidance;
- UI tests cover accessible names, focus, loading/error/empty states, and delayed-response binding.

## MCC-006 — Adversarial POC And Exact-Candidate Review

Objective: prove the bounded control plane on one exact candidate without a runner launch claim.

Required evidence:

- live synthetic admission, Node claim, running/succeeded reports, and Agent Run correlation;
- real Gateway restart; durable admission/report replay denial; partition denial; cancellation race;
- revocation, stale heartbeat, config drift, below-minimum version, evidence failure, concurrent
  claim, retired-key report, and quarantined late-report negative transcripts;
- interruption evidence before audit insert, after JSONL append, after audit commit, and before/after mission finalization;
- audit chain verification and redaction scan with no template payload or runner output leakage;
- `make agent-workflow-check`, focused mission gates, `make release-check`, and
  `make review-candidate` pass on the exact candidate;
- independent Sol xhigh source review records no unresolved critical/high finding.

This ticket may record only `mission_control_plane_candidate_ready_for_external_review`. It does not
authorize production deployment, runner launch, release, or UAT acceptance.

## Later Separate Capability

A fixed Hermes runner bridge is intentionally outside `MCC-001` through `MCC-006`. Its future
decision must define the exact process/container boundary, executable provenance, prompt custody,
resource limits, cancellation semantics, and non-bypass claims before any runtime adapter work.

<!-- mission-command-contract:start -->
{"document_type":"implementation_tickets","schema_version":"1","tool_count":24,"ordered_tickets":["MCC-001","MCC-002","MCC-003","MCC-004","MCC-005","MCC-006"],"runtime_starts_after_review":true,"database_schema_version":"4","minimum_writer_version":"4","evidence_commit_protocol_required":true,"late_report_quarantine_required":true,"signed_cancel_poll_required":true,"freeform_objective_authorized":false,"runner_bridge_authorized":false,"sol_ultra_authorized":false}
<!-- mission-command-contract:end -->
