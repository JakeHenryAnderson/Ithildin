# SUB-080 Review Console Interaction Test Harness

- Finding ID: SUB-080
- Severity: low
- Area: review console/admin boundary
- Affected files/functions: apps/ui/package.json; apps/ui/src/App.tsx; docs/codex/review-console-source-review-checklist.md
- Claim being tested: The review console should have automated interaction coverage for token storage, loading/locked states, approval controls, trust warnings, exports, and diagnostics rendering.
- Observed behavior: The repo now includes a Vitest/React Testing Library interaction harness with mocked local API responses for review-console token storage and bearer auth, trust warnings, approval binding evidence, approve/deny actions, signed export controls, and policy-preview JSON error handling.
- Risk: UI regressions in button state, warning rendering, or sessionStorage handling are now covered by a focused local interaction harness, while deeper browser/manual smoke coverage remains optional local-preview assurance.
- Recommended fix: Fixed by adding the review-console interaction harness and wiring `make ui-test` into `make release-check`.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `npm run test --prefix apps/ui`, `npm run typecheck --prefix apps/ui`, `npm run build --prefix apps/ui`, and `make release-check` cover the harness and existing UI gates. External/source review closure remains local-preview scoped.
