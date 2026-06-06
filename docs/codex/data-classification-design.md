# Data Classification Design

Status: design-only proposal. This document does not add runtime behavior, tool manifests,
executors, policy rules, API endpoints, MCP tools, UI editing, automatic discovery, sandbox
controls, SIEM adapters, production identity, runtime Postgres, hosted telemetry, shell, Docker,
Kubernetes, browser automation, plugin SDKs, arbitrary HTTP, or broad filesystem writes.

This proposal defines trusted local data labels that Ithildin can use later as policy inputs and UI
warnings for operator-managed workspaces and resources. The labels are local configuration intent,
not automatic classification and not a compliance claim.

## Labels

Future workspace/resource metadata may use these labels:

| Label | Intended meaning |
| --- | --- |
| `public` | Information already approved for public disclosure. |
| `internal` | Organization- or household-internal material. |
| `confidential` | Sensitive material requiring stronger review and evidence. |
| `PII` | Personal data that may identify a person. |
| `PHI` | Health-related data that may require organizational controls. |
| `client data` | Client, customer, or account-specific data. |
| `regulated financial data` | Financial data that may map to regulatory control objectives. |
| `secrets-adjacent` | Material near secrets, credentials, private keys, tokens, or secret-bearing config. |

Labels are intentionally coarse. A later implementation should prefer explicit trusted local
configuration; this proposal uses trusted local configuration as the only acceptable source until
automatic discovery is separately reviewed.

## Future Use

The first acceptable runtime uses, when separately approved, are:

- policy inputs that can require approvals, deny network access, or increase audit evidence for
  sensitive labels;
- review-console UI warnings that show an operator when a run, resource, or workspace carries a
  sensitive label;
- secret-free evidence fields that record label names and trusted config source without exporting
  file contents, prompts, diffs, response bodies, package script values, dependency names, or raw
  sensitive paths.

## Non-Goals

This proposal does not:

- discover labels automatically;
- edit labels through the UI;
- change policy decisions at runtime;
- classify file contents, prompts, diffs, HTTP responses, packages, or dependencies;
- export sensitive values to SIEM-shaped evidence;
- make HIPAA, GLBA, SOX, GDPR, or other compliance claims;
- claim sandboxing, SIEM-grade custody, production security control, production identity, or
  custody-grade evidence.

Any implementation must pass a separate proposal, executor/resource contract review where relevant,
policy fixtures, negative transcripts, accepted-risk impact review, and external/source review before
labels affect behavior.

## Review Gate

Run:

```text
make data-classification-design-check
```

The gate verifies this proposal, review-doc/docs-site wiring, README linkage, roadmap linkage, and
the no-new-powers boundary.
