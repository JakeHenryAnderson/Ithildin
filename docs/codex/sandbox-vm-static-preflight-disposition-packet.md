# Sandbox/VM Static Preflight Disposition Packet

Status: external-disposition packet plan for `ERG-003`.

This packet is the handoff layer for recording an external/source-review disposition of the
CLI-only sandbox/VM static preflight lane. It packages the source-review packet pointer,
disposition questions, response-intake template, response dry-run evidence, and command evidence
needed for a reviewer to say whether the static preflight lane can move from
`external_review_required` to
`closed_local_preview_static_preflight`.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Current `ERG-003` status before reviewer disposition: `external_review_required`.

This packet does not close `ERG-003` by itself. It does not approve live VM/container inspection,
VM/container lifecycle management, sandbox orchestration, Mission Control runtime behavior, local
model invocation, trusted-host promotion, network expansion, API/MCP profile loading, new governed
tools, production identity, runtime Postgres, hosted telemetry, remote MCP, SIEM delivery,
compliance automation, or public/security-product positioning.

## Packet Purpose

Generate a compact reviewer handoff under
`var/review-packets/v3/sandbox-vm-static-preflight-disposition/` that includes:

- the exact `ERG-003` disposition questions;
- the `EXT-SVP-###` finding namespace;
- source-review packet path and artifact-hash guidance;
- the response-intake normalization command;
- the response dry run proving absent, packet-only, bad-hash, critical/high, and direct-closure
  response cases fail closed while a source-level favorable response can become closure-ready for
  later triage;
- command evidence for the static-preflight source-review packet and disposition checks;
- explicit reminder that a later committed triage update is required to move `ERG-003`.

## Required Reviewer Question Set

The generated packet must ask the reviewer:

1. Did the reviewer inspect the static preflight source-review packet and source files named in that
   packet?
2. Does the CLI-only fixture runner stay within the approved boundary?
3. Are the static profile fixture contract and negative fixtures sufficient for local-preview
   planning evidence?
4. Are safe-label and safe-error expectations strong enough for packet/display use?
5. Does `XH-SANDBOX-PREFLIGHT-001` appear fixed for the local-preview fixture lane?
6. Are there any critical/high findings?
7. Does the response dry run prove absent responses stay not-ready, source-level favorable
   responses are accepted for later triage, and packet-only, bad-hash, critical/high, and direct
   external-closure attempts are rejected?
8. If there are no critical/high findings, can `ERG-003` move from `external_review_required` to
   `closed_local_preview_static_preflight`?
9. Does the reviewer explicitly avoid approving live VM/container control, Mission Control runtime
   behavior, local model invocation, trusted-host promotion, or production/security-product claims?

## Required Generated Artifacts

The generated disposition packet must contain:

- `00_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_INDEX.md`
- `01_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_PROMPT.md`
- `02_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_AND_INTAKE.md`
- `03_SANDBOX_VM_STATIC_PREFLIGHT_SOURCE_REVIEW_POINTERS.md`
- `04_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_COMMAND_EVIDENCE.md`
- `sandbox-vm-static-preflight-disposition-artifact-hashes.json`

## Validation

Run:

```sh
make sandbox-vm-static-preflight-disposition-packet-check
```
