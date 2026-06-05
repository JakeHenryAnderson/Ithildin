# v3 project.manifest.summary Implementation Decision

Status: approved for later bounded read-only implementation. This decision document does not add a tool manifest,
does not add an executor, does not add a policy rule, does not add MCP exposure,
does not add approval behavior, does not add API behavior, does not add UI behavior, and does not
add runtime behavior.

`project.manifest.summary` is approved only as a count-oriented local project manifest metadata
capability. It remains a narrow continuation of the read-only local metadata lane, not a new
powerful tool class.

## Approved Boundary

The later implementation may:

- add one manifest named `project.manifest.summary`;
- keep risk `read`, category `project`, and MCP exposure under the existing registry/listing path;
- accept only `workspace_id`, `root`, `manifest_kinds`, and `limit`;
- resolve `root` through the existing workspace and filesystem safety contracts;
- inspect only allowlisted manifest basenames at the selected root;
- parse bounded text manifests for count-only metadata;
- return response-local `manifest_id` handles, ecosystem labels, byte sizes, file digests, section
  counts, script counts, lockfile-presence metadata, parse status, limit status, and output-policy
  flags;
- record safe audit metadata for manifest count, truncation, effective manifest kinds, parser
  status, and output-policy booleans.

## Required Non-Goals

The later implementation must provide no shell, no package-manager execution, no registry or network access,
no recursive discovery, no arbitrary manifest filenames, no caller-controlled parser
options, no file contents, no dependency names, no package names, no dependency version constraints,
no package script names or values, no registry URLs, no repository URLs, no maintainer/author
fields, no lockfile contents, no package-manager stdout/stderr, and no broad filesystem access.

## Evidence Required Before Runtime Commit

- `make project-manifest-summary-implementation-plan-check`
- `make project-manifest-summary-implementation-gate`
- `make tool-surface-invariant-gate`
- `make no-new-powers-guardrail`
- focused read-tool/governed/MCP/policy tests
- `make manifest-lock-check` after the intentional manifest update
- `make release-check`

## Implementation State

Implementation state: approved_limited_read_only.

This decision authorizes only the later bounded read-only implementation described above. It does
not unlock broader capability expansion, public/security-product positioning, arbitrary filesystem
read expansion, package-manager execution, network access, or new powerful tool classes.
