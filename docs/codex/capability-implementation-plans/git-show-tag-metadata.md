# Implementation-Planning Packet: git.show.tag_metadata

Status: implementation-planning only.

This packet does not add a tool manifest, executor, policy rule, MCP exposure, approval behavior,
API behavior, UI behavior, or runtime behavior.

## Planning Decision

- Capability: `git.show.tag_metadata`.
- Implementation state: blocked.
- The tool may proceed only after an explicit implementation decision.
- The boundary is local-only, read-only, fixed-argv Git tag metadata with raw names/messages/signatures suppressed.

## Future Manifest Sketch

- name: `git.show.tag_metadata`;
- risk: `read`;
- category: `git`;
- MCP exposure: read-only after implementation approval;
- input schema: strict `selector.kind: all_local_tags`, optional `workspace_id`, optional bounded `limit`;
- output: bounded local tag metadata only.

No raw tag names, tag messages, tag signatures, stable tag-name hashes, file contents, diffs, raw
Git stderr, remote URLs, credentials, shell output, remotes, checkout, or mutation are allowed.

## Input And Schema Contract

Allowed top-level fields: `workspace_id`, `selector`, and `limit`.
Allowed selector fields: `kind` only.
Allowed selector kind: `all_local_tags`.
`limit` must be an integer from `1` to `200`, default `100`.
Every object schema must use `additionalProperties: false`.

Required negative schema cases include `include_names`, `include_messages`, `include_signatures`,
`ref`, `remote`, `format`, `argv`, `path`, `refspec`, `revision`, `pathspec`, and unknown selector
fields.

## Executor Contract Checklist

If approved, implementation must:

- resolve the workspace through the workspace registry;
- verify the Git repository toplevel is inside the workspace;
- use fixed argv and no shell;
- use internally controlled `git for-each-ref` format strings only;
- query only `refs/tags`;
- parse NUL-delimited structured output;
- validate tag names for control characters, Unicode normalization, byte limit, unsupported syntax,
  and casefold conflicts before suppressing them;
- distinguish `lightweight` and `annotated` tags;
- return only commit targets and skip non-commit tag targets safely;
- enforce byte, count, and runtime limits;
- return response-local `tag_id` handles only;
- label metadata as untrusted.

## Output Contract

Allowed top-level output fields are fixed and count-oriented.
Allowed top-level fields: `workspace_id`, `tool_name`, `selector`, `tag_count`,
`total_tag_count`, `skipped_non_commit_tag_count`, `truncated`, `tags`, and `output_policy`.

Allowed tag entry fields: `tag_id`, `tag_type`, `target_object_type`, `resolved_commit_hash`, and
`peeled_from_tag_object`.

Output must not include raw tag names, stable tag-name hashes, annotated tag messages, signatures,
file names, file contents, diffs, raw Git stderr, remote URLs, credentials, or environment values.

## Policy, Audit, UI, And Review Plan

Policy preview/runtime must use a normalized `git_tags` resource with workspace scope and selector
kind. Audit metadata must contain only selector/count/truncation/skipped/output-policy evidence.
The UI may list the tool as read-only metadata only; no approval workflow or run control changes are
introduced.

Negative tests must cover no tags, lightweight tags, annotated tags, non-commit tag targets,
malformed selectors, unknown fields, limit truncation, parent-repository escape, unknown principal,
and unauthorized principal denial. Source review must receive a focused bundle before local lane
closure.

## Resource Limits

- maximum tags returned: `200`;
- default tags returned: `100`;
- maximum tag name bytes before suppression: `240`;
- maximum total Git output bytes: existing read-tool byte limit;
- safe failure on ambiguous parsing or oversized output.
