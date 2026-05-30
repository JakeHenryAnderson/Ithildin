# Reviewer Finding Template

Use this template for each external/source review finding. It is designed for the v0.2 review
candidate for the v0.1 local-preview runtime boundary.

## Finding

- Finding ID:
- Severity: critical / high / medium / low / informational
- Area:
- Affected files/functions:
- Claim being tested:
- Observed behavior:
- Risk:
- Recommended fix:
- Blocking status: blocking / should-fix / later / accepted risk
- Disposition: open / fixed / deferred / rejected
- Verification notes:

## Review Summary

- Overall judgment: ready / ready with fixes / not ready
- Blockers:
- Should-fix before broader distribution:
- Documentation and positioning risks:
- Technical hardening priorities:
- Release packet gaps:
- v0.3 priority roadmap:
- Do-not-add-yet list:
- Brutal short version:

## Disposition Guidance

Use `blocking` only for issues that should prevent local-preview handoff or any broader capability
work. Use `should-fix` for issues that should be resolved before broader distribution. Use `later`
for roadmap items that do not invalidate the current local-preview boundary. Use `accepted risk`
only when the risk is documented in the threat model or release notes and no code change is planned.
