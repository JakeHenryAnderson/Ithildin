# Compliance Mapping Response Dry Run

Status: temporary fixture dry run for the planning-only `ERG-009` closure gate.

Validation command:

```sh
make compliance-mapping-response-dry-run
```

This dry run exercises favorable and unfavorable normalized-response fixtures against
`compliance-mapping-disposition-closure-gate.md` without recording external review, mutating
committed findings, or approving implementation. It writes temporary JSON fixtures to:

```text
var/review-runs/compliance-mapping/normalized-response.json
```

The original ignored response path is restored before the command exits.

## Cases Exercised

The dry run checks:

- absent normalized response remains valid but not closure-ready;
- source-level response with `disposition_outcome: continue_architecture_planning` can report
  `ready_for_architecture_decision_record`;
- packet-only response is rejected;
- invalid reviewed packet hash is rejected;
- critical/high finding is rejected;
- direct `closes_external_review: true` is rejected.

## Boundaries Preserved

The dry run always reports:

```text
committed_findings_mutated: false
external_review_recorded: false
erg_009_closed: false
architecture_planning_recorded: false
implementation_planning_allowed: false
runtime_changes_allowed: false
compliance_mapping_runtime_allowed: false
compliance_automation_allowed: false
legal_advice_allowed: false
automated_certification_allowed: false
regulated_industry_compliance_claims_allowed: false
public_security_product_positioning_allowed: false
```

It also keeps production identity, runtime Postgres, SIEM adapter behavior, hosted telemetry,
remote delivery, sandbox orchestration, local model invocation, trusted-host promotion,
shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem writes,
plugin SDK behavior, and new governed tool powers blocked.

## What This Does Not Prove

This is not an external review, legal review, compliance certification, control attestation,
custody-grade audit proof, or implementation approval. A favorable dry-run fixture only proves that
the local fail-closed closure gate can distinguish acceptable normalized response shapes from
unacceptable ones.

Any real movement of `ERG-009` still requires a separate committed triage update that cites the
reviewed packet hash, cites closure-gate output, preserves reviewer findings in the normal finding
workflow, and keeps runtime work blocked until a later post-RC decision record approves a specific
implementation plan.
