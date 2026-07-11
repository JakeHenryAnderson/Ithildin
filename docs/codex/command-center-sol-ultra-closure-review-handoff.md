# Command Center Sol Ultra Closure Review Handoff

Status: pre-dispatch draft; provenance schema resolved and dirty candidate validated; exact clean
commit pending.

This packet defines the independent closure review required before `CC-PILOT-107` operator UAT.
It is not dispatchable until the candidate is committed with a clean tree and the authoritative
gates pass for that exact commit. The review-run binding contract is resolved without rewriting
historical provenance, and the integrated dirty candidate has passed `make release-check`.

## Dispatch Preconditions

Record all of the following before sending this packet:

- candidate commit: `PENDING`;
- clean working tree: `PENDING`;
- governed tool/manifests count: `24 / 24`;
- `make agent-workflow-check`: `PENDING ON EXACT COMMIT`;
- `make release-check`: `PENDING ON EXACT COMMIT`;
- `make review-candidate`: `PENDING ON EXACT COMMIT`; and
- addition-aware whitespace check for all candidate documents: `PENDING ON EXACT COMMIT`.

The dispatch record must cite the immutable `release-check.txt` inside the exact candidate packet.
Do not use `var/review-packets/v3/review-candidate-release-check.txt` as the reviewer locator: that
path is a mutable build input and advances when a later candidate is generated.

Do not replace `PENDING` with an intended result. Use only observed output from the exact candidate.

## Reviewer Prompt

Act as the independent Sol Ultra closure reviewer for the Ithildin Command Center pre-UAT
remediation candidate.

Repository: `/Users/jake/Documents/Codex/Ithildin`

Read the complete applicable `AGENTS.md` hierarchy first. Perform a findings-first, read-only
review. Do not edit, stage, commit, refresh historical evidence, mutate approvals, export evidence,
or start operator UAT.

Review the candidate against:

- [the original findings register](command-center-sol-ultra-pre-uat-review.md);
- [the canonical UAT handoff](command-center-cc-pilot-107-uat-handoff.md);
- [the golden pilot scenario](command-center-golden-pilot-scenario.md);
- [the initial operator evidence](command-center-initial-operator-uat-evidence.md); and
- the exact candidate diff and validation artifacts.

For each `ULTRA-H-01` through `ULTRA-H-04` and `ULTRA-M-01` through `ULTRA-M-06`, independently
determine one disposition: `closed`, `partially_closed`, `open`, or `regressed`. Cite exact files,
lines, tests, and observed behavior. Do not infer closure from a passing broad gate when the gate
does not exercise the finding.

At minimum, verify:

1. conflicting approve/deny requests have one atomic winner, preserve the winning decision
   metadata, produce no contradictory terminal audit events, and reject expiry during transition;
2. proposal, run, evidence, approval-history, decision-event, policy-hash, and manifest-hash state
   remains bound to the selected record under delayed and out-of-order responses;
3. replacement-token rejection, logout, partial dashboard failure, operation-specific failure, and
   recovery do not retain or mislabel stale authority data;
4. the UAT handoff exactly preserves the fresh-participant constraint, single uncoached task card,
   six stages, 12-minute threshold, 7-of-8 comprehension threshold, confidence threshold,
   technical-evidence retrieval, and direct disposition of `UAT-OBS-063` through `070`;
5. export notices remain bound to audit/signed-audit/run scope and the selected run;
6. recorded approval lifecycle and binding validity remain separately visible;
7. draft Investigation filters are not described as applied, chip removal reloads the applied
   server query, and advanced controls remain outside the Routine and Policy Administration lenses;
8. Attention communicates time or expiry as well as mission, state, consequence, and action;
9. selection is programmatic, narrow artifact values retain labels, focus targets have accessible
   names, matching-approval navigation targets the exact approval, and focus tests are stable; and
10. the candidate commit, clean tree, documentation inventory, validation commands, generated
    evidence, and historical/current review bindings are reproducible without falsifying provenance.

## Required Output

Return:

1. milestone disposition: `ready_for_cc_pilot_107_uat` or `not_ready_for_cc_pilot_107_uat`;
2. severity-ordered findings with exact file and line references;
3. the ten finding dispositions with supporting evidence;
4. tests/checks run and not run;
5. open questions and residual risks; and
6. an explicit statement that the review is internal independent AI review only and does not
   constitute operator UAT, external/source review, promotion, trusted-host/runtime authorization,
   release approval, or accessibility conformance.

Any open or partially closed high finding requires `not_ready_for_cc_pilot_107_uat`. A clean review
may reopen the human UAT gate but cannot pass UAT or authorize any other initiative.
