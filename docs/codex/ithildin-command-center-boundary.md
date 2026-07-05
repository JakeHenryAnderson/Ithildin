# Ithildin Command Center Boundary

Status: current product-naming and authority-boundary note.

`Ithildin Command Center` is the current name for the operator-facing control-plane and dashboard
concept that earlier planning docs often called `Mission Control`. Historical filenames, generated
packet paths, and compatibility-oriented docs may continue to use `mission-control` names until a
separate migration is worth the churn. Current-facing docs should prefer `Ithildin Command Center`
when describing the operator UI.

## Role Split

- `Ithildin Gateway`: the governed MCP/tool gateway and enforcement point.
- `Ithildin Command Center`: the operator UI/control-plane surface for reviewing state, evidence,
  approvals, packets, run timelines, diagnostics, and handoff material.
- `Workbench`: the operator workspace inside Command Center for active runs, artifacts, evidence
  review, and demo flows.
- `Evidence`: audit events, signed exports, source-review packets, diagnostics, transcripts, and
  reconstruction material generated or verified by Ithildin.
- `Sandbox and staging`: operator-managed workspace, sandbox, staging, and approved-output zones.
  Ithildin may record or verify bounded evidence for these zones only when an explicit reviewed
  runtime slice exists.

## Authority Rules

Command Center does not become a second enforcement point. It may display Ithildin state, prepare
operator requests, and submit reviewed operator actions through existing Ithildin APIs. It must not:

- execute governed tools outside the gateway;
- bypass policy, manifests, approval state, or audit recording;
- create or complete approvals independently of Ithildin approval APIs;
- mutate audit logs, signed evidence, review packets, diagnostics, or closure records;
- write arbitrary host files or promote artifacts without an approved Ithildin runtime slice;
- start VMs, containers, local models, shells, Docker, Kubernetes, browsers, or network clients;
- claim production identity, SIEM custody, compliance automation, sandboxing, or public/security
  product readiness.

## Current ERG-005 Implication

The staging-only trusted-host promotion slice remains an Ithildin Gateway API capability. Command
Center may eventually display its proposals, approvals, diagnostics, and evidence, but Command
Center is not the promotion engine and does not receive trusted-host runtime authority.

The current ERG-005 state is: staging-only local-preview runtime implemented and internally reviewed;
focused external/source disposition remains pending before any broader trusted-host promotion,
approved-output publishing, or Command Center-host integration.

