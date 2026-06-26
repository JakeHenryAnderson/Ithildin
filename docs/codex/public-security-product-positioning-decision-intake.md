# Public/Security-Product Positioning Decision Intake

Status: decision-intake planning packet for `ERG-010` and `PRD-PUBLIC-POSITIONING-001`.

Current governed tool count: `24`.

Current `ERG-010` status: `blocked`.

Current selected capability: `not selected`.

This intake defines the evidence required before any future post-RC decision record may reconsider
Ithildin's public/security-product positioning. It does not approve broader public distribution,
production deployment readiness, security-product positioning, sandbox claims, EDR/MDM claims, SIEM
custody claims, compliance claims, production identity, runtime Postgres, hosted telemetry, remote
MCP, hosted MCP, plugin SDK behavior, compliance automation, shell/Docker/Kubernetes/browser
governed powers, arbitrary HTTP, broad filesystem writes, or new governed tool powers.

public/security-product positioning remains blocked.

Validate this intake with:

```sh
make public-security-product-positioning-decision-intake-check
```

## Current Decision

The current decision remains:

- continued local-preview development: `go`;
- limited technical-preview sharing with warning packet: `conditional_go`;
- broad public/security-product positioning: `no_go`;
- production/security/compliance positioning: `no_go`;
- capability implementation: `no_go` unless a separate post-RC implementation decision explicitly
  approves one bounded lane.

## Required Preconditions

Any future decision record that revisits `PRD-PUBLIC-POSITIONING-001` must prove:

- independent external/source review disposition exists for every row that the proposed claim
  depends on;
- accepted deferred risks are either closed, explicitly accepted for the exact claim, or called out
  as claim blockers;
- production identity, tenant/workspace authorization, session/admin model, and audit attribution
  are either implemented and reviewed or explicitly excluded from the claim;
- durable storage, retention, backup/restore, migration, and evidence custody boundaries are either
  implemented and reviewed or explicitly excluded from the claim;
- sandbox/VM posture, local model invocation, and trusted-host promotion are either implemented and
  reviewed or explicitly excluded from the claim;
- SIEM/export adapter behavior and compliance mapping behavior are either implemented and reviewed
  or explicitly excluded from the claim;
- support model, deployment model, update model, incident-response path, and operator warning
  language are explicit;
- release evidence includes same-commit `make release-check`, `make review-candidate`, packet
  redaction `findings: 0`, and no open critical/high findings;
- claim text has been reviewed for forbidden overclaims and matches the implemented, reviewed
  runtime boundary.

## Required Evidence

A future decision record must link:

- `v0.8-public-preview-risk-review.md`;
- `v0.8-final-decision-packet.md`;
- `v1.0-rc-final-handoff.md`;
- `v1.0-rc-readiness-gate.md`;
- `v1.0-assurance-closure.md`;
- `enterprise-readiness-gap-matrix.md`;
- `post-rc-decision-register.md`;
- `accepted-risk-register.json`;
- source-review closure matrix evidence for the exact rows supporting the claim;
- external/source review response artifacts for the exact rows supporting the claim;
- updated README/release/website/UI wording proposed for review.

## Explicitly Forbidden Claim Categories Until A Future Decision Changes This

Do not claim or imply:

- production deployment ready wording;
- sandbox guarantee language;
- security product;
- EDR/MDM agent;
- SIEM custody;
- compliance tool;
- regulatory-grade audit;
- custody-grade audit;
- tamper-proof logging;
- audit immutability;
- production identity;
- enterprise RBAC;
- hosted MCP;
- remote MCP transport/gateway claims;
- hosted telemetry;
- runtime Postgres;
- managed model serving;
- arbitrary-tool safety wording;
- broad autonomous execution;
- HIPAA/GLBA/SOX/GDPR/SOC 2/NIST/CIS compliance;
- automated certification;
- legal advice;
- public/security-product positioning.

## Allowed Current Wording

Current docs may continue to describe Ithildin as:

- a local-preview governed MCP/tool gateway;
- a bounded local operator workbench for mediated agent tool calls;
- a local evidence and approval gateway with narrow built-in tools;
- a local technical preview suitable for reviewers and security-conscious developers who understand
  the local-preview trust model.

All current wording must keep the warning that Ithildin is not production software, not a sandbox,
not EDR/MDM, not SIEM custody, not a compliance system, not production identity, and not a hosted
control plane.

## Stop Conditions

Stop the lane and keep `ERG-010` blocked if:

- any proposed wording claims production/security/compliance readiness without the exact evidence
  above;
- any required external/source review row remains pending for the claim being made;
- any critical/high finding remains open;
- accepted deferred risks are not dispositioned against the exact claim;
- the proposed claim depends on production identity, runtime Postgres, SIEM adapter behavior,
  sandbox orchestration, trusted-host promotion, hosted telemetry, remote MCP, local model
  invocation, or compliance mapping runtime behavior that has not been implemented and reviewed;
- the proposed wording cannot be made understandable without hiding local-preview limitations.

## Validation

Run:

```sh
make public-security-product-positioning-decision-intake-check
make v08-public-preview-decision
make v1-rc-readiness
make v1-assurance-closure-check
make post-rc-decision-register-check
```
