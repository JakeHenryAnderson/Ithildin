# External Review Response Intake Template v2

Task 173 provides a structured template for turning GPT 5.5 Pro / Very High or human expert review
responses into concrete follow-up records. It does not mutate findings, close external review, or approve
capability expansion by itself.

Use this template after receiving a review response. Extract each actionable issue into
[reviewer-finding-template.md](reviewer-finding-template.md) with an `EXT-###` ID, then update
[source-review-closure-matrix.md](source-review-closure-matrix.md) only after triage.

## Review Summary

### Overall judgment

- Reviewer:
- Model / reviewer type:
- Date:
- Reviewed packet or commit:
- Overall judgment:

### Blockers

- Blocker ID:
- Summary:
- Affected area:
- Required before:

### Should-fix before broader distribution

- Item:
- Severity estimate:
- Recommended follow-up task:

### Documentation and positioning risks

- Risk:
- Overclaim or ambiguity:
- Suggested wording:

### Technical hardening priorities

- Area:
- Files/functions to inspect:
- Recommended test or fix:

### Packet gaps

- Missing artifact:
- Expected evidence:
- Proposed packet update:

### v0.6 or next-roadmap recommendations

- Recommendation:
- Dependency:
- Deferred until:

### Do-not-add-yet list

- Capability or product surface:
- Reason to defer:
- Required gate before revisiting:

## Finding Extraction Table

| Finding ID | Severity | Area | Affected files/functions | Blocking status | Disposition | Recommended fix |
| --- | --- | --- | --- | --- | --- | --- |
| EXT-### | critical/high/medium/low/informational | patch/http/filesystem/etc. | paths/functions | blocking/should-fix/advisory | open | follow-up task |

## Intake Rules

- Every blocker or should-fix item becomes a structured finding unless it is purely editorial.
- Critical/high findings remain open until a follow-up commit and verification notes exist.
- Accepted or deferred risks must link to the accepted-risk register and closure matrix.
- AI/subagent feedback is useful pressure testing, but only GPT 5.5 Pro / Very High or human expert review
  can satisfy external review rows.
