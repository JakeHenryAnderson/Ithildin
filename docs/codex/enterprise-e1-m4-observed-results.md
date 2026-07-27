# Enterprise E1 M4 Observed Results

Status: `E1-M4` engineering checkpoint complete. This is evidence for the exact repository state
below; it is not human UAT, accessibility certification, release acceptance, or production
promotion.

## Exact state

- Branch: `codex/enterprise-single-site-operations`
- Commit: `c73e1e73eb2f7c92f9cc0d470fb26f23dffcbaf5`
- Governed tools: `24`
- E1 cockpit schema: `ithildin.enterprise-e1-cockpit.v1`
- Command Center execution authority: `false`
- Human UAT complete: `false`

## Observed coverage

The existing Command Center implementation, now bound by the E1 cockpit contract, presented seven
operator surfaces:

1. missions;
2. Nodes;
3. software versions;
4. configuration posture;
5. Attention;
6. approvals; and
7. evidence.

Mission and Node views kept four truth sources distinct:

- Gateway lifecycle, admission, policy, approval, execution, and audit are authoritative within
  Ithildin;
- Node connectivity means only that a correctly signed heartbeat was accepted recently;
- runner state is runner-reported through an authenticated Node and does not prove process state;
- model-provider inference, output correctness, chain of thought, and health remain `Unknown`.

The rendered controls call existing authenticated Gateway endpoints. Mission admission remained
bound to the server-owned synthetic template and did not accept a free-form objective. Mission
cancellation remained a Gateway decision rather than an operating-system process-stop claim.
Configuration storage acknowledgment remained distinct from enforcement.

## Validation

`make enterprise-e1-cockpit-check` passed with:

- the closed seven-surface/four-truth-source machine contract;
- the locked 24-tool manifest;
- `1` focused E1 Python contract test;
- Ruff and strict mypy;
- UI TypeScript typecheck;
- `66` Command Center interaction tests;
- a Vite `7.3.6` production build with `1,751` modules transformed.

The focused UI suite exercised keyboard skip/focus transfer, destination navigation, truth-source
labels, accessible Attention remediation, missions, Node connectivity, version/configuration
cohorts, approvals, evidence, async error/status behavior, and governed action endpoint bindings.

During the isolated dependency install, `npm audit` initially reported four build/test/dev-graph
advisories. The existing semver ranges admitted patched releases, so only
`apps/ui/package-lock.json` was refreshed. A subsequent `npm audit --json` reported zero known
vulnerabilities, and the full cockpit gate passed again. The compiled static UI remains the shipped
artifact; the Vite development server is not part of the E1 runtime image.

Additional boundary checks passed:

```text
make enterprise-e1-contract-check
make tool-surface-invariant-gate
make no-new-powers-guardrail
git diff --check
```

## Evidence limits

- Automated interaction tests do not prove fresh-operator comprehension.
- Keyboard/focus assertions do not constitute WCAG conformance or screen-reader certification.
- The production build does not prove a particular browser, assistive-technology, zoom, or narrow-
  viewport experience.
- Command Center does not observe activity that bypasses the Gateway.
- No runner, model-provider, whole-host, SIEM, telemetry, notarization, compliance, production-
  identity, or production-readiness claim is made.

Fresh human accessibility and operator-flow acceptance remains in `E1-M6` and is deliberately not
marked complete.
