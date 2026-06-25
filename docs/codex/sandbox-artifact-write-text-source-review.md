# sandbox.artifact.write_text Source Review Handoff

Status: future source-review handoff only. No runtime behavior.

This document defines the future source-review lane for `sandbox.artifact.write_text`. The tool is
not implemented. This handoff exists so a later implementation cannot skip the same review
machinery used by the existing local-preview capabilities.

## Current Decision

- Tool candidate: `sandbox.artifact.write_text`.
- Current state: design and implementation planning only.
- Runtime implementation: blocked.
- Manifest: absent by design.
- Tool count: remains `23`.
- Mission Control runtime behavior: not implemented.
- VM lifecycle control: not implemented.
- Host promotion: not implemented.

## Future Reviewer Scope

A future reviewer must inspect:

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

## Future Closure Questions

A reviewer should answer whether the lane can close for the v0.1 local-preview runtime boundary:

1. Does the implementation create only bounded text artifacts under trusted sandbox/staging roots?
2. Are host writes and promotion still separate from sandbox creation?
3. Are overwrite and parent-directory creation bound to explicit approval evidence?
4. Are traversal, symlink, hardlink, hidden, `.git`, and host-root escapes denied?
5. Are responses and audit events free of file contents, raw host paths, prompts, secrets,
   environment values, shell output, VM logs, and unrelated listings?
6. Does Mission Control remain an operator/evidence surface rather than an independent authority?

## Required Future Commands

A future implementation must add and pass commands equivalent to:

```sh
make sandbox-artifact-write-text-implementation-gate
make sandbox-artifact-write-text-preimplementation-check
make sandbox-artifact-write-text-review-handoff-check
make sandbox-artifact-write-text-source-review-bundle
make policy-parity
make release-check
```

This current planning slice adds only `make sandbox-artifact-write-text-preimplementation-check`.

## Finding Namespace

Future source-review findings should use `EXT-SANDBOX-WRITE-###`.

No source-review closure is claimed by this document.
