# sandbox.artifact.write_text Source Review Handoff

Status: runtime source-review handoff pending.

This document defines the source-review lane for the bounded local-preview
`sandbox.artifact.write_text` implementation. The tool is implemented, but this document does not
claim external/source-review closure.

## Current Decision

- Tool candidate: `sandbox.artifact.write_text`.
- Current state: bounded local-preview runtime implementation present.
- Runtime implementation: approval-bound sandbox text artifact creation only.
- Manifest: present.
- Tool count: remains `24`.
- Mission Control runtime behavior: not implemented.
- VM lifecycle control: not implemented.
- Host promotion: not implemented.

## Reviewer Scope

A reviewer must inspect:

- manifest/schema and manifest-lock update;
- executor implementation and filesystem path handling;
- sandbox profile validation;
- approval binding and one-time consumption;
- audit metadata and redaction behavior;
- policy preview/runtime parity for `sandbox_artifact`;
- MCP exposure through the governed path;
- negative transcripts and fixture coverage;
- promotion separation from artifact creation;
- Mission Control evidence attachment semantics.

## Closure Questions

A reviewer should answer whether the lane can close for the v0.1 local-preview runtime boundary:

1. Does the implementation create only bounded text artifacts under trusted sandbox/staging roots?
2. Are host writes and promotion still separate from sandbox creation?
3. Are overwrite and parent-directory creation bound to explicit approval evidence?
4. Are traversal, symlink, hardlink, hidden, `.git`, and host-root escapes denied?
5. Are responses and audit events free of file contents, raw host paths, prompts, secrets,
   environment values, shell output, VM logs, and unrelated listings?
6. Does Mission Control remain an operator/evidence surface rather than an independent authority?

## Required Commands

The implementation must pass:

```sh
make sandbox-artifact-write-text-implementation-gate
make policy-parity
make release-check
```

Future closure work should add a focused source-review bundle and negative transcript generator if
this lane is sent for external/source review.

## Finding Namespace

Source-review findings should use `EXT-SANDBOX-WRITE-###`.

No source-review closure is claimed by this document.
