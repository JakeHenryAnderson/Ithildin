# Post-RC Decision Register

Status: current register for post-v1.0 RC boundary decisions.

This register records the active post-RC lane decisions that govern the next enterprise-readiness
steps. It is a status source of truth, not an approval to add runtime behavior. Any entry that moves
from planning to implementation still requires a dedicated decision record, implementation plan,
source-review or external-review evidence, tests, gates, packet artifacts, and an explicit go/no-go
outcome.

The broader enterprise gap map is
[enterprise-readiness-gap-matrix.md](enterprise-readiness-gap-matrix.md). This register records the
current lane decision status; the matrix records the claim/capability each unresolved gap blocks.

Current governed tool count: `24`.

Current selected capability: `not selected`.

## Register Rules

- `approved_for_planning` allows documentation, schema sketches, static fixtures, review packets,
  and source-review preparation only.
- `no_go` blocks runtime behavior and may allow design cleanup or packet preparation only when the
  allowed scope says so.
- No entry in this register approves manifests, executors, policy/rule changes, API/MCP behavior,
  approval/audit behavior, UI runtime behavior, Mission Control runtime behavior, sandbox
  orchestration, local model invocation, trusted-host promotion, SIEM adapters, production identity,
  runtime Postgres, hosted telemetry, remote MCP, plugin SDK behavior, compliance automation,
  public/security-product positioning, broad filesystem writes, or arbitrary network expansion.
- A lane must stay blocked if its allowed scope, forbidden scope, required evidence, accepted-risk
  impact, and operator warning language are incomplete.

## Current Decisions

| Decision ID | Lane | Status | Allowed next action | Runtime allowed | Required next evidence |
| --- | --- | --- | --- | --- | --- |
| `PRD-MC-DISPLAY-001` | Mission Control display importer continuation | `approved_for_planning` | Prepare display-only schema, packet, static fixtures, and source-review handoff | `false` | Mission Control-side review packet and implementation plan before runtime importer work |
| `PRD-SANDBOX-PREFLIGHT-001` | Live sandbox/VM preflight | `no_go` | Continue static fixture evidence and source-review disposition only | `false` | Separate live-preflight decision record, implementation plan, and external/source review |
| `PRD-SANDBOX-LIVE-POC-001` | Live sandbox/VM worker proof of concept | `no_go` | Maintain the decision-intake packet and wait for favorable `ERG-003` disposition | `false` | Favorable static-preflight disposition, live POC decision record, implementation plan, cleanup/failure transcripts, and external/source review |
| `PRD-CAPABILITY-001` | New governed tool after RC freeze | `no_go` | Candidate selection and design packet only | `false` | Capability proposal, implementation plan, source-review handoff, negative transcripts, and accepted-risk update |
| `PRD-TRUSTED-HOST-001` | Trusted-host promotion lane | `no_go` | Promotion state-machine design and evidence contract discussion only | `false` | Artifact hash-binding model, approval model, negative transcripts, and external/source review |
| `PRD-SIEM-EXPORT-001` | SIEM-shaped export adapter lane | `no_go` | Stable schema and offline export design only | `false` | Delivery model, redaction policy, compatibility tests, and external/source review |

## Decision Details

### PRD-MC-DISPLAY-001

- Status: `approved_for_planning`.
- Current allowed scope: display-only import planning for labels, hashes, warnings, links, run IDs,
  approval IDs, local-preview status, and packet versions.
- Current forbidden scope: Mission Control execution authority, policy authority, approval authority,
  audit authority, local-model runner behavior, VM/container management, sandbox orchestration,
  trusted-host promotion, file mutation, runtime importer behavior, and production identity.
- Current implementation posture: runtime behavior remains blocked.
- Current warning language: Mission Control remains an evidence display/import planning surface only.
- Current decision-intake evidence:
  `mission-control-display-decision-intake.md` defines the preconditions, allowed outcomes, negative
  evidence, and forbidden authority claims before any runtime importer decision can be recorded.

### PRD-SANDBOX-PREFLIGHT-001

- Status: `no_go`.
- Current allowed scope: static fixture evidence, source-review disposition, docs, review packets,
  negative fixture planning, and operator warnings.
- Current forbidden scope: live VM/container inspection, SSH, shell, Docker socket access,
  Kubernetes tools, local model invocation, sandbox orchestration, trusted-host promotion, runtime
  preflight runner behavior, production identity, and remote control-plane behavior.
- Current implementation posture: live runtime behavior remains blocked.
- Current warning language: Ithildin does not start, inspect, or manage VMs/containers in this lane.

### PRD-SANDBOX-LIVE-POC-001

- Status: `no_go`.
- Current allowed scope: decision-intake evidence in
  `sandbox-vm-live-poc-decision-intake.md`, favorable `ERG-003` disposition tracking,
  decision-record drafting, docs, review packets, and operator warnings.
- Current forbidden scope: live VM/container inspection, local model invocation, Mission Control
  runtime behavior, sandbox orchestration, SSH, shell, Docker socket access, Kubernetes tools,
  browser automation, arbitrary HTTP, broad filesystem writes, trusted-host promotion, runtime
  profile loading, production identity, SIEM adapters, and public/security-product positioning.
- Current implementation posture: live worker runtime behavior remains blocked.
- Current warning language: Ithildin does not run a local model, inspect a live VM/container,
  orchestrate a sandbox, or promote sandbox artifacts in this lane.

### PRD-CAPABILITY-001

- Status: `no_go`.
- Current allowed scope: candidate selection, design packet, proposal, risk analysis, source-review
  request, and implementation plan draft.
- Current forbidden scope: manifest addition, executor code, policy/rule semantics, MCP/API
  behavior, approval behavior, audit behavior, UI runtime behavior, runtime storage changes, local
  model invocation, sandbox orchestration, and trusted-host promotion.
- Current implementation posture: no new governed tool is approved by this register.
- Current warning language: post-RC capability work remains design-only until a separate record
  approves implementation.

### PRD-TRUSTED-HOST-001

- Status: `no_go`.
- Current allowed scope: design-only discussion of source/destination zones, artifact hashes,
  approval binding, replay denial, conflict handling, and operator warnings.
- Current forbidden scope: direct host writes, overwrite/delete/move behavior, broad archive
  extraction, automatic promotion, promotion without exact artifact hash binding, and promotion
  without approval evidence.
- Current implementation posture: trusted-host promotion remains blocked.
- Current warning language: sandbox outputs may be described as staged evidence only, not promoted
  host artifacts.

### PRD-SIEM-EXPORT-001

- Status: `no_go`.
- Current allowed scope: stable event schema design, redaction policy design, offline export shape,
  compatibility tests, and source-review preparation.
- Current forbidden scope: hosted telemetry by default, custody-grade audit claims, stronger audit
  guarantee claims, compliance automation claims, and exporting prompts, file contents, diffs,
  response bodies, secrets, dependency names, package scripts, raw sensitive paths, or raw sandbox
  internals.
- Current implementation posture: SIEM adapter work remains blocked.
- Current warning language: Ithildin may support control mapping and evidence export design, not
  SIEM custody or automated compliance.

## Validation

Run:

```sh
make post-rc-decision-register-check
make post-rc-decision-record-examples-check
make post-rc-decision-gate
```

All checks must remain green before `make release-check` can pass.
