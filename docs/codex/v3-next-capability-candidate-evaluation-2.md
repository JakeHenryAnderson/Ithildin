# v3 Next Capability Candidate Evaluation 2

Status: historical planning-only candidate evaluation. This document did not add a tool manifest,
did not add an executor, did not add policy rules, did not add MCP exposure, did not add API
behavior, did not add UI behavior, and did not add runtime behavior.

It remains a historical review artifact and does not add a tool manifest, does not add an
executor, does not add policy rules, does not add MCP exposure, does not add API behavior, does not
add UI behavior, and does not add runtime behavior.

This sprint evaluates the next safest bounded read-only metadata candidate after the current
project-intelligence family. The current tool count remains `23`. The historical selected
candidate was `project.release.summary`; proposal and implementation work completed, and no next
candidate is selected.

## Evaluation Summary

| Candidate | Decision | Short Reason |
| --- | --- | --- |
| `project.release.summary` | Selected | Strongest next fit because it stays count-only and label-only while avoiding release names, version strings, changelog contents, tag names, branch names, package names, and dependency names. |
| `project.license.summary` | Deferred | Plausible count-only metadata, but legal or compliance interpretations can be over-read if labels are too specific. |
| `project.ownership.summary` | Deferred | Ownership metadata can leak people, teams, or customer structure and is too sensitive for this sprint. |

## Candidate Evaluations

### `project.release.summary`

#### Intended Safe Value

Help an agent notice whether release-shaped metadata exists without exposing release names, version
strings, changelog contents, tag names, branch names, package names, dependency names, or file
contents.

#### Proposed Resource Type

`project_release`

#### Safe Output Labels/Counts Only

Release artifact/config counts, release-note and changelog counts by coarse category, version-marker
counts by coarse source category, release automation/config category counts, location buckets,
skipped counts, truncation metadata, and output-policy flags.

#### Strict Non-Goals

No release names, version strings that reveal product/customer cadence, changelog contents, tag
names, branch names, package names, dependency names, author or maintainer names, raw paths, file
contents, shell access, Git execution, package-manager execution, CI execution, or registry data.
No legal, compliance, or shipping-readiness conclusions.

#### Sensitive Metadata Risks

Could expose release cadence, shipping strategy, or product planning if labels drift into specific
release identifiers or version strings.

#### Policy/Audit Evidence Expectations

Require policy preview/runtime parity for the normalized resource, audit evidence with counts and
allowlisted labels only, and negative transcripts showing release names, version strings, and
changelog contents are withheld.

#### Negative Cases

Empty workspace; release artifacts present but unsupported; mixed monorepo release layouts;
ambiguous version markers; recursive traversal beyond reviewed scope.

#### Source-Review Requirement

Required before any implementation decision.

#### Decision

Selected.

### `project.license.summary`

#### Intended Safe Value

Help an agent understand whether license-shaped metadata is present without reading license text or
implying a legal conclusion.

#### Proposed Resource Type

`project_license`

#### Safe Output Labels/Counts Only

License-family counts, allowlisted posture labels, truncation indicators, and support flags only.

#### Strict Non-Goals

No raw filenames, raw paths, license text, package names, dependency names, registry data, or
compliance conclusions.

#### Sensitive Metadata Risks

Could imply legal or compliance posture if labels become too specific or if a narrow license family
is mistaken for approval.

#### Policy/Audit Evidence Expectations

Require policy preview/runtime parity for the normalized resource, audit evidence with counts and
allowlisted labels only, and negative transcripts showing license text and package names are
withheld.

#### Negative Cases

No license files detected; multiple license-like files; mixed-source workspaces; ambiguous copied
headers; recursive traversal beyond reviewed scope.

#### Source-Review Requirement

Required before any implementation decision.

#### Decision

Deferred.

### `project.ownership.summary`

#### Intended Safe Value

Help an agent understand whether ownership-shaped metadata is present without exposing people,
teams, customers, or account structure.

#### Proposed Resource Type

`project_ownership`

#### Safe Output Labels/Counts Only

Presence counts, truncation indicators, and only the coarsest non-identifying category labels a
future policy can prove are safe.

#### Strict Non-Goals

No names, emails, usernames, handles, team labels, customer labels, account identifiers, or any
other direct or indirect person or organization identifiers.

#### Sensitive Metadata Risks

This is the most sensitive candidate because it can reveal org structure, maintainership, customer
relationships, or staffing patterns even when the output is small.

#### Policy/Audit Evidence Expectations

Require policy preview/runtime parity for the normalized resource, audit evidence with counts only,
and negative transcripts showing names and structure labels are withheld.

#### Negative Cases

Any workspace with human ownership metadata; multi-team projects; customer-specific structures;
ambiguous provenance markers; recursive traversal beyond reviewed scope.

#### Source-Review Requirement

Required before any implementation decision.

#### Decision

Deferred.

## Required Future Review

The next step is proposal work for `project.release.summary`, not another candidate search. Any
later proposal must still preserve the planning-only boundary, the current tool count, and the
no-new-powers posture.
