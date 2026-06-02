# Accepted Risk Register

Task 168 adds an explicit accepted-risk register for the v0.5 source-review closure track. It is a
local-preview risk inventory, not a product approval artifact. It does not approve capability expansion,
does not close external source review, and does not change the deferred-power list.

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
- Accepted risks remain pending external/source review before closure unless a structured
  local-preview source-review closure is recorded for that risk.
- Any new powerful tool class requires a separate capability decision and external/source review.

## Risks

| ID | Area | Accepted Scope | Current Status |
| --- | --- | --- | --- |
| AR-001 | Local host trusted computing base | v0.1 local-preview only | Accepted for preview; external review required before closure |
| AR-002 | Local principal labels | v0.1 local-preview only | Accepted for preview; external review required before closure |
| AR-003 | Local tamper-evident audit | v0.1 local-preview only | Accepted for preview; external review required before closure |
| AR-004 | Patch apply write surface | v0.1 local-preview only | Accepted for preview; external review required before closure |
| AR-005 | Filesystem platform/race claims | v0.1 local-preview only | Source-reviewed and closed for the v0.1 local-preview filesystem/platform lane via EXT-FS-001 |
| AR-006 | HTTP fetch SSRF-sensitive boundary | v0.1 local-preview only | Accepted for preview; external review required before closure |
| AR-007 | Policy engine parity and OPA optionality | v0.1 local-preview only | Accepted for preview; external review required before closure |
| AR-008 | Local operator signing keys | v0.1 local-preview only | Accepted for preview; external review required before closure |
| AR-009 | SQLite-only runtime storage | v0.1 local-preview only | Accepted for preview; external review required before closure |
| AR-010 | Best-effort redaction | v0.1 local-preview only | Accepted for preview; external review required before closure |

## Review Use

Reviewers should use this register as a map of known local-preview limitations. A risk can move out of
accepted-preview pending status only after implementation evidence, source review, and explicit closure
notes are recorded in [source-review-closure-matrix.md](source-review-closure-matrix.md). This register
does not close external source review globally, does not approve capability expansion, and does not
support production/security-product claims.
