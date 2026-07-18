# Mission Command Control Plane Architecture

Status: approved architecture for the bounded synthetic mission admission and Node-delivery slice.

Current governed tool count: `24`.

## Purpose

Command Center needs a real control-plane object that begins before an Agent Run. A **mission** is
the administrator's admitted intent and delivery lifecycle. An **Agent Run** remains evidence of
governed tool activity that actually reached Ithildin. The two may correlate, but neither fabricates
the other.

```text
authenticated administrator
        |
        v
Command Center -> Gateway mission admission -> durable queued mission
                                              |
                              signed Node claim and reports
                                              |
                                              v
                                       enrolled Ithildin Node
                                              |
                                  closed local runner handoff
                                              |
                                              v
                                  externally managed runner/model
```

The first implementation stops at a durable Node claim and runner-report boundary. A later,
separately reviewed adapter ticket may prove a fixed Hermes handoff. No ticket in this packet grants
generic process or container control.

## Truth Ownership

| Fact | Authority | Meaning |
| --- | --- | --- |
| mission ID, requester, target, workspace, admitted payload digest | Gateway | server-derived durable mission identity |
| queued, canceled, claim issued/expired, report receipt | Gateway | control-plane decisions and accepted protocol events |
| mission envelope stored locally | Node report | authenticated Node statement, not runner enforcement |
| accepted, running, succeeded, failed, cancellation observed | runner-reported through Node | observation from the external execution side |
| governed tool activity | Gateway Agent Run/audit evidence | only calls that traversed Ithildin |
| runner process health | runner/provider system | unknown unless a later bounded integration supplies evidence |
| model inference, tokens, chain of thought, correctness | model provider/runner | outside Ithildin custody and authority |

Command Center must render the authority source beside every state. It must never collapse Gateway
`cancel_requested` into `runner_stopped`, or Node `runner_reported_succeeded` into `output_verified`.

## Mission Admission Envelope

The bounded public request contains:

- `target_node_id`;
- `mission_template_id`, selected from the startup-only server registry and initially limited to
  `synthetic_read_review_v1`;
- `requested_timeout_seconds`, within a closed range;
- `client_request_id`, a caller-generated idempotency label.

The Gateway derives and persists:

- random `mission_<32 lowercase hex>` identity;
- authenticated requester principal and role generation;
- Node-derived workspace and principal identity;
- desired Node configuration generation and digest;
- template registry generation, immutable template payload digest, and canonical envelope digest;
- timestamps, lifecycle revision, evidence status, and current authority state.

The request rejects unknown, revoked, stale, evidence-incomplete, below-minimum,
configuration-drifted, or non-read-only-ready Nodes. The client cannot choose title, objective,
workspace, principal, policy digest, manifest digest, runner executable, provider, endpoint,
environment, or host resource. Template payloads are repo-owned synthetic fixtures, loaded once at
startup, hash-bound into admission, and never sourced from the request.

## Lifecycle State Machine

```text
unadmitted
  -> queued
  -> claimed
  -> runner_reported_running
  -> runner_reported_succeeded | runner_reported_failed

queued -> canceled
claimed | runner_reported_running -> cancel_requested
cancel_requested -> runner_reported_canceled | runner_reported_succeeded | runner_reported_failed
claimed -> claim_expired_review_required

any transition evidence interruption -> prior lifecycle state + evidence_incomplete transition
```

`admission_pending_evidence` and `claim_pending_evidence` are transition-attempt statuses, not
authoritative mission lifecycle states. Admission remains `unadmitted` until the queued transition
finalizes. Claim remains `queued` until the claimed transition finalizes.

Rules:

- a mission has one target Node and one immutable admitted envelope;
- one atomic claim exists at a time;
- claim expiry moves the mission to `claim_expired_review_required`; delivery may have succeeded
  even when no later report arrived, so expiry never returns a mission to `queued`;
- no claimed or running mission is automatically reassigned under any condition;
- cancellation prevents a new claim but does not erase accepted or quarantined reports;
- terminal reports are append-only and idempotent by report ID and exact body digest;
- conflicting replay fails closed;
- operator retry or clone is always a new mission ID.

## Evidence Commit Protocol

Mission lifecycle state and evidence status are separate axes. Every state-changing admission,
claim, cancellation, control acknowledgment, and report follows this ordering:

1. In one SQLite transaction, insert an immutable transition attempt containing `transition_id`,
   mission ID, prior lifecycle state/revision, proposed state/revision, request digest, safe metadata,
   and `evidence_status = pending`. Do not advance the mission's authoritative lifecycle state.
2. Commit the staged transition before calling the existing audit writer.
3. Append an audit event that describes the **staged proposal**, including the transition ID and
   request digest. It must not claim the proposed state is complete.
4. After the audit writer has durably completed its own JSONL and SQLite work, capture the returned
   event ID and event hash.
5. In a new `BEGIN IMMEDIATE` mission transaction, revalidate the unchanged prior lifecycle
   revision, bind the exact audit event ID/hash to the staged transition, mark transition evidence
   complete, and only then advance the mission lifecycle state/revision.
6. Return an admitted mission, delivery envelope, cancellation completion, or accepted terminal
   transition only after step 5 commits.

If any boundary fails, the prior lifecycle state/revision remains unchanged. The
transition is retained as `evidence_incomplete` when that can be recorded safely; otherwise the
pending row itself forces fail-closed recovery. A pending or incomplete transition blocks later
state changes. Recovery is not automatic. Tests interrupt before audit insertion, after JSONL
append, after audit SQLite commit, and immediately before and after mission finalization.

## Signed Node Protocol

Mission claim, control polling, and report calls reuse `ITHILDIN-NODE-V1` canonical request signing
and durable nonce consumption. The Gateway additionally binds a new claim to:

- current Node identity and non-revoked status;
- recent accepted heartbeat;
- exact desired and acknowledged configuration generation/digest;
- current policy and manifest-lock digests;
- minimum Node software version;
- Node-derived workspace.

The Node receives the server-owned synthetic template payload only after all claim bindings pass.
A partition cannot produce a new claim or lifecycle-advancing report. Offline execution is not
authorized by the mission envelope.

Every claim has a Gateway-derived `claim_id`, claim revision, envelope digest, Node identity key ID,
and immutable authority snapshot. Every report carries the mission ID, claim ID, envelope digest,
expected lifecycle revision, report ID, closed report kind, closed outcome/reason code, and optional
artifact digest.

Report handling has two separate paths:

1. **Authenticated receipt:** verify the signature using the Node's current evidence-complete key or,
   after revocation, the retained last evidence-complete public key; consume a report receipt nonce;
   bind the report to the original claim and envelope; and stage append-only receipt evidence.
2. **Lifecycle advancement:** only after receipt evidence finalizes, revalidate the Node's current
   non-revoked, recently observed, configuration, policy, manifest, version, workspace, and identity
   posture plus the expected lifecycle revision. Eligible reports may stage a lifecycle transition.
   A valid report from a stale, revoked, drifted, below-minimum, rotation-incomplete, or otherwise
   ineligible Node is quarantined with its receipt-time posture and never advances Gateway state.

Identity-key rotation remains acceptable only when the report verifies with the current
evidence-complete key for the same Node identity. A report signed by a retired key is denied, even if
that key originally claimed the mission. Revocation retains the last public key solely for
quarantined evidence receipt; it does not restore action authority.

## Cancellation Delivery Protocol

After claim, the Node polls a signed mission-control read for its claim ID and last observed
lifecycle revision. The Gateway returns only the current control decision (`continue` or
`cancel_requested`), decision revision, mission ID, claim ID, and envelope digest. The Node reports
`cancel_observed` with that exact decision revision before it may report `runner_reported_canceled`.

Gateway `cancel_requested` means only that the decision was durably recorded. `cancel_observed`
means only that the authenticated Node acknowledged the decision. Neither means a runner stopped.
Polling, acknowledgment, and cancellation reports use the evidence commit protocol and exact-body
idempotency.

## Data Minimization And Evidence

The first slice is technically synthetic-only: public admission accepts only a server-owned template
ID, and the template registry contains repo-reviewed synthetic payloads. The mission database stores
the template ID, registry generation, and payload digest; it does not duplicate template text.
Inventory, detail, audit, logs, errors, telemetry, and evidence exports never include template
payload text.

Runner reports may contain only closed status/outcome/reason codes, timestamps, an optional output
artifact digest, and correlation labels. Free-form summaries, raw model output, prompt transcripts,
chain of thought, credentials, hostnames, usernames, IP addresses, environment variables, and raw
paths are excluded.

Mission metadata and transition evidence use the existing configured retention boundary in this
local-preview slice. Node-local claim state is stored only in the exclusive mode-`0600` Node state
directory and retains template ID/digest plus lifecycle identifiers, not template payload text after
handoff. Production retention and deletion remain a later production-storage decision.

## Restart, Replay, Partition, And Cancellation Semantics

- SQLite state and nonce consumption survive Gateway restart.
- Admission idempotency is uniquely namespaced by `(requester_principal_id,
  requester_identity_generation, client_request_id)`. Those server-derived requester fields are
  included in the canonical admission digest. The same namespace and exact digest returns the
  original mission; a different body or authority generation conflicts or creates a separately
  namespaced request rather than retrieving another authority generation's mission.
- A repeated claim nonce is denied after restart.
- A repeated report ID with the same body is idempotent; a different body conflicts.
- Gateway partition means no new mission authority. The Node may retain an already claimed envelope
  but its later activity is runner-reported and cannot use governed tools while Node posture is
  stale or configuration authority is unavailable.
- Claim-response ambiguity is fail-closed: expiry produces operator review, never automatic requeue.
  A retry or clone receives a new mission ID and preserves the original history.
- Cancellation races preserve both the Gateway cancellation decision and any later authenticated
  runner report; the UI explains the disagreement instead of rewriting history.
- Audit failure preserves the prior lifecycle state and leaves a pending or `evidence_incomplete`
  transition that blocks further transitions until a separately reviewed recovery path exists.

## Coordinated Migration And Downgrade

Mission tables and constraints join the central SQLite migration as schema version `4` with minimum
writer version `4`. The single migration transaction creates and verifies mission, claim, report
receipt, and transition-attempt tables before updating version metadata. Startup creates a
pre-migration backup receipt, interrupted DDL rolls back completely, and every writer refuses a
database whose minimum writer is newer than itself.

Downgrade is restore-only: a version-3 binary must refuse the upgraded database. Operators restore
the pre-migration version-3 database copy rather than destructively rewriting version-4 tables.
Tests cover interrupted upgrade rollback, full schema/constraint verification, old-writer refusal,
backup receipt verification, and restore-only downgrade startup.

## Deployment Boundary

This slice uses the existing local-preview API/Node deployment topology. It adds no listening port
to the Node, no Docker socket, no host process namespace, no broad filesystem mount, and no remote
transport claim. A future operator-managed runner bridge must use a closed profile and a bounded
Node-owned state directory; it cannot accept arbitrary commands from mission content.

## Non-Claims

Mission admission does not mean a runner started. Claim does not mean inference began. A Node report
does not prove runner behavior, model correctness, filesystem isolation, or complete observation.
Agent Runs prove only governed calls that reached Ithildin. The architecture is not production
identity, multi-tenancy, endpoint management, EDR/MDM, SIEM custody, or compliance automation.

<!-- mission-command-contract:start -->
{"document_type":"architecture","schema_version":"1","database_schema_version":"4","minimum_writer_version":"4","tool_count":24,"mission_template_ids":["synthetic_read_review_v1"],"freeform_objective_allowed":false,"freeform_report_summary_allowed":false,"lifecycle_states":["unadmitted","queued","claimed","runner_reported_running","runner_reported_succeeded","runner_reported_failed","canceled","cancel_requested","runner_reported_canceled","claim_expired_review_required"],"transition_attempt_statuses":["admission_pending_evidence","claim_pending_evidence"],"evidence_statuses":["pending","complete","evidence_incomplete"],"admission_idempotency_namespace":["requester_principal_id","requester_identity_generation","client_request_id"],"claim_expiry_requeues":false,"quarantined_reports_advance_lifecycle":false,"runner_bridge_authorized":false,"arbitrary_host_control_authorized":false}
<!-- mission-command-contract:end -->
