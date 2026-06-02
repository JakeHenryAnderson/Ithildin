# SUB-080 Review Console Interaction Test Harness

- Finding ID: SUB-080
- Severity: low
- Area: review console/admin boundary
- Affected files/functions: apps/ui/package.json; apps/ui/src/App.tsx; docs/codex/review-console-source-review-checklist.md
- Claim being tested: The review console should have automated interaction coverage for token storage, loading/locked states, approval controls, trust warnings, exports, and diagnostics rendering.
- Observed behavior: The repo currently validates the React console with TypeScript and production build checks, plus backend API tests and source-review checklists, but it does not include a frontend interaction-test harness.
- Risk: UI regressions in button state, warning rendering, or sessionStorage handling may be caught later than backend/API regressions.
- Recommended fix: Add a small Vitest/React Testing Library or Playwright harness after the current review-console source-review lane, using mocked API responses for local admin flows.
- Blocking status: later
- Disposition: deferred
- Verification notes: Deferred as a low-priority UI assurance improvement because adding a new frontend test harness is larger than this remediation sprint and does not affect runtime tool execution. `npm run typecheck --prefix apps/ui` and `npm run build --prefix apps/ui` remain required. External/source review remains pending.
