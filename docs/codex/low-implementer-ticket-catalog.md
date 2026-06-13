# Low-Implementer Ticket Catalog

Status: delegation calibration catalog. This document defines small-verifiable tickets that may be
handed to Low Codex implementers such as `gpt-5.4-mini` low effort. It is not permission to edit
runtime behavior, decide safety boundaries, or change Ithildin product claims.

This catalog is not permission to edit runtime behavior.

The main Codex manager owns scope, review, gates, staging, and commits. The default worker is
`gpt-5.4-mini` with low reasoning. Use one Low Codex implementer at a time by default. Low
implementers may return suggestions only unless the manager explicitly asks for a bounded patch
after several clean read-only trials.

## Approved Ticket Types

| Ticket | Purpose | Allowed output |
| --- | --- | --- |
| `docs-link-scan` | Find stale command-list references, missing documentation links, or obvious navigation drift. | Short report with candidate text changes. |
| `stale-wording-scan` | Check current tool count, next-candidate wording, and read-only inventory text for drift. | Short report with exact stale phrases and suggested replacements. |
| `make-target-wiring` | Compare documented Make targets with existing release-readiness assertions. | Short report with missing command references or assertion suggestions. |
| `packet-inventory` | Check generated packet references and artifact inventory wording. | Short report with missing packet references or stale artifact names. |

Repetitive release-readiness assertion suggestions are allowed when they follow an existing test
pattern and do not alter runtime behavior.

## Forbidden Work

Low implementers must not edit manifests, executors, policy semantics, approval logic, audit logic,
MCP/API behavior, storage/auth boundaries, UI runtime behavior, or public trust claims. They must
not add tool powers, broaden filesystem/network access, change evidence semantics, or decide whether
a capability is safe.

## Manager Scorecard

Every generated delegation packet includes a manager scorecard. Use it to record:

- `useful_suggestions_count`;
- `rejected_suggestions_count`;
- `boundary_drift_observed`;
- `manager_cleanup_required`;
- `delegate_again`.

Delegation is considered useful only when the manager accepts mechanical suggestions with less
review/cleanup effort than doing the scan directly.

## Command

```sh
make low-implementer-delegation-packet
uv run python scripts/low_implementer_delegation_packet.py --ticket stale-wording-scan
make low-implementer-ticket-catalog-check
```

The packet generator does not call a model. Live subagent trials are separate manager-controlled
experiments and must remain read-only until the manager records multiple useful, low-cleanup,
no-boundary-drift trials.
