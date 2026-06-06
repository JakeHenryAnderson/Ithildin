# Control Mapping Design

Status: design-only proposal. This document does not add runtime behavior, tool manifests,
executors, policy rules, API endpoints, MCP tools, UI editing, sandbox controls, SIEM adapters,
production identity, runtime Postgres, hosted telemetry, shell, Docker, Kubernetes, browser
automation, plugin SDKs, arbitrary HTTP, or broad filesystem writes.

This design describes how Ithildin evidence may later support operator control mapping. It is
control mapping support only. It is not HIPAA, GLBA, SOX, GDPR, or other regulatory compliance
automation, and it does not certify that an organization satisfies any control framework.

## Mapping Areas

The required mapping areas are least privilege, approval-required writes, restricted network destinations, sensitive-resource labeling, evidence export, denied destructive actions, and incident reconstruction.

| Control objective | Ithildin evidence that may support mapping |
| --- | --- |
| Least privilege | Trusted manifests, role-aware tool visibility, policy decisions, and denied tool attempts. |
| Approval-required writes | Stored patch proposal, approval binding evidence, one-time consumption, and patch diagnostics. |
| Restricted network destinations | Exact allowlist configuration, `http.fetch` policy/resource evidence, redirect denial, and audit events. |
| Sensitive-resource labeling | Future trusted local data labels from [data-classification-design.md](data-classification-design.md). |
| Evidence export | Audit JSONL, locally signed audit export bundles, review packet hashes, and command transcripts. |
| Denied destructive actions | Dangerous/destructive risk policy denials and no-new-powers/tool-surface guardrails. |
| Incident reconstruction | Agent Run records, audit events, approvals, diagnostics, signed exports, and future SIEM-shaped evidence. |

## Design Rules

- A mapping must name the Ithildin-mediated action or evidence field it relies on.
- A mapping must describe what the evidence can prove and what it cannot prove.
- A mapping must not claim OS-level containment, model intent, human identity proof, external
  notarization, custody-grade retention, or activity outside Ithildin.
- A mapping must link to tests, review docs, or operator commands that produce the evidence.
- A mapping must keep prompts, secrets, file contents, diffs, response bodies, package script values,
  dependency names, and raw sensitive paths out of generated evidence unless separately reviewed.

## Non-Claims

Control mapping support is not:

- compliance automation;
- a HIPAA, GLBA, SOX, GDPR, or regulatory certification;
- a SIEM-grade custody system;
- a sandbox or endpoint protection product;
- production identity or enterprise RBAC;
- proof of actions outside Ithildin-mediated tools.

Future policy packs may say they support a control objective only after a separate proposal, policy
fixtures, evidence contracts, review-console expectations, negative transcripts, accepted-risk
impact review, and external/source review.

## Review Gate

Run:

```text
make control-mapping-design-check
```

The gate verifies this design, review-doc/docs-site wiring, README linkage, roadmap linkage, and the
no-new-powers boundary.
