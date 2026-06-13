# Capability Proposal: git.show.tag_metadata

Status: design-only proposal.

This proposal does not add a tool manifest, executor code, API behavior, MCP exposure, policy rule,
approval behavior, UI behavior, or runtime behavior.

## Purpose

`git.show.tag_metadata` would help an agent understand local repository tag posture without raw Git
execution, tag names, annotated tag messages, signatures, remotes, file contents, diffs, checkout,
mutation, credentials, or shell access.

## Proposed Input Shape

```json
{
  "workspace_id": "default",
  "selector": {"kind": "all_local_tags"},
  "limit": 100
}
```

Allowed inputs are `workspace_id`, `selector.kind`, and `limit` only. `selector.kind` is exactly
`all_local_tags`. Strict JSON Schema must use `additionalProperties: false` at every object level.
Unknown fields such as `include_names`, `include_messages`, `include_signatures`, `ref`, `remote`,
`format`, `argv`, `path`, `refspec`, `revision`, and `pathspec` must be rejected before execution.

## Proposed Output Shape

```json
{
  "workspace_id": "default",
  "tool_name": "git.show.tag_metadata",
  "selector": {"kind": "all_local_tags"},
  "tag_count": 2,
  "total_tag_count": 2,
  "truncated": false,
  "tags": [
    {
      "tag_id": "tag_0001",
      "tag_type": "lightweight",
      "target_object_type": "commit",
      "resolved_commit_hash": "0123456789abcdef0123456789abcdef01234567"
    }
  ],
  "output_policy": {
    "tag_names_included": false,
    "tag_messages_included": false,
    "tag_signatures_included": false,
    "stable_tag_hashes_included": false,
    "tag_ids_are_response_local": true,
    "metadata_is_untrusted": true
  }
}
```

Output is safe metadata only. It must not include raw tag names, stable tag-name hashes, annotated
tag messages, tag signatures, raw Git stderr, remote URLs, file names, file contents, diffs, refs
outside `refs/tags/*`, credentials, environment values, or shell output.

## Executor Contract Sketch

The future executor must resolve the workspace, verify the Git toplevel is inside the workspace,
run fixed `git for-each-ref` argv against `refs/tags` only, parse internally controlled structured
output, validate tag names only for safety before suppressing them, distinguish lightweight and
annotated tags, peel annotated tags only to commits, skip non-commit targets safely, enforce byte and
count limits, and replace tag names with response-local `tag_id` values before response/audit.

The executor must never use shell execution, caller-controlled argv, caller-controlled format
strings, checkout, tag creation/deletion, branch mutation, remote fetch/pull/push, credential
access, package-manager execution, or broad filesystem reads.

## Policy, Audit, And Review Evidence

Future policy fixtures must prove read-capable principals receive `allow` for in-scope local tag
metadata, unauthorized/unknown principals deny before execution, unknown workspaces deny safely, and
preview/runtime resource evidence uses a normalized `git_tags` resource.

Audit evidence should include tool name, manifest hash/version, workspace ID, selector kind,
requested/effective limit, returned count, total count, truncation flag, skipped non-commit count,
and output-policy booleans. It must not include tag names, messages, signatures, raw Git stderr,
remote URLs, file contents, diffs, or credentials.

Implementation requires an implementation plan, explicit implementation decision, manifest lock
update, policy parity evidence, negative tests, resource limits, source-review handoff bundle, and
release/readiness gates.

## Negative Cases

Required denial or safe-skip cases include caller-supplied names/messages/signatures, remotes,
revision syntax, pathspec-like selectors, unknown schema fields, non-commit tag targets,
casefold-conflicting or malformed tag names, oversized output, unknown workspace, disabled
workspace, and repository root outside workspace.

## No-New-Powers Analysis

This is a bounded read-only metadata proposal. It does not add a new powerful tool class and does
not approve arbitrary Git execution, raw ref/tag exposure, shell, Docker, Kubernetes, browser
automation, arbitrary HTTP, broad filesystem writes, production identity, runtime Postgres, hosted
telemetry, remote MCP, plugin SDK behavior, sandbox orchestration, SIEM adapters, or compliance
claims.
