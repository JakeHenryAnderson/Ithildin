# Compliance Mapping Architecture

Status: design-only architecture packet for `ERG-009`.

This document defines the future architecture questions Ithildin must answer before it can offer
formal compliance mapping support. It does not add runtime behavior, control-pack execution, API
endpoints, MCP tools, tool manifests, policy rules, executors, sandbox orchestration, SIEM adapter
behavior, hosted telemetry, production identity, runtime Postgres, legal conclusions, compliance
automation, public security-product positioning, or any new governed tool power.

Current governed tool count: `24`.

Current selected capability: `not selected`.

## Scope

This packet covers `ERG-009`: Compliance mapping support.

The existing [control-mapping-design.md](control-mapping-design.md) defines the current
control-objective mapping support boundary. The existing
[incident-reconstruction-guide.md](incident-reconstruction-guide.md) defines how operators can
reconstruct Ithildin-mediated actions. This architecture packet defines the additional template,
responsibility, legal-review, evidence, and claim-boundary requirements that must exist before any
formal compliance mapping feature is implemented or shared as a regulated-industry artifact.

## Current Boundary

The current v1.0 local-preview boundary remains:

- control mapping support, not HIPAA, GLBA, SOX, GDPR, or other regulatory compliance;
- mediated-action reconstruction, not proof of activity outside Ithildin;
- local evidence exports, not custody-grade audit;
- operator responsibility language, not legal advice;
- design packets and review artifacts, not automated certification.

## Future Compliance Mapping Questions

Before implementation, a future decision record must define:

- target framework or control family: HIPAA, GLBA, SOX, GDPR, NIST, CIS, SOC 2, or another explicit
  mapping scope;
- control objective taxonomy and versioning policy;
- evidence source inventory and field-level mapping rules;
- operator responsibility language;
- legal-review boundary and reviewer role expectations;
- accepted-risk impact for local principals, audit custody, sandbox posture, and identity/storage
  gaps;
- evidence freshness, retention, and export requirements;
- mapping confidence labels and unsupported-control handling;
- false-positive and false-assurance warnings;
- reviewer-visible gaps and non-applicability reasons;
- change-control process for template updates.

## Mapping Template Requirements

A future mapping template must be explicit and narrow. Each row must include:

- mapping ID and framework/control reference;
- control objective label;
- Ithildin evidence source;
- safe evidence fields used;
- required operator input or attestation, if any;
- what the evidence can support;
- what the evidence cannot prove;
- freshness and review cadence;
- unsupported or not-applicable conditions;
- accepted-risk references;
- verification command or packet pointer.

Template rows must not infer compliance from a green test, a signed export, a denial event, or a
local-preview review result. They may only say that specific Ithildin evidence supports an operator
mapping for a named objective.

## Evidence Sources

Future mappings may cite only secret-free, reviewable evidence such as:

- Agent Run lifecycle records;
- policy decision evidence;
- approval lifecycle evidence;
- executor result evidence;
- denied destructive-action evidence;
- patch diagnostics and recovery evidence;
- audit verification results;
- locally signed audit export metadata;
- review packet hashes;
- source-review closure rows;
- accepted-risk dispositions;
- sandbox/workspace posture labels;
- future SIEM-shaped evidence categories.

## Evidence Non-Goals

Compliance mapping artifacts must not include prompts, secrets, file contents, diffs, response
bodies, package script values, dependency names, raw sensitive paths, raw tool arguments, model
output, private key material, bearer tokens, cookies, environment variables, connection strings,
local database contents, raw sandbox internals, raw IdP claims, raw user-directory data, legal
advice, patient/client records, or regulated data values.

## Operator Responsibility Model

Future mapping support must make the operator boundary visible:

- Ithildin may show that a mediated action was allowed, denied, approved, exported, or verified.
- Ithildin may show that a control mapping row references evidence and known gaps.
- The operator remains responsible for choosing the framework, validating applicability, reviewing
  legal obligations, configuring retention, and deciding whether external audit evidence is
  sufficient.
- A legal/compliance reviewer remains responsible for any claim that an organization satisfies a
  regulation or contractual control.

## Required Before Implementation

A future implementation sprint must have:

- post-RC decision record for `ERG-009`;
- exact mapping scope and framework version;
- mapping-template schema and fixture examples;
- legal-review boundary text;
- operator responsibility language;
- evidence-field allowlist and denylist tests;
- unsupported-control and non-applicability fixtures;
- accepted-risk impact review;
- review-console expectations;
- source-review handoff;
- external/source review before any regulated-industry mapping feature, compliance-support packet,
  or public claim is shipped.

## Explicit Non-Goals

This packet does not approve:

- compliance automation;
- HIPAA, GLBA, SOX, GDPR, SOC 2, NIST, CIS, or other compliance claims;
- legal advice;
- automated certification;
- production security-product positioning;
- custody-grade audit claims;
- external notarization;
- immutable storage;
- production identity;
- runtime Postgres;
- SIEM adapter runtime behavior;
- sandbox orchestration;
- public/security-product positioning.

## Current Decision

The current decision is `planning_only`.

Template discussion, control-objective taxonomy, evidence-field design, operator-responsibility
language, legal-review boundary drafting, and review packets may continue. Runtime compliance
mapping implementation remains blocked until a separate post-RC decision record approves a specific
implementation plan.

## Validation

Run:

```sh
make compliance-mapping-architecture-check
make control-mapping-design-check
make incident-reconstruction-check
make enterprise-readiness-gap-matrix-check
make post-rc-decision-register-check
```
