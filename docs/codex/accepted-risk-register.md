# Accepted Risk Register

Task 168 added the original accepted-risk register. v0.8 Wave 2 turns it into an explicit
product-risk disposition artifact. It remains scoped to the v0.1 local-preview runtime boundary.

Machine-readable records live in
[accepted-risk-register.json](accepted-risk-register.json). The release gate validates them with:

```bash
make accepted-risk-register-check
```

## Boundary Rules

- Accepted risks apply only to the v0.1 local-preview runtime boundary.
- Accepted risks are not production authorization and are not production security certification.
- Local signed evidence remains local operator evidence, not external notarization.
- Critical or high accepted risks are not allowed in this register.
- `closed_local_preview` means source-review or packet-and-source review closed the risk only for
  the local-preview behavior named in the record.
- `accepted_deferred` means the risk is explicitly carried forward with rationale, owner, revisit
  criteria, and blocked claims; it does not approve capability expansion.
- Any new powerful tool class requires a separate capability decision and external/source review.

This register does not approve capability expansion, does not close external source review globally,
does not support production/security-product claims, and does not change the deferred-power list.

## v0.8 Disposition Summary

| ID | Area | Disposition | Product effect |
| --- | --- | --- | --- |
| AR-001 | Local host trusted computing base | accepted_deferred | Blocks sandbox/EDR/production-security claims |
| AR-002 | Local principal labels | accepted_deferred | Blocks production identity and enterprise RBAC claims |
| AR-003 | Local tamper-evident audit | accepted_deferred | Blocks immutable/custody/notarization/compliance claims |
| AR-004 | Patch apply write surface | closed_local_preview | Closed only for stored approval-gated patch apply |
| AR-005 | Filesystem platform/race claims | closed_local_preview | Closed only for macOS/Linux local-preview claims |
| AR-006 | HTTP fetch SSRF-sensitive boundary | closed_local_preview | Closed only for exact-allowlist GET-only behavior |
| AR-007 | Policy engine parity and OPA optionality | closed_local_preview | Closed only for YAML-canonical local-preview policy/registry behavior |
| AR-008 | Local operator signing keys | closed_local_preview | Closed only for local signed-evidence verification behavior |
| AR-009 | SQLite-only runtime storage | accepted_deferred | Blocks runtime Postgres/multi-user storage claims |
| AR-010 | Best-effort redaction | accepted_deferred | Blocks guaranteed-redaction/secrets/telemetry claims |

## Review Use

Reviewers should use this register as a map of known local-preview limitations. Closed risks are
reference evidence for the current runtime boundary, not approval for broader product claims.
Accepted-deferred risks must be revisited before the blocked claims or capability classes named in
their records.

The register does not close external source review globally, does not approve capability expansion,
and does not support production/security-product claims.
