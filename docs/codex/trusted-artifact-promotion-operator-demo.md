# Trusted Artifact Promotion Operator Demo

Status: walkthrough-ready demo runway for the bounded `ERG-005` staging-only trusted-host
promotion runtime slice.

This document defines the operator-facing story for promoting one sandbox/workspace-produced
artifact into a configured trusted-host staging area. It is a demo and evidence contract, not a
new power class.

## Purpose

The demo should let an operator see the complete path:

1. A sandbox/workspace-side artifact exists with safe metadata and a SHA-256 digest.
2. Ithildin records an approval-bound promotion proposal for exactly that artifact digest and
   destination label.
3. A one-time approval authorizes one create-exclusive staging placement.
4. Ithildin independently verifies staged bytes against the approved digest.
5. Audit, proposal, approval, and packet evidence show what happened without exposing file
   contents, raw sensitive paths, prompts, secrets, or broad host filesystem state.

## Command Center Boundary

Ithildin Command Center is the operator display and review surface. It may show status, evidence,
warnings, and next actions, but it does not become the promotion engine or a second enforcement
point. Ithildin remains the governed gateway/source of truth for policy, approval binding,
promotion execution, audit evidence, and diagnostics.

## Demo Story

The first story is deliberately small:

- artifact label: `hello-world-summary.txt` or equivalent fixture label;
- source zone: sandbox/workspace artifact evidence;
- staging zone: configured local trusted-host staging root;
- operation: create one new staged file only;
- digest: SHA-256 computed before proposal and verified after staging;
- review: operator inspects safe metadata and approval binding evidence;
- export: packet and audit evidence prove the digest-bound placement.

## Operator Reading Order

1. `00_TRUSTED_ARTIFACT_PROMOTION_OPERATOR_DEMO_INDEX.md`
2. `01_GUIDED_OPERATOR_FLOW.md`
3. `02_COMMAND_CENTER_FRAMING.md`
4. `03_DEMO_SCENARIO.md`
5. `04_EVIDENCE_MAP.md`
6. `05_LIVE_WALKTHROUGH_PREP.md`
7. `06_BOUNDARY_FLAGS.md`
8. `trusted-artifact-promotion-operator-demo-artifact-hashes.json`

## Walkthrough Commands

Prepare the packet and known-good evidence:

```sh
make trusted-artifact-promotion-operator-demo
make trusted-artifact-promotion-operator-demo-check
make sandbox-artifact-observed-demo
make trusted-host-promotion-negative-transcripts
make trusted-host-promotion-runtime-source-review-bundle
```

Then use the packet at:

```text
var/review-packets/v3/trusted-artifact-promotion-operator-demo/
```

The packet tells the operator what to run next and what evidence should exist before attempting
any live/manual walkthrough.

## Acceptance Boundary

This demo does not add governed tools, manifests, policy rules, API endpoints, MCP tools,
Command Center runtime authority, sandbox orchestration, VM/container lifecycle management,
local model invocation, SIEM adapters, production identity, runtime Postgres, hosted telemetry,
remote MCP, shell execution, Docker/Kubernetes/browser powers, arbitrary HTTP, broad filesystem
writes, approved-output publishing, compliance automation, or public/security-product claims.

The only implemented runtime slice it may describe is the existing `ERG-005` staging-only
single-artifact promotion path: one stored artifact, one operator proposal, one one-time approval,
one create-exclusive placement into configured local host staging, and read-only diagnostics/evidence.

## Validation

Use:

```sh
make trusted-artifact-promotion-operator-demo-check
```

The check must confirm:

- Tool count remains `24`;
- the packet is generated without starting services or calling governed tools;
- the Command Center stays display/review-only;
- no broad host promotion is claimed;
- docs-site, review-doc, README, and release-check wiring are present;
- packet artifact hashes cover generated files without hashing the hash manifest itself.
