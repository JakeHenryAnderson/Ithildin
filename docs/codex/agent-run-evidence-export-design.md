# Agent Run Evidence Export Design

Status: design-only export contract. This document prepares a future Agent Run evidence export
bundle shape, but it does not add runtime behavior, API endpoints, MCP tools, executors, policy
rules, UI controls, SIEM adapters, sandbox controls, production identity, runtime Postgres, hosted
telemetry, shell, Docker, Kubernetes, browser automation, arbitrary HTTP, broad filesystem writes,
or plugin SDK work.

## Purpose

The future export should let an operator collect the secret-free evidence for one mediated Agent Run
without scraping unrelated dashboards or raw audit files. The bundle is for local review and
incident reconstruction of Ithildin-mediated actions only. It is not a claim of sandboxing,
SIEM-grade custody, compliance automation, production security, or activity outside Ithildin.

## Proposed Bundle

A future Agent Run evidence export bundle should contain:

- `schema_version`: stable export schema version.
- `export_id`: local export identifier.
- `exported_at`: UTC timestamp.
- `run`: safe Agent Run summary.
- `timeline`: ordered secret-free run events.
- `approvals`: correlated approval lifecycle summaries.
- `patch_diagnostics`: read-only patch apply diagnostic summaries when present.
- `signed_export_references`: local signed audit export references when present.
- `evidence_hashes`: SHA-256 digests for exported sections.
- `redaction_summary`: counts and categories only.
- `warnings`: local-preview warning states.

The `run` object should include `run_id`, `principal_id`, `workspace_id`, optional `sandbox_id`,
`session_id`, `model_client_label`, `status`, `policy_hash`, `manifest_lock_hash`,
`tool_call_count`, `created_at`, and `updated_at`.

The `timeline` entries should include `event_id`, `run_id`, `timestamp`, `category`, `status`,
`correlation_id`, optional `tool_name`, optional `approval_id`, optional `audit_event_id`,
optional `policy_hash`, optional `manifest_hash`, and safe status metadata. Categories should align
with the Agent Run Evidence Contract: run lifecycle, tool lifecycle, policy decision, approval
lifecycle, executor result, audit verification, signed export, redaction summary, diagnostics, and
sandbox/workspace posture.

## Exclusions

The export must not include prompts, model output, model reasoning, raw tool arguments, file contents,
diffs, response bodies, secrets, bearer tokens, cookies, package script values,
dependency names, raw sensitive paths, private key material, local environment files, runtime
SQLite databases, or raw audit JSONL unless separately reviewed and explicitly requested.

## Evidence Relationship

The future export should point to, but not replace:

- the [Agent Run Evidence Contract](agent-run-evidence-contract.md);
- the [Incident Reconstruction Guide](incident-reconstruction-guide.md);
- the [Dashboard Evidence Review Checklist](dashboard-evidence-review-checklist.md);
- the [SIEM-Shaped Evidence Design](siem-shaped-evidence-design.md);
- the [Signed Audit Exports](signed-audit-exports.md) guide.

Signed audit exports remain local authenticity and integrity evidence only. Agent Run exports should
not imply external notarization, hosted custody, immutable evidence, or SIEM-grade retention.

## Future Review Requirements

Before implementation, a follow-up task must provide:

- API shape and authorization review;
- fixture export bundle and negative transcript examples;
- policy/audit/resource evidence fields;
- redaction and size-limit tests;
- signed-export interaction tests;
- dashboard review expectations;
- external/source review for the export implementation.

Run `make agent-run-evidence-export-check` to validate that this design remains linked, secret-free
in posture, and design-only.
