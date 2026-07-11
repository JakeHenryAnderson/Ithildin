# Command Center Independent Sol Ultra Pre-UAT Findings Register

Status: internal independent AI review received; remediation implemented; exact-candidate closure
review pending; not UAT-ready.

Review basis: dirty Command Center candidate based on
`6a357bd4bb7e7a7dc10abeb4bfa834addf64175c`. The reviewer made no edits and did not perform operator
UAT, external/source review, promotion approval, trusted-host/runtime authorization, or release
approval.

The reviewer confirmed no governed-tool or capability expansion: 24 tools and 24 manifests, with
the no-new-powers guardrail passing.

## Findings And Required Closure Evidence

| ID | Severity | Finding | Required closure evidence | Status |
| --- | --- | --- | --- | --- |
| `ULTRA-H-01` | high | Conflicting approval decisions can race to authoritative state. | Atomic pending-to-terminal transition, per-approval UI serialization, and adversarial transition tests. | remediated; closure review pending |
| `ULTRA-H-02` | high | Selected proposal/run records and technical evidence are not identity-bound. | Stale-response suppression, selection clearing/refresh, exact request correlation, and multi-record delayed-response tests. | remediated; closure review pending |
| `ULTRA-H-03` | high | Authentication and partial-load failures retain stale authority state or imply authoritative emptiness. | Fail-closed presentation state plus rejected-token, endpoint-failure, and recovery tests. | remediated; closure review pending |
| `ULTRA-H-04` | high | The `CC-PILOT-107` handoff weakens the canonical UAT protocol. | One canonical participant rule, task card, timing/comprehension thresholds, six stages, and direct disposition of `UAT-OBS-063` through `070`. | remediated; verification pending |
| `ULTRA-M-01` | medium | Export results are attributed to the wrong evidence scope. | Scope- and run-bound notices with cross-scope tests. | remediated; closure review pending |
| `ULTRA-M-02` | medium | Binding validity replaces recorded approval lifecycle state. | Separate lifecycle and binding presentation. | remediated; verification pending |
| `ULTRA-M-03` | medium | Investigation controls do not match the lens or applied query. | Specialist-only controls, draft/applied separation, and reload on chip removal. | remediated; verification pending |
| `ULTRA-M-04` | medium | Attention lacks required age or expiry. | Visible recorded time or expiry on every Attention source. | remediated; verification pending |
| `ULTRA-M-05` | medium | Selection, focus targets, and narrow artifact rows are not fully accessible. | Programmatic selection, labeled fields/regions, exact approval focus, stable navigation tests, and representative live checks. | remediated; closure review pending |
| `ULTRA-M-06` | medium | Dirty candidate and validation claims are not reproducibly bound. | Whitespace-clean integrated commit, executable checks, exact candidate identifier, and authoritative gates. | schema remediated; exact commit and closure review pending |

## Remediation Verification

Focused evidence collected before the authoritative candidate gates:

- approval workflow tests include a coordinated two-thread approve/deny race with exactly one
  terminal winner and one terminal audit event, expiry-during-transition rejection, and preserved
  decision metadata;
- the UI suite contains 17 tests covering rejected replacement tokens, fail-closed partial refresh
  and recovery, delayed multi-record proposal/run/evidence responses, in-flight opposite approval
  suppression, applied-query filter removal, lifecycle/binding separation, scoped export notices,
  and stable focus; three consecutive full UI runs passed;
- live local-preview QA at a 390 by 844 viewport found no horizontal overflow, retained 45 labeled
  narrow artifact cells, one programmatically selected proposal and run, hidden routine server
  filters, and visible Investigation filters only after selecting that lens;
- live Attention navigation focused the exact source panel and selected the proposal whose request
  matched the Attention record; and
- browser warning/error logs were empty during the live pass.

The integrated dirty candidate subsequently passed `make release-check`, including 1,111 Python
tests, 17 UI tests, lint, mypy, UI typecheck/build, docs build, and the repository governance
matrix. This evidence does not claim screen-reader interoperability, formal accessibility
conformance, human comprehension, operator acceptance, or closure of any finding. The exact clean
commit and independent closure disposition remain required.

## Review-Run Provenance Resolution

The review-run evidence contract now separates immutable `historical` bindings from exact
`current_candidate` bindings. Historical records retain the commit and dirty state actually
reviewed and require that commit to exist. Current-candidate records must match the full current
`HEAD`, dirty flag, and deterministic tree fingerprint. The fingerprint distinguishes staged and
unstaged changes and includes non-ignored untracked file content, type, mode, and symlink targets.

Refresh is staleness-only and never rewrites an executed review record. Manifest symlinks,
out-of-root untracked paths, unsafe file replacement, nonexistent historical commits, and stale or
malformed current-candidate bindings fail closed. A separate read-only internal review found no
remaining provenance-schema findings after the corrections. This internal review and the passing
dirty-tree release gate do not close `ULTRA-M-06`; closure still requires an exact clean candidate
commit, exact-commit gates, and the independent Sol Ultra closure review.

## Closure Rule

No finding is closed merely because code or documentation changed. Closure requires the listed
evidence against one reproducible candidate, followed by a fresh independent Sol Ultra closure
review. Only that closure disposition may reopen the human `CC-PILOT-107` UAT gate.
