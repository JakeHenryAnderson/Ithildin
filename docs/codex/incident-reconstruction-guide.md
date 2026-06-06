# Incident Reconstruction Guide

Status: operator/reviewer guide. This document does not add runtime behavior, tool manifests,
executors, policy rules, API endpoints, MCP tools, UI controls, sandbox controls, SIEM adapters,
production identity, runtime Postgres, hosted telemetry, shell, Docker, Kubernetes, browser
automation, plugin SDKs, arbitrary HTTP, or broad filesystem writes.

This guide describes how an operator can reconstruct an Ithildin-mediated agent run from existing
and future evidence. It covers mediated actions only. It cannot prove activity outside Ithildin,
activity performed directly by a model client, host process behavior, OS-level containment, human
identity proof, or custody-grade retention.

## Evidence Sources

Reconstruction uses Agent Run records, audit events, approvals, patch diagnostics, signed exports,
and future SIEM-shaped evidence.

Use these sources together:

| Source | What it contributes |
| --- | --- |
| Agent Run records | Run ID, principal ID, workspace ID, optional sandbox ID, status, and correlated tool/audit/approval IDs. |
| Audit events | Policy decisions, executor lifecycle, denials, approvals, diagnostics, verification head, and redaction summary evidence. |
| Approvals | Requesting principal, approving principal, one-time scope, proposal hash, policy/manifest evidence, expiry, and consumption status. |
| Patch diagnostics | Patch apply attempts, expected base/post-apply hashes, recovery-required status, and safe operator recommendations. |
| Signed exports | Locally signed audit export bundle, key ID, event digest, audit verification status, and offline verification result. |
| Future SIEM-shaped evidence | Stable event categories, correlation IDs, severity labels, resource summaries, and evidence hashes. |

## Reconstruction Flow

1. Identify the `run_id` from the review console, `/runs`, audit event metadata, or the exported
   evidence bundle.
2. Confirm the local principal, workspace ID, optional sandbox ID, policy hash, manifest lock hash,
   and run status recorded for that run.
3. List correlated tool calls and order them by timestamp and sequence where available.
4. For each tool call, inspect schema/resource normalization, policy decision, matched rules,
   obligations, executor status, and safe error metadata.
5. For approval-gated patch apply, match the approval ID, proposal ID, proposal hash, base file hash,
   request hash, expiry, approval consumption status, and patch diagnostics.
6. Verify whether any denied attempts occurred, including dangerous tools, out-of-scope resources,
   unknown or disabled principals, blocked network destinations, stale patch bases, or replayed
   approvals.
7. Verify the audit chain head and, when available, verify a locally signed audit export bundle.
8. Record unresolved gaps such as missing run records, recovery-required patch attempts, unsupported
   filesystem profile warnings, stale evidence, or actions outside Ithildin.

## What Can Be Proven

For Ithildin-mediated actions, reconstruction can support:

- which local principal label requested an action;
- which workspace/resource was normalized;
- whether policy allowed, denied, or required approval;
- whether a human approval was created, denied, expired, or consumed;
- whether an executor started, completed, failed closed, or recorded diagnostics;
- which audit head and signed export bind the evidence observed at export time.

## What Cannot Be Proven

This guide does not prove:

- model intent or reasoning;
- production human identity;
- actions outside Ithildin-mediated tools;
- OS-level sandbox containment;
- external notarization or custody-grade evidence;
- compliance with HIPAA, GLBA, SOX, GDPR, or other regulatory regimes;
- that best-effort redaction caught every secret.

## Review Gate

Run:

```text
make incident-reconstruction-check
```

The gate verifies this guide, review-doc/docs-site wiring, README linkage, roadmap linkage, and the
no-new-powers boundary.
