# Implementation-Planning Packet: git.show.ref_summary

Status: historical implementation-planning packet; later advanced through the approved bounded
`git.show.ref_summary` implementation and source-review handoff.

Original status: implementation-planning only.

Original marker: Status: implementation-planning only.

Historical invariant: this document does not add a tool manifest, executor, policy rule, MCP
exposure, approval behavior, API behavior, UI behavior, or runtime behavior. It is kept as lineage
for the bounded
implementation now recorded in
[../v0.9-git-ref-summary-implementation.md](../v0.9-git-ref-summary-implementation.md) and
[../v0.9-git-ref-summary-source-review.md](../v0.9-git-ref-summary-source-review.md). It does not
authorize additional Git tools or broader capability expansion.

## Planning Decision

- Capability: `git.show.ref_summary`.
- Planning state: completed as historical lineage.
- Implementation state: completed for the one bounded read-only lane only.
- Original implementation state: blocked.
- Original marker: Implementation state: blocked.
- Original assertion: Actual implementation remains blocked until a later internal xhigh source
  review, source-level implementation packet, and explicit implementation go decision.
- The original planning packet is still checked with `make git-ref-summary-implementation-plan-check`
  so the lineage stays reviewable.

## Boundary

This planning packet must not create or modify:

- `tool-manifests/` files or `tool-manifests.lock.json`;
- executor code or governed tool dispatch;
- API or MCP runtime behavior;
- policy rules or approval behavior;
- UI behavior;
- registry behavior, principal behavior, workspace behavior, or audit storage behavior.

It may describe future work, proposed contracts, expected tests, and required evidence.

## Future Manifest Sketch

If implementation is later approved, the future manifest should describe a read-only local Git
metadata tool:

- name: `git.show.ref_summary`;
- risk: `read`;
- category: `git`;
- MCP exposure: yes only after explicit implementation approval;
- input schema: strict structured selector only;
- output schema: bounded local-ref metadata only;
- no raw ref names, stable raw ref-name hashes, commit messages, file contents, diffs, patch hunks,
  raw Git stderr, remote URLs, credentials, or shell output.

This is a sketch only. No manifest is added in this planning sprint.

## Proposed Input Contract

The future input schema should include:

- `workspace_id`: optional configured workspace ID.
- `selector`: required object with exactly one field:
  - `kind`: exact enum `all_local`, `branch`, or `tag`.
- `limit`: optional integer, minimum `1`, maximum `200`, default `100`.

The first implementation plan must reject raw-name and current-branch-name options. It must not
accept `include_names`, `include_current_branch`, `ref`, `remote`, `format`, `argv`, `path`,
`refspec`, revision syntax, pathspecs, ref globs, environment variables, or caller-supplied Git
format strings.

## Strict Schema Contract

Future schema validation must use `additionalProperties: false` at every object level.

Allowed top-level properties:

- `workspace_id`;
- `selector`;
- `limit`.

Allowed `selector` properties:

- `kind`.

Required negative schema cases:

```json
{"selector":{"kind":"branch","ref":"refs/heads/main"}}
{"selector":{"kind":"branch"},"include_names":true}
{"selector":{"kind":"branch"},"include_current_branch":true}
{"selector":{"kind":"branch"},"format":"%(refname)"}
{"selector":{"kind":"branch"},"argv":["for-each-ref","refs/remotes"]}
{"selector":{"kind":"branch"},"remote":"origin"}
{"selector":{"kind":"branch"},"refspec":"origin/main"}
{"selector":{"kind":"branch"},"path":"README.md"}
```

These inputs must fail before execution and must not write audit events that expose rejected values
beyond safe denial metadata.

## Executor Contract Checklist

A future executor, if approved, must:

- run only inside a workspace root accepted by the workspace registry and Git safety layer;
- verify the Git repository toplevel is inside the configured workspace root;
- avoid shell interpretation entirely;
- use fixed argv only;
- use `--end-of-options` where Git argv could otherwise parse user-like values as options;
- use internally controlled `git for-each-ref` format strings only;
- query only `refs/heads` and/or `refs/tags` based on `selector.kind`;
- parse NUL-delimited or otherwise unambiguous structured output;
- suppress proxy/network behavior by construction by using local Git read operations only;
- enforce count, byte, and runtime limits;
- return safe errors without raw Git stderr, ref names, file contents, patch contents, environment,
  credentials, or command output beyond bounded returned metadata.

## Ref Enumeration And Validation Plan

Future tests and implementation must cover:

- `all_local` enumerating only `refs/heads/*` and `refs/tags/*`;
- `branch` enumerating only `refs/heads/*`;
- `tag` enumerating only `refs/tags/*`;
- remote-tracking refs such as `refs/remotes/origin/main` excluded by construction;
- local branch names that textually resemble remotes, such as `origin/main`, treated only as local
  branch refs if Git accepts them under `refs/heads/*`;
- full-refname validation by exact namespace prefix;
- UTF-8 decoding and Unicode NFC policy;
- control-character rejection;
- Git ref-format round trip;
- repeated-dot, trailing-dot, slash, and casefold-conflict detection where relevant to the supported
  platform profile;
- symbolic refs outside `refs/heads/*` and `refs/tags/*` denied or skipped safely;
- detached HEAD reported only as absence of `is_current_branch`, not as a name;
- annotated tags peeled safely;
- lightweight tags handled safely;
- non-commit tag targets denied or skipped safely;
- every returned object ID verified as a commit object.

## Ref Privacy And Output Contract

The first implementation plan must return response-local opaque `ref_id` values only. It must not return raw ref names. It must not return raw `sha256(refname)` values.

Returned entries may include:

- `kind`: `branch` or `tag`;
- `ref_id`: response-local opaque identifier such as `ref_0001`;
- `is_current_branch`: boolean for branch entries only, with no branch name;
- `resolved_commit`: full commit object ID;
- `peeled_from_tag_object`: boolean for tag entries when relevant.

Future output schema validation must use `additionalProperties: false` at every object level.

Allowed top-level output fields:

- `workspace_id`;
- `selector`;
- `ref_count`;
- `truncated`;
- `refs`;
- `redaction`.

Allowed branch entry fields:

- `kind`;
- `ref_id`;
- `is_current_branch`;
- `resolved_commit`.

Allowed tag entry fields:

- `kind`;
- `ref_id`;
- `resolved_commit`;
- `peeled_from_tag_object`.

No other response fields are allowed in the first implementation plan. Branch entries must not
include raw names or tag-only fields. Tag entries must not include `is_current_branch` or raw names.

Stable hashes are not anonymity guarantees. If a later reviewed mode needs cross-response
correlation, it must define a separate domain-separated keyed HMAC or repository/workspace-scoped
salted digest contract, including canonical hash input, digest version, key/salt scope, rotation
behavior, audit wording, and external/source review.

## Policy Fixture Plan

Future policy fixtures must prove:

- read-capable principal and in-scope workspace metadata returns `allow`;
- read-only/auditor principal remains read-only under the existing role matrix;
- unknown, disabled, or spoofed principals deny before execution;
- disabled or unknown workspace denies before execution;
- out-of-scope workspace/root denies before execution;
- unknown schema properties deny before policy execution;
- write/network/destructive obligations are not introduced;
- policy preview and runtime resource evidence are comparable.

No policy rule is added in this planning sprint.

## Audit Evidence Plan

Future audit metadata should include:

- tool name, manifest hash/version, and schema version;
- normalized principal and session ID;
- workspace ID and in-scope repository evidence;
- selector kind;
- requested limit and effective limit;
- returned count and truncation flag;
- whether response-local opaque ref IDs were used;
- whether raw ref names were returned; expected value `false`;
- whether stable ref-name hashes were returned; expected value `false`;
- stable hash privacy caveat flag;
- timeout and limit status;
- safe error reason when denied or failed.

It must not include raw ref names, raw stable ref-name hashes, raw Git stderr, remote URLs, commit
messages, file paths, file contents, patch contents, environment variables, credentials, or command
output beyond bounded returned metadata.

## UI And Policy Preview Plan

Future UI/review behavior should:

- show the tool in registered-tools only after a manifest is intentionally added later;
- show read risk, Git category, workspace scope, and bounded-output warnings;
- show policy preview evidence for principal, workspace, selector kind, resource scope, decision,
  matched rules, obligations, and redaction/limit expectations;
- label `is_current_branch` as name-free branch orientation only;
- expose no execution controls beyond the existing governed tool path.

## Negative Transcript Plan

Future negative transcripts or tests must cover:

- remote ref selector denial;
- revision-expression denial (`HEAD~1`, `HEAD@{1}`, ranges, `:/message`);
- pathspec-like selector denial (`main:README.md`);
- caller-supplied Git format denial;
- caller-supplied argv denial;
- raw-name request denial (`include_names`, `include_current_branch`);
- unknown JSON properties denied by strict schema validation;
- control-character or non-NFC ref names denied or skipped safely;
- casefold-conflicting refs denied or skipped safely;
- symbolic ref outside local branch/tag namespace denied or skipped safely;
- annotated tag peeling to non-commit target denied or skipped safely;
- oversized ref set truncated safely;
- unknown/disabled workspace denial;
- unknown/disabled/spoofed principal denial;
- safe error output with no raw names, raw stderr, contents, credentials, or environment.

## Resource Limits

Initial planning limits:

- maximum refs returned: `200`;
- maximum ref name bytes before validation: `240`;
- maximum total Git output bytes: `131072`;
- maximum command runtime: `5` seconds;
- no binary/content-bearing output by construction.

These are planning defaults and must be revalidated during implementation review.

## Source Review And Implementation Decision Requirement

Before implementation begins, an internal xhigh reviewer must inspect this implementation plan for
boundary drift, Git ref canonicalization, schema strictness, ref privacy, and audit evidence. A later
implementation sprint must produce source-level review artifacts for:

- manifest and lock update;
- executor implementation;
- schema validation;
- policy preview/runtime parity;
- audit evidence;
- MCP exposure;
- UI/tool-list evidence;
- negative transcripts and focused tests.

Actual implementation remains blocked until that later source review and explicit implementation
decision are recorded. This planning sprint adds no manifest, executor, policy rule, MCP exposure, or
runtime behavior.
