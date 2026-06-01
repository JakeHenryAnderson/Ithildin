# SUB-059 Signed Evidence Dispatch Pointers

- Finding ID: SUB-059
- Severity: medium
- Area: external review dispatch packets
- Affected files/functions: scripts/external_review_dispatch_packets.py; docs/codex/review-packet-source-pointers.md
- Claim being tested: Signed-evidence review packets should point reviewers at implemented source files and all relevant finding records.
- Observed behavior: Internal proxy review found a stale/nonexistent `audit_routes.py` pointer and missing signed-evidence finding records in the dispatch packet.
- Risk: External reviewers could spend time on stale pointers or miss important context from previous signed-evidence remediations.
- Recommended fix: Replace stale route pointers with `apps/api/src/ithildin_api/app.py` and include the complete signed-evidence finding trail.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: Dispatch packets now point to `app.py` for audit routes and include signed-evidence finding records. Release-readiness tests cover dispatch packet wiring. External/source review remains pending.
