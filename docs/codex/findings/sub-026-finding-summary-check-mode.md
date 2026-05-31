# SUB-026 Finding Summary Check Mode

- Finding ID: SUB-026
- Severity: low
- Area: release automation
- Affected files/functions: Makefile; scripts/review_findings_collect.py; check_summary_outputs
- Claim being tested: release gates should fail on stale generated finding summaries rather than mutating tracked outputs during a check.
- Observed behavior: The release-check path could regenerate finding-summary outputs, making stale artifacts less obvious.
- Risk: A release gate might hide missing committed updates by rewriting generated documentation during validation.
- Recommended fix: Make the default gate compare generated output against committed artifacts, and provide a separate explicit write target for regeneration.
- Blocking status: later
- Disposition: fixed
- Verification notes: `make review-findings-summary` now runs in compare-only check mode, and `make review-findings-summary-write` performs explicit regeneration. The collector reports stale markdown or JSON outputs with a deterministic remediation message. External/source review remains pending.
