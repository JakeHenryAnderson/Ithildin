# SUB-021 Approval Route Decision Mismatch

- Finding ID: SUB-021
- Severity: low
- Area: admin approval API
- Affected files/functions: apps/api/src/ithildin_api/app.py; approve_approval; deny_approval
- Claim being tested: approval mutation routes should reject contradictory route/body decisions.
- Observed behavior: The approve and deny routes accepted a body `decision` field but ignored mismatches with the route action.
- Risk: Client mistakes or review-console bugs could send contradictory approval payloads that are harder to diagnose.
- Recommended fix: Validate route/body decision agreement and return a safe client error on mismatch.
- Blocking status: later
- Disposition: fixed
- Verification notes: The approve route now requires `decision: approve` and the deny route requires `decision: deny`; mismatches return HTTP 400. API tests cover both mismatches. External/source review remains pending.
