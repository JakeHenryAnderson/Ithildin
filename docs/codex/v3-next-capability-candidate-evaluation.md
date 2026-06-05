# v3 Next Capability Candidate Evaluation

Status: design-only candidate evaluation. This document evaluates the next narrow read-only
metadata candidate after `git.show.commit_metadata` and `git.show.ref_summary`.

Selected candidate: `project.manifest.summary`.

This evaluation does not add a manifest, does not add an executor, and does not add policy rules.
It does not add MCP exposure, does not add API behavior, does not add UI behavior, and does not add
runtime behavior. Actual implementation remains blocked until a full proposal, implementation plan,
source-review handoff, internal xhigh review, release-gate wiring, and explicit implementation
decision are recorded for this one capability.

## Candidate Shape

`project.manifest.summary` would be a local read-only project-orientation tool. A future proposal may
explore whether it can safely report bounded metadata about common project manifest files in the
workspace root or a reviewed workspace-relative subdirectory.

Possible metadata, subject to later proposal review:

- manifest kind, such as `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, or lockfile;
- response-local manifest IDs;
- ecosystem labels such as Python, Node, Go, or Rust;
- dependency counts by section;
- package script count only;
- manifest file byte size and digest;
- truncation and unsupported-manifest evidence.

## Non-Goals

A future implementation must preserve:

- no file contents;
- no package script values;
- no dependency names by default;
- no package version constraints by default;
- no package installation, execution, build, test, or lifecycle-script behavior;
- no registry or network access;
- no shell;
- no arbitrary manifest paths;
- no recursive repository scan by default;
- no lockfile body output;
- no credential, token, private registry URL, or environment-variable output.

## Why This Candidate

This is a reasonable next design target because it helps an agent understand a local project’s
ecosystem without reading source files, raw manifests, package scripts, dependency names, or lockfile
contents. It also exercises a useful v3 pattern: bounded project metadata with strong parser and
redaction contracts rather than general file reads or shell inspection.

## Required Future Proposal Sections

A real proposal must include:

- exact input and output shapes;
- manifest allowlist and parser contract;
- privacy policy for package names, dependency names, script names, script values, registry URLs,
  and lockfile metadata;
- policy preview/runtime resource shape;
- audit evidence fields;
- negative cases and transcripts;
- size limits and parse limits;
- UI/review expectations;
- accepted-risk impact;
- source-review bundle plan;
- explicit implementation decision requirement.

## Deferred Alternatives

- `git.show.tag_metadata`: deferred because annotated tag messages can expose untrusted text and
  possible secrets, and tag reachability is already partially served by `git.show.ref_summary`.
- `dependency.manifest.summary`: deferred until the project-manifest privacy policy decides whether
  dependency names and versions can be exposed.
- `git.show.remote_summary`: deferred because remote URLs and names can expose private hosts,
  organizations, and repository intent.
