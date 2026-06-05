# v3 project.manifest.summary Source Review Handoff

Status: internally prepared for bounded local-preview source review.

This document records the source-review handoff for the bounded v3
`project.manifest.summary` implementation. It prepares the read-only project manifest metadata tool
for optional external/source review. It does not approve future capability expansion or
public/security-product positioning.

## Review Boundary

- Area: `project-manifest-summary`.
- Finding namespace: `EXT-PMS-###`.
- Source-review status: source-review packet prepared; external/source disposition optional/deferred
  unless a future capability gate requires it.
- Runtime boundary: v0.1 local-preview.
- Capability boundary: exactly one bounded read-only project manifest metadata tool.

The handoff bundle is generated with:

```sh
make project-manifest-summary-source-review-bundle
```

The ignored output directory is:

```text
var/review-packets/v0.9/project-manifest-summary-source-review/
```

## Bundle Contents

The generated bundle contains exactly ten review attachments:

1. index;
2. source-review prompt;
3. implementation packet;
4. source bundle;
5. tests bundle;
6. contracts/docs bundle;
7. evidence summary;
8. focused test transcript;
9. external-review intake commands;
10. artifact hashes.

The source bundle includes the tool manifest, manifest lock, read-tool executor path, resource
construction, policy preview/runtime path, MCP adapter path, and policy-parity wiring. The tests
bundle includes direct read-tool coverage, governed-call coverage, MCP coverage, policy-parity
fixtures, tool-registry coverage, manifest-change review coverage, and release-readiness assertions.

## Review Questions

Review should focus on:

- schema shape and denial of unsupported caller fields;
- workspace-root confinement through the existing filesystem safety contract;
- allowlisted manifest basename handling only;
- symlink, hardlink, hidden/sensitive path, traversal, binary, encoding, and size-limit denials;
- count-only parser behavior and absence of file contents, dependency names, version constraints,
  package names, script names/values, registry URLs, repository URLs, and package-manager output;
- policy preview/runtime parity for the syntactic `project_manifest` resource;
- MCP exposure and role visibility through the existing governed pipeline;
- audit metadata staying limited to manifest count, truncation, parser status, manifest kind, and
  output-policy evidence;
- no-new-powers and tool-surface gates staying limited to this bounded read-only addition.

## Closure Boundary

Even if this source-review lane closes, it does not approve:

- shell execution;
- package-manager execution;
- registry or network access;
- recursive project discovery;
- arbitrary manifest filenames;
- dependency-name or package-script disclosure;
- broad filesystem access;
- write behavior, approval changes, production identity, hosted telemetry, runtime Postgres, remote
  MCP, public/security-product positioning, or future governed tool powers.

`project.manifest.summary` remains local-preview read-only metadata mediation, not a project
security scanner or dependency inventory system.
