# Threat Model and Non-Goals

Ithildin v0.1 is a local-preview governed MCP gateway. It is designed to reduce the blast radius of
local AI tool use by mediating tool calls through manifests, schema validation, trusted local
principal labels, policy, approval, scoped executors, redaction, and tamper-evident audit logs.

## Trust Model

- The agent or local model is untrusted.
- The local host, local admin, trusted manifests, trusted policies, and Ithildin process are part of
  the local trusted computing base.
- The review console is security-sensitive admin UI.
- The MCP stdio adapter is an ingress adapter; it must stay thin and delegate governance to the
  shared pipeline.
- SQLite and JSONL audit files are local evidence, not independent durable custody.

## In Scope

- Prevent direct agent access to raw filesystem, shell, Docker, Kubernetes, browser, or arbitrary
  network capabilities.
- Enforce narrow tool schemas, scoped paths, exact HTTP allowlists, policy decisions, and approval
  gates.
- Produce local tamper-evident audit records that can reconstruct governed decisions.
- Fail closed when manifests, policy evidence, principal registry, approval state, or configured
  storage mode are invalid.

## Non-Goals

- Ithildin is not a kernel sandbox, EDR, MDM, SIEM, production identity provider, hosted MCP server,
  managed model platform, or compliance-grade immutable audit store.
- Local principals are attribution labels and local policy inputs, not enterprise authentication.
- Redaction is best-effort leak reduction, not a guarantee that secrets cannot be exposed.
- Hash-chained audit is tamper-evident local evidence, not external notarization.
- Postgres settings are readiness evidence only; SQLite is the only v0.1 runtime backend.

## Deferred Security Work

- Production identity integration such as OIDC, SAML, SCIM, tenant isolation, and managed sessions.
- Signed manifests, signed audit exports, and external audit anchoring.
- Runtime Postgres storage adapters and migrations.
- Stronger OS sandboxing/containerized execution.
- Remote MCP transports and hosted control-plane deployment.
