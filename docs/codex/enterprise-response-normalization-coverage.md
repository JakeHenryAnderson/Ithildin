# Enterprise Response Normalization Coverage

Status: coverage gate for enterprise response normalization lanes.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Run:

```sh
make enterprise-response-normalization-coverage
```

## Purpose

This gate checks that every lane listed by the Enterprise Response Status Board is known to the
shared external-review response normalizer and has a stable finding namespace.

It currently covers:

- `sandbox-vm-static-preflight`: `EXT-SVP-###`
- `mission-control-display`: `EXT-MC-DISPLAY-###`
- `trusted-host-promotion`: `EXT-TRUSTED-HOST-###`
- `production-identity-storage`: `EXT-PROD-IAM-STORAGE-###`
- `siem-export-adapter`: `EXT-SIEM-ADAPTER-###`
- `compliance-mapping`: `EXT-COMPLIANCE-MAPPING-###`
- `sandbox-vm-live-poc`: `EXT-LIVE-POC-###`
- `public-security-product-positioning`: `EXT-PUBLIC-POSITIONING-###`

## Boundary

This check does not normalize responses, does not write response files, does not mutate findings,
does not record external review, does not close enterprise lanes, does not approve runtime behavior,
does not approve new power classes, and does not approve public/security-product positioning.

It is a process-readiness invariant: if an enterprise lane appears on the response status board, the
normalizer must know how to validate that lane's finding namespace before operators paste reviewer
text into ignored local response files.

Use `make enterprise-response-status-board` to see whether any normalized responses are present and
which lane-specific dry-run or closure command should be used next.

Use `make enterprise-response-inbox` to create ignored raw-response placeholders and exact
normalization commands for all enterprise lanes after this coverage gate passes.

Use `make enterprise-response-intake-drill` to exercise all supported response-intake paths with
temporary fixtures while preserving ignored response state and without recording external review.
