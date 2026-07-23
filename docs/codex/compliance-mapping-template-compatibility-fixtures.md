# Compliance Mapping Template Compatibility Fixtures

Status: static planning-only compatibility corpus for `CMT-001` and `ERG-009`.

Current governed tool count: `24`.

This packet freezes a synthetic, non-regulatory template shape for testing the design mechanics
required by the compliance mapping architecture. It does not select a real framework, interpret a
law or contract, claim that an organization satisfies a control, or authorize runtime compliance
mapping.

## Frozen Inputs

- `tests/fixtures/compliance_mapping/valid-template-v1.json` is the canonical synthetic template.
- `tests/fixtures/compliance_mapping/compatibility-corpus.json` is the closed case inventory.
- The checker verifies the exact byte hashes and exact two-file fixture inventory.
- Every case is materialized in memory from an independent deep copy and is never written.

The framework family and control references are deliberately synthetic. They are test vocabulary,
not substitutes for HIPAA, GLBA, SOX, GDPR, NIST, CIS, SOC 2, or another external framework.

## Contract

The template uses the closed schema `ithildin.control_mapping_template.v1`. Every row names:

- a mapping ID and synthetic control reference;
- a controlled objective and evidence source;
- allowlisted safe evidence fields;
- operator input, evidence support, and what the evidence does not prove;
- freshness, review cadence, applicability, confidence, and review-console expectation;
- accepted-risk references; and
- an allowlisted verification command and packet pointer.

The template-level operator-responsibility and legal-review objects remain explicit. All authority
flags remain false.

## Corpus

`CMT-COMP-001` through `CMT-COMP-003` are accepted examples covering supported, unsupported, and
not-applicable rows. `CMT-COMP-004` through `CMT-COMP-024` reject:

- `duplicate_json_member`;
- `unknown_template_field` and `unknown_row_field`;
- `unsupported_template_schema`;
- `real_framework_not_allowed`;
- `legal_review_boundary_weakened`;
- `authority_expansion`;
- `forbidden_evidence_field`;
- `unknown_evidence_field`;
- `missing_evidence_limitation`;
- `applicability_confidence_mismatch`;
- `unsafe_verification_reference`;
- `invalid_accepted_risk_reference`;
- duplicate mapping IDs and control references;
- `prohibited_claim_text`;
- `non_finite_number`; and
- `invalid_unicode`;
- arbitrary or sensitive limitation values;
- evidence-source/support mismatches; and
- verification command/pointer cross-pairs.

The checker reports only the safe reason label. It never includes rejected keys or values in its
report.

## Authority Boundary

This corpus:

- does not select a real framework or version;
- does not change `PRD-COMPLIANCE-MAPPING-001` beyond `approved_for_planning`;
- does not close `ERG-009`;
- does not authorize runtime mapping, compliance automation, legal advice, certification, external
  claims, custody-grade audit, production identity, release, promotion, or UAT;
- does not add API, UI, policy, persistence, network, credential, service, container, or tool
  behavior; and
- does not authorize new power classes.

## Validation

Run:

```sh
make compliance-mapping-template-compatibility-check
make compliance-mapping-architecture-check
make control-mapping-design-check
make accepted-risk-register-check
make no-new-powers-guardrail
make tool-surface-invariant-gate
```
