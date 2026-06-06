# Dashboard Evidence Review Checklist

Status: review checklist. This document does not add runtime behavior, tool manifests, executors,
policy rules, API endpoints, MCP tools, UI controls, sandbox controls, process supervision, SIEM
adapters, production identity, runtime Postgres, hosted telemetry, shell, Docker, Kubernetes,
browser automation, plugin SDKs, arbitrary HTTP, or broad filesystem writes.

This checklist defines what an operator-facing evidence dashboard should make visible before
Ithildin adds richer Agent Run or sandbox/workspace UI. It is a review target, not a current feature
claim.

## Required Evidence Panels

Future dashboard work should preserve or add reviewable surfaces for:

- Agent Run summary: run ID, principal, workspace, optional sandbox ID, status, tool-call count,
  policy hash, manifest lock hash, and timestamps;
- timeline evidence: schema validation, resource normalization, policy decision, executor start,
  executor completed/failed, audit event hash, and safe error status;
- approval evidence: proposal ID/hash, base hash, request hash, manifest/policy evidence, expiry,
  approver/requester labels, and one-time consumption status;
- patch diagnostics: completed, failed, file replaced, recovery required, stale base, and safe
  operator recommendation;
- signed export evidence: key ID, bundle digest, event digest, verification status, and local
  signing/non-notarization warning;
- data classification warnings: trusted local labels and config source only;
- control mapping hints: mapping support labels without compliance claims;
- unsupported posture warnings: dev-token mode, unsupported filesystem profile, missing signing
  keys, stale audit, recovery diagnostics, and dangerous config states.

## Interaction Expectations

- UI actions must not hide binding evidence behind a destructive or irreversible action.
- Copyable values should be hashes, IDs, and safe metadata only.
- Errors must not expose prompts, file contents, diffs, response bodies, secrets, package script
  values, dependency names, or raw sensitive paths.
- Empty, unauthorized, loading, and failed states must be readable without raw JSON.
- Any future pause/abort/disable control must be introduced through a separate proposal and source
  review before implementation.

## Review Questions

Before a dashboard change is accepted, reviewers should ask:

1. Does the operator see what action happened, who requested it, which workspace/resource it used,
   and which policy evidence applied?
2. Can a denied or failed action be reconstructed without exposing sensitive content?
3. Are local-preview warnings visible when evidence is local, unsigned, unsupported, or
   recovery-required?
4. Does the UI avoid compliance, sandbox, production identity, SIEM custody, and public/security
   product claims?
5. Do UI tests cover the evidence display and the relevant action buttons?

## Review Gate

Run:

```text
make dashboard-evidence-checklist-check
```

The gate verifies this checklist, review-doc/docs-site wiring, README linkage, roadmap linkage, and
the no-new-powers boundary.
