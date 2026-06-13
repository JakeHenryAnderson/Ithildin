# Ithildin Agent Instructions

These instructions apply to AI coding agents working in this repository. They are coordination guidance, not a security boundary. Ithildin's tests, gates, review workflow, and human review remain
the enforcement layer.

## Product Boundary

Ithildin is a local-preview governed MCP/tool gateway. Preserve the current boundary unless the
user explicitly starts a new approved capability or architecture sprint.

Do not add shell execution, Docker socket access, Kubernetes tools, browser automation, arbitrary HTTP methods/headers/bodies, broad filesystem writes/deletes/moves/chmod/archive extraction,
production identity, runtime Postgres, hosted telemetry, remote MCP hosting, plugin SDK behavior,
secrets-manager tools, sandbox orchestration, SIEM adapters, compliance automation, or public
security-product claims.

Current governed tool count is 19. Any tool-count change requires an explicit capability proposal,
implementation plan, implementation gate, manifest lock update, policy/parity coverage, source-review
handoff, and release/readiness updates.

## Planner-Implementer Model

- The main Codex agent owns scope, safety judgment, implementation review, gates, staging, and
  commits.
- Low Codex implementers are the preferred mechanical delegation path. Use `gpt-5.4-mini` with low
  reasoning as the default cheap worker for narrow report-first tasks: docs links, stale wording
  scans, repetitive test wiring suggestions, packet inventory checks, and boilerplate following an
  existing pattern.
- Use one Low Codex implementer at a time by default. Direct file edits by Low Codex implementers
  should remain disabled until several read-only trials have produced useful suggestions with low
  cleanup cost and no boundary drift.
- Gemma/local-model output is advisory only and should be used only for offline suggestions when a
  task is large but shallow; it is not the default implementation path for Ithildin.
- Low Codex and Gemma/local-model implementers must not decide safety boundaries, design executors,
  change policy semantics, edit manifests, add MCP/API behavior, alter approval/audit logic, or make
  product-risk claims.
- High agents may handle bounded implementation or review when runtime behavior, tests, policy,
  registry, audit, executor, release-gate, or UI trust surfaces are touched.
- XHigh agents are reserved for ambiguous security/product-boundary decisions, milestone risk review,
  and break-glass consultation.

Discard or rewrite any implementer output that weakens validation, broadens capabilities, adds
unreviewed runtime behavior, leaks sensitive metadata, or conflicts with these instructions.

## Required Local Checks

Use focused gates for the files touched, then run broader gates before committing meaningful changes.
For release or capability work, prefer:

```sh
make agent-workflow-check
make release-check
make review-candidate
```

For small docs-only changes, at minimum run:

```sh
make agent-workflow-check
uv run pytest tests/test_release_readiness.py tests/test_docs_site.py -q
make lint
```

## Stop Conditions

Stop and report status if a critical/high trust-boundary issue appears, the same gate fails three
times, implementation requires changing the product boundary, tests reveal a real security
regression, or a low Codex/Gemma implementer proposes changes outside its allowed role.
