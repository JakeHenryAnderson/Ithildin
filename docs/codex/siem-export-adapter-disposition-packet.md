# SIEM Export Adapter Disposition Packet

Status: external architecture-disposition handoff packet for `ERG-008` and
`PRD-SIEM-EXPORT-001`.

Current governed tool count: `24`.

Current `ERG-008` status: `planning_only`.

This packet defines the review question for Ithildin's future SIEM-shaped export adapter lane. It
asks whether the current design-only event schema, redaction, delivery, compatibility, signing, and
diagnostics evidence is coherent enough to continue architecture planning, or whether the lane needs
revision before any post-RC implementation decision can be drafted.

This packet does not approve SIEM adapter runtime behavior, hosted telemetry, remote delivery,
custody-grade audit claims, external notarization, immutable storage, production identity, runtime
Postgres, compliance automation, security-operations control-plane claims, public/security-product
positioning, API endpoints, MCP tools, tool manifests, policy rules, executors, sandbox
orchestration, local model invocation, trusted-host promotion, shell, Docker/Kubernetes/browser
governed powers, arbitrary HTTP, broad filesystem writes, plugin SDK behavior, or new governed tool
powers.

Validate this packet with:

```sh
make siem-export-adapter-disposition-packet-check
make siem-export-adapter-disposition-closure-check
```

Generate the focused disposition handoff with:

```sh
make siem-export-adapter-disposition-packet
```

Record reviewer responses with
[siem-export-adapter-external-response-intake.md](siem-export-adapter-external-response-intake.md)
and validate the intake template with:

```sh
make siem-export-adapter-external-response-intake-check
```

## Required Reviewer Question

A reviewer should answer:

Is the current SIEM-shaped export adapter architecture evidence coherent enough for continued
planning, or must Ithildin revise the event schema, redaction policy, delivery boundary,
compatibility model, signing story, retry/backpressure behavior, and safe-error diagnostics before
any implementation decision is considered?

Allowed reviewer dispositions:

- `continue_architecture_planning`: the current evidence is coherent for more design, static
  fixtures, compatibility tests, schema examples, and review packets.
- `revise_before_more_planning`: the evidence has missing architecture questions, ambiguous
  delivery authority, unsafe event fields, weak failure-mode coverage, or unclear signing
  expectations that should be fixed before more planning.
- `block_runtime_implementation`: a blocking adapter, custody, telemetry, or evidence-leak risk
  prevents implementation planning until a later decision record resolves it.

## Current Evidence Set

The reviewer should inspect:

| Evidence | Source |
| --- | --- |
| Adapter architecture packet | `siem-export-adapter-architecture.md` |
| SIEM-shaped evidence design | `siem-shaped-evidence-design.md` |
| Fail-closed closure gate | `siem-export-adapter-disposition-closure-gate.md` |
| Evidence contracts | `evidence-contracts.md` |
| Post-RC decision register | `post-rc-decision-register.md` |
| Enterprise gap matrix | `enterprise-readiness-gap-matrix.md` |
| Enterprise runway | `enterprise-readiness-runway.md` |
| Accepted-risk register | `accepted-risk-register.json` |
| No-new-powers evidence | `make no-new-powers-guardrail` and `make tool-surface-invariant-gate` |

## Required Architecture Focus

Before implementation planning, the lane needs clear answers for:

- target adapter type and local-only versus remote delivery posture;
- supported event schema version and compatibility policy;
- event category allowlist and required fields;
- redaction rules, denylist rules, and no-export behavior for blocked sensitive fields;
- batch size, event size, export window, and queue limits;
- retry, dead-letter, and backpressure behavior;
- destination authentication model without exposing secrets;
- signing, verification, and key-loss story;
- clock/timestamp ordering and idempotency/replay handling;
- operator-visible diagnostics and safe failure summaries;
- external/source review requirements before any SIEM integration, delivery, or security-operations
  ingestion claim.

## Required Boundary Flags

Current output must continue to report:

- SIEM adapter allowed: `false`;
- hosted telemetry allowed: `false`;
- remote delivery allowed: `false`;
- custody-grade audit claims allowed: `false`;
- external notarization allowed: `false`;
- immutable storage allowed: `false`;
- production identity allowed: `false`;
- runtime Postgres allowed: `false`;
- compliance claims allowed: `false`;
- security-operations control-plane claims allowed: `false`;
- new power classes allowed: `false`;
- closes `ERG-008`: `false`.

## Required Negative Review Focus

The disposition review should look for:

- event fields that could expose prompts, secrets, file contents, diffs, response bodies, package
  script values, dependency names, raw sensitive paths, raw tool arguments, model output, private key
  material, bearer tokens, cookies, environment variables, connection strings, local database
  contents, raw sandbox internals, or unredacted identity-provider/user-directory claims;
- delivery language that implies remote transmission, hosted telemetry, or destination credentials
  are implemented today;
- retry or dead-letter language that implies unbounded queues or undisclosed local storage;
- signing language that implies external notarization, official custody, or stronger trust roots
  than local operator keys;
- wording that implies SIEM custody, compliance automation, or security-operations control-plane
  authority;
- missing compatibility, failure-mode, redaction, or safe-error expectations.

## Current Allowed State

This packet supports architecture docs, schema sketches, static examples, compatibility-test
planning, review packets, and operator warning design. It does not close `ERG-008`, and it does not
authorize SIEM adapter runtime behavior. A later post-RC decision record must record reviewer
disposition before any implementation plan moves.
Normalized responses must also pass
[siem-export-adapter-disposition-closure-gate.md](siem-export-adapter-disposition-closure-gate.md)
before a later triage update may consider an architecture decision record.
