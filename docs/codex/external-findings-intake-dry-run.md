# External Findings Intake Dry Run

Task 166 adds `make external-findings-intake-dry-run` to exercise the external finding intake
workflow without adding a real external finding or changing source-review closure status.

## Command

```sh
make external-findings-intake-dry-run
uv run python scripts/external_findings_intake_dry_run.py --json
```

The dry run creates temporary `EXT-###` finding fixtures, validates a well-formed low-severity
external finding, verifies that an open high-severity external finding fails closed, and then deletes
the temporary fixture directory.

## Boundary

The dry run does not mutate `docs/codex/findings/`, does not update the closure matrix, does not
mark external review complete, and does not approve capability expansion. It exists so packet
generation and release gates can prove that the external intake rails still work before a real GPT
5.5 Pro / Very High or human review response arrives.
