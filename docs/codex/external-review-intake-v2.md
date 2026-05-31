# External Review Intake v2

Task 150 updates the external review intake workflow for the v0.4 review-candidate phase. It does
not close any external review row by itself.

## Intake Rule

Every GPT 5.5 Pro / Very High or human expert review response must be converted into structured
finding records before it changes the closure matrix.

Use:

```sh
make reviewer-findings-check
make review-findings-summary
make release-check
```

## Required Mapping

For each reviewer response:

1. Save the raw response or a sanitized excerpt with the review packet evidence.
2. Create one finding file per actionable issue under `docs/codex/findings/`.
3. Use `EXT-###` IDs for external findings.
4. Include affected files/functions when the reviewer inspected source.
5. Mark critical/high findings as blocking unless a user explicitly accepts the risk as deferred.
6. Update [source-review-closure-matrix.md](source-review-closure-matrix.md) only after the finding
   record validates.
7. Record verification command, fixed commit, or accepted/deferred risk link before closing a row.

## Closure Guardrails

- Internal AI/subagent review cannot close external rows.
- Packet/evidence review cannot be described as source review unless source files/functions were
  inspected.
- Critical/high open findings stop autonomous implementation.
- Any finding that requires shell, Docker socket, Kubernetes, browser automation, arbitrary HTTP,
  broad filesystem writes, production identity, runtime Postgres, hosted telemetry, remote MCP, or a
  plugin SDK becomes a boundary decision.
- External closure is local-preview closure only; it does not create production/security-product
  positioning.

## Review Artifacts to Attach

- consolidated packet index and attachment hashes;
- release-check transcript and release evidence JSON;
- v0.4 review packet summary from `make v04-review-packet`;
- review-doc hashes and artifact hashes;
- negative transcripts and demo scenario pack;
- signed-evidence demo summary;
- source-review closure matrix and this intake guide.
