# Compliance Mapping Disposition Packet

Status: external architecture-disposition packet for `ERG-009`.

This packet prepares the compliance mapping support lane for reviewer disposition. It does not add
runtime behavior, API endpoints, MCP tools, tool manifests, policy rules, executors, sandbox
orchestration, SIEM adapter behavior, hosted telemetry, production identity, runtime Postgres, legal
conclusions, compliance automation, automated certification, public security-product positioning, or
any new governed tool power.

Current governed tool count: `24`.

Current `ERG-009` status: `planning_only`.

Post-RC decision ID: `PRD-COMPLIANCE-MAPPING-001`.

## Purpose

The compliance mapping architecture in
[compliance-mapping-architecture.md](compliance-mapping-architecture.md) defines future template,
evidence, operator-responsibility, and legal-review questions. This disposition packet asks whether
that architecture is coherent enough to continue design-only planning.

The intended reviewer answer is a narrow disposition, not an implementation approval.

## Allowed Reviewer Dispositions

- `continue_architecture_planning`: the current architecture evidence is coherent enough for more
  design-only planning, fixtures, packet work, and decision-record preparation.
- `revise_before_more_planning`: the architecture has claim, template, evidence, legal-boundary, or
  operator-responsibility gaps that should be fixed before more planning.
- `block_runtime_implementation`: a blocking issue prevents implementation planning until a future
  post-RC decision record resolves it.

## Review Focus

Reviewers should inspect:

- target framework/control-family boundary;
- mapping-template shape and required fields;
- evidence-field allowlist and denylist;
- operator responsibility language;
- legal-review boundary;
- accepted-risk impact;
- incident reconstruction support for mediated actions only;
- false-assurance and unsupported-control warnings;
- prohibition on automated certification and regulated-industry compliance claims.

## Boundary Flags

The disposition packet must preserve these flags:

```json
{
  "tool_count": 24,
  "erg_009_status": "planning_only",
  "prd_id": "PRD-COMPLIANCE-MAPPING-001",
  "runtime_changes_allowed": false,
  "compliance_mapping_planning_allowed": true,
  "compliance_mapping_runtime_allowed": false,
  "compliance_automation_allowed": false,
  "legal_advice_allowed": false,
  "automated_certification_allowed": false,
  "regulated_industry_compliance_claims_allowed": false,
  "custody_grade_audit_allowed": false,
  "production_identity_allowed": false,
  "runtime_postgres_allowed": false,
  "siem_adapter_allowed": false,
  "sandbox_orchestration_allowed": false,
  "new_power_classes_allowed": false,
  "public_security_product_positioning_allowed": false,
  "closes_erg_009": false
}
```

## What This Packet Does Not Prove

This packet does not prove external architecture review has happened, does not close `ERG-009`, does
not approve runtime compliance mapping, and does not prove Ithildin satisfies any regulation or
contractual framework.

It also does not approve legal advice, compliance automation, automated certification, custody-grade
audit, production identity, runtime Postgres, SIEM adapter runtime behavior, sandbox orchestration,
public/security-product positioning, or any new governed tool power.

## Required Before Runtime Work

Before any runtime compliance mapping feature can be considered, a later decision record must
provide:

- exact framework/control-family scope and version;
- mapping-template schema and fixtures;
- evidence-field allowlist and denylist tests;
- unsupported-control and non-applicability fixtures;
- operator responsibility and legal-review text;
- accepted-risk impact review;
- review-console expectations, if any;
- source-review handoff;
- external/source review disposition.

## Validation

Run:

```sh
make compliance-mapping-disposition-packet-check
make compliance-mapping-disposition-packet
make compliance-mapping-architecture-check
make control-mapping-design-check
make incident-reconstruction-check
```
