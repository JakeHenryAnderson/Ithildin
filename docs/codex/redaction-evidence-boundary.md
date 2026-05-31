# Redaction Evidence Boundary

Task 145 clarifies Ithildin's redaction evidence boundary for the v0.1 local-preview runtime and
v0.4 review-closure wave.

Redaction is best-effort leak reduction. It is not a security boundary, not a secret-discovery
engine, not proof that outputs are safe to publish, and not a substitute for scoped executors,
schema validation, policy, approvals, or review-packet scanning.

## Runtime Redaction

Governed tool results pass through the API redaction service before being returned to agents. The
baseline service redacts:

- common sensitive keys such as authorization, cookie, token, API key, secret, password, and private
  key fields;
- common bearer-token, GitHub token, OpenAI-style token, assignment, JSON assignment, and private-key
  string patterns;
- locally configured extra keys and regex patterns when an operator sets them.

Audit metadata may include `redaction_applied`, `redaction_count`, and `redaction_paths`. These are
safe evidence fields that show where redaction was applied. They intentionally do not include the
original value or the redacted replacement source.

## Review Packet Redaction Scan

`make packet-redaction-scan` scans generated review-packet artifacts for obvious secret material and
runtime files that should never be uploaded. It is a handoff hygiene gate for generated artifacts,
not a complete repository or workstation secrets scan.

## What Redaction Does Not Prove

Redaction does not prove:

- that arbitrary secrets cannot appear in a tool result;
- that all unknown token formats or customer-specific secrets are detected;
- that screenshots, copied terminal output, local databases, or manually assembled packets are safe;
- that a reviewer can treat redacted output as public;
- that redaction can compensate for a broadened tool boundary.

The safe operating rule is still to keep tools narrow, deny by default, avoid broad network or
filesystem access, and scan generated handoff packets before review.

## Review Checklist

Before external handoff:

1. Run `make release-check`.
2. Run `make review-candidate`.
3. Confirm `packet-redaction-scan.txt` reports zero findings in the generated packet.
4. Confirm release evidence reports the runtime redaction status without exposing configured
   patterns or secret values.
5. Treat any redaction finding as a release/handoff blocker until the packet is regenerated cleanly.
