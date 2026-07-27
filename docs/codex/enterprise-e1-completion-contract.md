# Ithildin Enterprise Track E1 Completion Contract

Status: active implementation contract. Outcomes complete: `2/6`. Milestones complete: `2/6`.

The machine-readable authority is
[`enterprise-e1-completion-contract.json`](enterprise-e1-completion-contract.json). Validate it
from the repository root:

```sh
make enterprise-e1-contract-check
make enterprise-e1-milestone-check
```

This track starts from source commit
`0ef2fae9a06da7455a25017e5773caa52e7c8db6` on
`origin/codex/lv1-007-candidate-uat`. The inherited frozen Local v1 runtime candidate remains
`ab4162d8f4b6d3f45a68f33316f4b765a45765db`. Enterprise work occurs only on an isolated
descendant branch and does not change Local v1 candidate, review, UAT, or release disposition.

## Fixed milestone order

| Milestone | Outcome | Current state |
| --- | --- | --- |
| `E1-M1` | `E1-O1` - Reproducible single-site deployment | `complete` |
| `E1-M2` | `E1-O2` - Versioned policy and Node-configuration distribution | `complete` |
| `E1-M3` | `E1-O3` - Safe upgrade, rollback, and recovery | `in_progress` |
| `E1-M4` | `E1-O4` - Authoritative mission and fleet operations cockpit | `not_started` |
| `E1-M5` | `E1-O5` - Bounded operational evidence export | `not_started` |
| `E1-M6` | `E1-O6` - Exact candidate qualification and UAT handoff | `not_started` |

Milestones advance in this order. A later outcome may reuse or inspect existing behavior, but it
does not become complete before the preceding checkpoint is complete.

## Reuse audit and remaining work

### E1-O1 - Reproducible single-site deployment

Reuse `deploy/docker-compose.yml`, `deploy/README.md`, the stdlib runtime-candidate bootstrap, and
the Local v1 operations rehearsal. E1 adds
[`deploy/single-site/`](../../deploy/single-site/README.md): a versioned API/UI profile,
owner-only closed environment and state bootstrap, authenticated loopback health/status probe,
fixed shutdown path, static deployment checkpoint, and isolated observed rehearsal.
[`enterprise-e1-m1-observed-results.md`](enterprise-e1-m1-observed-results.md) binds the passing
build, start, 24-tool health, shutdown, retained-state observation, and cleanup receipt to exact
source commit `1300f2d046f0f255c6a1a5206f0a9d318f36d24a`. The runtime posture remained explicitly
`unreviewed_local`; this is deployment-candidate provenance, not E1 candidate qualification.
E1-O1 and E1-M1 are complete. E1-M3 will reuse the substrate for its separate upgrade and recovery
outcome.

### E1-O2 - Versioned policy and Node-configuration distribution

E1 reuses the existing signed per-Node configuration generations, server-derived Node/workspace
binding, private local storage, acknowledgment, offline enforcement, staleness rejection, trust
rotation, and manual rollback-as-fresh-generation behavior.
[`enterprise-e1-configuration-state-contract.md`](enterprise-e1-configuration-state-contract.md)
defines the checked policy/configuration bundle and keeps desired, acknowledged, stored, enforced,
stale, rejected, and rollback states distinct.
[`enterprise-e1-m2-observed-results.md`](enterprise-e1-m2-observed-results.md) binds the focused
authenticated checkpoint to exact commit `e15c524804f6b7d16704db3f4124eed2bda89a01`.
No new governed tool or arbitrary host control was added. E1-O2 and E1-M2 are complete.

### E1-O3 - Safe upgrade, rollback, and recovery

Reuse Local v1 candidate-bound backup, failed-start, restore, restart, and evidence-preservation
machinery plus the database migration-backup helper. E1 still needs compatibility validation and a
supported rehearsal spanning Gateway, Command Center, and optional Node continuity. Ambiguous
ownership must remain a stop condition; cleanup cannot be inferred safe.
This is the active `E1-M3` checkpoint.

### E1-O4 - Authoritative mission and fleet operations cockpit

Reuse Command Center mission, fleet, configuration cohort, version cohort, approvals, attention,
run correlation, evidence, and terminology work. Prior Command Center UAT artifacts remain
lineage, not E1 qualification. The E1 checkpoint must prove accessible operator flow and preserve
the distinction between Gateway truth, Node connectivity, runner-reported state, and unknown
model-provider state. Command Center remains a presentation and initiation surface over existing
Gateway-governed workflows.

### E1-O5 - Bounded operational evidence export

Reuse signed local audit export, Agent Run evidence export, enterprise display-status export, and
packet redaction checks. None is the required unified E1 operations bundle. The E1 export must be
deterministic, receiver-neutral, locally verifiable, redacted, and cover deployment,
configuration, upgrade/rollback, mission, fleet, approvals, and audit evidence without claiming
whole-host coverage, SIEM custody, hosted telemetry, external notarization, or compliance
automation.

### E1-O6 - Exact candidate qualification and UAT handoff

Reuse Local v1 candidate-gate patterns only as implementation lineage. E1 requires its own exact
candidate, dedicated gate, proportional independent review, and concise human UAT packet.
Automated checks and reviews remain evidence only. Genuine human UAT stays false and is the final
stop line.

## Frozen boundaries and nonclaims

The governed tool count remains exactly `24`. Ithildin gains no arbitrary shell, browser, process,
Docker-socket, Kubernetes, broad filesystem, or arbitrary-network authority. Local operator
Compose commands do not become Gateway Docker authority.

This contract does not claim production identity, runtime PostgreSQL, high availability, hosted
operation, whole-host coverage, SIEM custody, hosted telemetry, external notarization, compliance
automation, enterprise production readiness, Local v1 release acceptance, or human UAT completion.

The PIS lane remains at
`await_external_operator_target_and_signed_receipt_inputs_before_separate_collection_action_authority`.
External inputs and collection-action authority are false. Do not select a target, inspect
credentials, consume a DSN, load a driver, connect, migrate, manage a service, or fabricate
receipts.

## Candidate and UAT gates

An E1 candidate is not qualified until all six outcomes and milestones are complete against one
exact clean commit, the dedicated candidate gate passes, and the proportional independent review
is recorded with its own evidence. A usable UAT packet may then be prepared. The implementation
lane stops before genuine human UAT and does not mark production readiness, Local v1 acceptance,
or public security-product readiness complete.
