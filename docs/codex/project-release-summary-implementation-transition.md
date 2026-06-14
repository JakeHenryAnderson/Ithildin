# project.release.summary Implementation Transition

Status: implementation-transition checklist only.

This document is the canonical handoff from the `project.release.summary` preimplementation lane to
a later bounded runtime implementation sprint. It does not add runtime behavior, tool manifests,
manifest-lock entries, executors, policy rules, MCP exposure, API behavior, UI behavior,
approval/audit behavior, or new governed tool powers.

## Current State

- selected capability: `project.release.summary`;
- current tool count: `21`;
- current runtime status: not implemented;
- current guard status: preimplementation guard active;
- current release-check posture: the guard intentionally fails closed if a
  `project.release.summary` manifest, manifest-lock entry, or runtime helper appears before the
  implementation sprint updates the gate.

## Transition Purpose

The approved implementation boundary says `project.release.summary` may be implemented in a later
bounded read-only sprint. The active preimplementation guard says it must not appear in runtime
source yet. This transition checklist exists so the next sprint can flip that state deliberately
instead of accidentally fighting the guard.

## Next Sprint Sequence

The next manager-owned runtime sprint must do these steps in one coherent implementation checkpoint:

1. Replace the preimplementation guard with an implementation-aware gate state.
2. Add exactly one bounded read-only manifest for `project.release.summary`.
3. Add exactly one bounded read-only executor path.
4. Update the manifest lock intentionally.
5. Add policy preview/runtime parity evidence for resource type `project_release`.
6. Add governed pipeline, MCP list/call, schema-rejection, unauthorized-principal, and audit metadata
   coverage.
7. Add negative transcripts and source-review bundle coverage for the implemented lane.
8. Update tool count and read-only inventory evidence.
9. Run `make release-check` and `make review-candidate` from a clean tree.

## Boundary That Must Not Change

The future tool remains:

- local workspace only and read-only;
- count-only and label-only;
- no release names;
- no version strings that reveal cadence;
- no changelog contents;
- no tag names;
- no branch names;
- no raw paths;
- no raw file names;
- no file contents;
- no package names;
- no dependency names;
- no author or maintainer names;
- no shell;
- no Git execution;
- no package-manager execution;
- no CI execution;
- no registry or network access;
- no deployment-readiness, legal, compliance, or public/security-product claims;
- no new powerful tool class.

## Delegation Rule

Low implementers may help with fixture inventory or docs-only scans. Runtime implementation,
manifest edits, policy/resource semantics, governed dispatch, MCP exposure, audit metadata, source
review disposition, gate changes, and commits remain main-manager work.

## Stop Conditions

Stop the next sprint if implementation requires exposing raw release names, version strings, raw
paths, file contents, commands, dependency names, package names, author/maintainer identity,
registry URLs, Git output, package-manager output, CI output, or any broader runtime power.

Stop if tool count changes by more than the single expected `project.release.summary` manifest, if
policy/resource parity cannot be preserved, if release-check assumptions diverge from this contract,
or if implementation would require changing the v1.0 RC deferred-power list.

