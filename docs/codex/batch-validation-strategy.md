# Ithildin Batch Validation Strategy

Status: checked batch validation strategy for controlled, lane-bounded development.

This strategy exists to keep Ithildin moving quickly without lowering its evidence bar. It allows
controlled batches when the work shares one lane, one authority boundary, and one validation surface.
It rejects broad mixed-authority batches that would make failures hard to diagnose.

## Validation Tiers

| Tier | Purpose | Typical commands | What it proves |
| --- | --- | --- | --- |
| Tier 1: inner loop | Fast feedback while editing one lane. | `make validation-decision-run ARGS="changed files..."`, focused pytest nodes, `make lint`, `make typecheck` | The changed slice is locally coherent. |
| Tier 2: batch checkpoint | Validate a completed lane-bounded batch. | `make status-now`, `make enterprise-status-slice`, `make handoff-dry-run`, lane-specific dry runs and closure gates | The lane is coherent with current generated evidence. |
| Tier 3: handoff freeze | Freeze release or review evidence. | `make release-check`, `make review-candidate`, `make artifact-freshness-check` | Full local handoff evidence matches the current commit. |

## Safe Batch Shapes

Safe batches are small groups of changes with the same validation surface.

- `ERG-003` packet/response-preflight docs plus static sandbox/VM response-kit checks.
- `ERG-002` Mission Control display/import planning docs plus fixture/import checks.
- Technical MVP execution-board and status-command wiring.
- One bounded read-only capability from proposal through implementation and source-review handoff.
- One response-intake lane from raw response to dry-run to disposition packet.

## Unsafe Batch Shapes

Do not batch these together:

- sandbox/VM runtime authority plus Mission Control runtime behavior;
- trusted-host promotion plus broad filesystem or artifact movement changes;
- identity/storage architecture plus public-positioning claims;
- SIEM adapter design plus compliance automation wording;
- runtime code, policy semantics, manifests, and public claims in the same sprint unless a specific
  implementation plan authorizes that exact combination.

## Batch Done Criteria

A batch is complete only when:

1. The changed files are listed.
2. The relevant Tier 1 checks pass.
3. The lane-specific Tier 2 checks pass.
4. The board row status is updated or explicitly left unchanged.
5. No blocked authority is newly allowed.
6. A Tier 3 freeze is run only if the batch changes handoff or release evidence.

## Recommended Current Batches

| Batch | Status | Use now? | Fast validation |
| --- | --- | --- | --- |
| Technical MVP execution-board cleanup | done | no | `make technical-mvp-execution-board`, `make roadmap-status` |
| `ERG-004` live-POC runtime implementation-gate prep | active resume checkpoint | yes | `make sandbox-vm-live-poc-runtime-ticket-internal-review-check`, `make sandbox-vm-live-poc-runtime-implementation-gate-check` |
| `ERG-003` response intake | blocked on response | not until response arrives | `make sandbox-vm-static-preflight-response-dry-run` |
| `ERG-002` response intake | blocked on response | not until response arrives | `make mission-control-display-response-dry-run` |
| live sandbox/VM POC | blocked on `ERG-003` | no | `make sandbox-vm-live-poc-preconditions-ready-check` |

## Practical Rule

If a change only updates docs or scripts for one lane, use Tier 1 and Tier 2. If a change updates
runtime authority, policy semantics, manifests, public claims, or review packets that will be sent,
finish the batch with Tier 3. If a full gate fails because of generated artifact staleness, refresh
only the documented artifacts; do not rewrite product claims to make the gate pass.
