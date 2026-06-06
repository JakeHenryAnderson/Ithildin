# SIEM-Shaped Evidence Design

Status: evidence-design preparation. This document does not add runtime behavior, API endpoints,
MCP tools, tool manifests, policy rules, executors, SIEM adapters, hosted telemetry, or new governed
tool powers.

This design defines how Ithildin can shape future JSONL evidence exports so they are easier to map
into operator logging and incident-review systems without claiming SIEM-grade custody.

## Event Categories

Future SIEM-shaped evidence should use stable categories for:

- run lifecycle;
- tool lifecycle;
- policy decision;
- approval lifecycle;
- executor result;
- audit verification;
- signed export;
- redaction summary;
- diagnostics;
- sandbox/workspace posture.

## Common Fields

Each event should be secret-free and include:

- event category;
- event timestamp;
- run ID when available;
- request ID when available;
- principal ID;
- workspace ID;
- optional sandbox ID;
- tool name when relevant;
- decision/status;
- severity label;
- resource summary;
- evidence hash or audit event hash;
- policy hash when relevant;
- manifest hash or manifest lock hash when relevant;
- redaction summary when relevant.

## Export Non-Goals

SIEM-shaped evidence must not export prompts, secrets, file contents, diffs, response bodies,
package script values, dependency names, raw sensitive paths, raw tool arguments, model output,
private key material, bearer tokens, cookies, environment variables, or local database contents
unless a later reviewed contract explicitly allows a narrower field.

This design does not add hosted telemetry, SIEM adapters, custody-grade retention, external
notarization, immutable storage, production identity, or remote MCP behavior.

## Relationship To Signed Evidence

Future SIEM-shaped JSONL should remain compatible with local signed export workflows. Signing can
bind exported content and metadata to a local key, but it does not provide external notarization,
hosted custody, or compliance proof by itself.

## Verification

Run:

```bash
make siem-evidence-design-check
```

The gate validates that this design is present, linked from the roadmap, included in review/docs
materials, and still aligned with the no-new-powers boundary.
