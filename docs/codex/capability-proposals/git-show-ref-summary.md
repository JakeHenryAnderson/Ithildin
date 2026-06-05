# Capability Proposal: git.show.ref_summary

Status: design-only proposal.

This proposal does not add a tool manifest, executor code, API behavior, MCP exposure, policy rule,
approval behavior, UI behavior, or runtime behavior. It is planning material for a possible future
read-only local Git metadata tool. Implementation remains blocked until a separate implementation
plan, source review, and explicit capability decision are recorded.

## Purpose

`git.show.ref_summary` would help an agent orient around local repository refs without exposing raw
Git command execution, file contents, diffs, patch hunks, remote state, credentials, or branch
mutation. It is intended to complement the already reviewed `git.show.commit_metadata` lane by
returning bounded local ref metadata only.

## Proposed Input Shape

```json
{
  "workspace_id": "default",
  "selector": {
    "kind": "all_local"
  },
  "limit": 100
}
```

- `workspace_id`: optional workspace identifier resolved through the existing workspace registry.
- `selector.kind`: one of `all_local`, `branch`, or `tag`.
- `limit`: optional integer capped by the executor contract, proposed maximum `200`.

Strict schema validation must reject unknown properties. No caller-controlled argv, Git format
string, revision expression, pathspec, ref glob, remote name, raw ref name, display-name option, or
filesystem path is accepted. The first implementation plan must reject `include_names`,
`include_current_branch`, `ref`, `remote`, `format`, `argv`, `path`, `refspec`, and all other
unknown fields.

## Proposed Output Shape

```json
{
  "workspace_id": "default",
  "selector": {"kind": "all_local"},
  "ref_count": 2,
  "truncated": false,
  "refs": [
    {
      "kind": "branch",
      "ref_id": "ref_0001",
      "is_current_branch": true,
      "resolved_commit": "0123456789abcdef0123456789abcdef01234567"
    },
    {
      "kind": "tag",
      "ref_id": "ref_0002",
      "resolved_commit": "fedcba9876543210fedcba9876543210fedcba98",
      "peeled_from_tag_object": false
    }
  ],
  "redaction": {
    "names_returned": false,
    "ref_ids_are_response_local": true,
    "stable_hash_privacy_caveat": true
  }
}
```

Output must be structured metadata only. It must not include commit subjects, commit bodies,
annotated tag messages, file names, diffstat, diffs, file contents, remote URLs, reflogs, Git config,
raw ref names, stable ref-name hashes, raw stderr, credentials, environment values, or shell output.

## Ref Name Privacy Policy

Branch and tag names can reveal customer names, incident IDs, security work, unreleased products,
or personal identifiers. First implementation planning must therefore return response-local opaque
`ref_id` values only. Raw ref names are future-only and rejected for the first implementation plan.
The current branch must follow the same policy: it may be indicated only as `is_current_branch: true`
on a response-local ref entry, not as a raw name.

Stable hashes are not anonymity guarantees; reviewers must treat them as local correlation aids with dictionary-attack risk. First implementation planning must not return raw `sha256(refname)` values. If a later reviewed mode needs cross-response correlation, it must define a separate domain-separated keyed HMAC or repository/workspace-scoped salted digest contract, including canonical hash input, digest version, key/salt scope, rotation behavior, audit wording, and external/source review. That later mode remains out of scope here.

## Ref Selection Policy

The tool would inspect only local refs under:

- `refs/heads/<name>`
- `refs/tags/<name>`

It must not inspect or return:

- remote-tracking refs such as `refs/remotes/origin/main`;
- remote names such as `origin/main`;
- reflog selectors such as `HEAD@{1}`;
- revision expressions such as `HEAD~1`, `main^`, ranges, or `main..feature`;
- pathspec-like selectors such as `main:README.md`;
- message selectors such as `:/message`;
- arbitrary ref globs, caller-supplied `for-each-ref` patterns, or format strings;
- symbolic-ref targets outside the approved local branch/tag namespace.

Ref names containing control characters, ambiguous Unicode normalization, invalid UTF-8, path
separators outside Git's valid ref syntax, repeated/trailing-dot ambiguity, or other hard-to-review
forms should fail closed with safe errors.

## Strict Schema Contract

The first implementation plan must use a JSON Schema with `additionalProperties: false` at every
object level. Required validation rules:

- top-level fields: `workspace_id`, `selector`, and `limit` only;
- `selector` fields: `kind` only;
- `selector.kind`: exact enum `all_local`, `branch`, or `tag`;
- `limit`: integer, minimum `1`, maximum `200`;
- no raw ref selector field;
- no display-name field;
- no current-branch name option;
- no Git argv, format, path, remote, refspec, revision, glob, pathspec, or environment field.

Concrete malicious JSON inputs that must be denied before execution:

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

## Executor Contract Sketch

The future executor contract must specify a fixed parse-normalize-resolve flow:

1. Resolve the workspace through the existing workspace registry.
2. Verify the Git repository root is inside the workspace root.
3. Use fixed Git argv only, with `--end-of-options` where applicable.
4. Use internally controlled `git for-each-ref` format strings only.
5. Query only `refs/heads` and/or `refs/tags` based on the structured selector.
6. Parse NUL-delimited or otherwise unambiguous structured output.
7. Validate each full refname by exact namespace prefix, UTF-8 decoding, Unicode NFC policy, control
   character rejection, Git ref-format round trip, and casefold-conflict detection where the host
   filesystem profile makes that relevant.
8. Reject or skip symbolic refs outside the approved local branch/tag namespace.
9. For tags, distinguish lightweight tags from annotated tags and verify the peeled object is a commit.
   Non-commit tag targets must be denied or reported as skipped without exposing tag messages or
   object contents.
10. Verify every returned object ID names a commit object.
11. Enforce count, byte, and runtime limits before returning.
12. Replace ref names with response-local `ref_id` values before policy/audit evidence and response
   construction.

The executor must never use shell execution, caller-controlled argv, caller-controlled format
strings, checkout, branch creation/deletion, tag mutation, remote fetch/pull/push, credential access,
or broad filesystem reads.

## Policy Fixtures

Future policy fixtures should cover:

- read-capable principals receiving `allow` for in-scope workspace ref metadata;
- read-only/auditor principals receiving `allow` if the default role/risk matrix permits Git read
  metadata;
- unknown and disabled principals receiving deny-style results before execution;
- out-of-scope workspace IDs receiving deny-style results;
- dangerous/destructive tool-risk rules remaining unaffected.

## Audit Fields

Runtime audit evidence, if implemented later, should include:

- tool name `git.show.ref_summary`;
- manifest hash/version once a manifest exists;
- workspace ID and normalized repository root evidence without leaking host-only path detail beyond
  existing workspace evidence conventions;
- selector kind;
- requested limit and effective limit;
- returned count and truncation flag;
- whether ref names were returned; expected value for first implementation planning is `false`;
- whether stable ref-name hashes were returned; expected value for first implementation planning is
  `false`;
- response-local ref ID mode;
- stable hash privacy caveat flag;
- policy version/hash, matched rules, and obligations;
- principal ID/roles after trusted registry normalization;
- safe error reason for denied or failed cases.

It must not audit raw ref names when names are not returned, raw Git stderr, remote URLs, commit
messages, file paths, diffs, file contents, or credentials.

## Resource Limits

Proposed limits for implementation planning:

- maximum refs returned: `200`;
- maximum ref name bytes before hashing/redaction: `240`;
- maximum total Git output bytes: `131072`;
- maximum executor runtime: `5` seconds;
- maximum current-branch name bytes: `240`;
- safe failure when the repository exceeds limits or parsing becomes ambiguous.

## Negative Transcripts

Negative transcript sketches should be added before implementation:

- remote ref selector denied with concrete malicious JSON;
- revision syntax denied (`HEAD~1`, `HEAD@{1}`, `main..feature`);
- pathspec-like selector denied (`main:README.md`);
- caller-supplied format string denied;
- control-character or non-normalized ref name denied or redacted before output;
- raw-name request denied (`include_names`, `include_current_branch`);
- unknown JSON properties denied by strict schema validation;
- annotated tag peeling to non-commit target denied or skipped safely;
- casefold-conflicting refs denied or skipped safely;
- symbolic ref outside `refs/heads/*` and `refs/tags/*` denied or skipped safely;
- oversized ref set truncated safely;
- unknown principal denied;
- disabled workspace denied;
- repository root outside workspace denied.

## UI/review Evidence

No UI surface is proposed in this design-only step. If implemented later, the review console may list
the tool only as a read-only metadata capability and should label ref names as repository-supplied
untrusted metadata. No approval workflow should be required for bounded name-free local-ref metadata
under the default read policy, but policy preview/runtime evidence must stay comparable. Stable
hashes, HMAC modes, salted digest modes, and raw-name modes remain out of scope pending separate
review.

## Accepted-Risk Impact

This proposal does not change the accepted-risk register because it adds no runtime behavior. If
implementation planning proceeds, the implementation plan must revisit:

- local Git metadata privacy risk;
- stable hash dictionary risk;
- repository-controlled metadata display risk;
- exact workspace confinement assumptions;
- policy/audit evidence stability.

## No-New-Powers Analysis

This is a design-only proposal. It does not add:

- a manifest;
- an executor;
- a policy rule;
- MCP exposure;
- API behavior;
- approval behavior;
- UI behavior;
- shell execution;
- broad filesystem reads or writes;
- remote Git access;
- network access;
- credential access.

If implemented later, the intended power class would remain read-only local Git metadata and would
not authorize branch mutation, checkout, fetch, pull, push, merge, rebase, reset, stash, or file
content access.

## External/source Review Requirement

Before implementation planning may begin, this proposal needs internal xhigh review focused on
privacy, Git ref normalization, and boundary drift. Before any runtime implementation can ship, a
separate source-review lane must inspect the implementation plan, manifest, executor, tests, policy
fixtures, audit evidence, MCP path, and review-packet evidence.
