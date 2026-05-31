# Release Guardrail Expansion

Task 108 expands `make release-guardrails` from public-warning/deployment checks into a v0.3-prep
handoff guard. The script still does not prove source-code correctness; it catches drift in the
review and release envelope before a packet is handed to an external reviewer.

## Guardrails

`scripts/release_guardrails.py` now checks:

- public-preview warning labels and forbidden overclaiming phrases;
- threat-model links in required public-preview docs;
- Compose loopback binding, no Docker socket mount, and no privileged services;
- required review/docs-site documents exist;
- `release-check` still includes manifest lock, release guardrails, reviewer finding intake,
  filesystem contract evidence, policy tests, policy parity, tests, lint, typecheck, and docs-site;
- `review-candidate` still runs the expected evidence generation sequence in order;
- Make targets for release evidence validation, review packet diffs, and reviewer finding intake
  remain wired;
- committed tool manifests do not introduce deferred shell, Docker, Kubernetes, or browser tool
  powers;
- Tasks 101-112 are marked done before the final v0.3-prep handoff claim.

Task 126 extends the same guardrail into the v0.4 horizontal gate:

- `release-check` must include `release-evidence-gate`;
- `review-packet-diff-gate` must remain wired as a Make target;
- `packet-redaction-scan` must remain wired and run during `make review-candidate`;
- the v0.4 milestone manifest must mark Tasks 113-127 done and Tasks 128-151 planned;
- the v0.4 after-wave command list must include both `release-evidence-gate` and
  `review-packet-diff-gate`;
- every completed v0.4 checkpoint must preserve the deferred-boundary metadata.

These checks are intentionally conservative. If a future task intentionally changes the release
workflow or adds a new governed tool-power class after external review, the guardrail should be
updated in the same checkpoint as the boundary decision.
