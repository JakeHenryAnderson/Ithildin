# Capability Proposal: project.manifest.summary

Status: design-only proposal. This document does not add a tool manifest. This document does not
add an executor. It does not add policy rules, does not add MCP exposure, does not add API behavior,
does not add UI behavior, and does not add runtime behavior.

Boundary markers: does not add an executor; no registry or network access.

`project.manifest.summary` is a proposed local read-only project-orientation capability. It would
return bounded metadata about approved project manifest files without returning raw manifest file
contents, dependency names by default, package script values, lockfile bodies, registry credentials,
or network-derived package information.

## Purpose

Agents often need quick orientation around a workspace before choosing read-only inspection paths.
Today they can list files or read specific manifests directly, but that either exposes raw text or
requires the agent to infer ecosystem shape manually. `project.manifest.summary` would provide a
safer middle layer: structured counts and ecosystem labels for a tiny manifest allowlist.

The capability is intended to complement `git.show.commit_metadata` and `git.show.ref_summary` by
adding bounded project metadata, not general file reading or package-manager behavior.

## Proposed Input Shape

```json
{
  "workspace_id": "default",
  "root": ".",
  "manifest_kinds": ["package.json", "pyproject.toml"],
  "limit": 20
}
```

- `workspace_id`: optional workspace ID resolved through the existing workspace registry.
- `root`: optional workspace-relative directory, default `"."`.
- `manifest_kinds`: optional array of allowlisted manifest basenames.
- `limit`: optional integer count limit for returned manifest summaries.

## Strict Schema Contract

A future implementation plan must use strict JSON Schema with `additionalProperties: false` at
every object level.

Top-level fields:

- `workspace_id`;
- `root`;
- `manifest_kinds`;
- `limit`.

The schema must reject caller-controlled glob patterns, recursive scan depth, arbitrary filenames,
absolute paths, package-manager commands, parser options, network options, registry URLs, include
flags for raw contents, and include flags for dependency or script names.

Concrete malicious JSON inputs that must be denied before execution:

```json
{"path":"package.json"}
{"root":"../outside"}
{"manifest_kinds":["../../secrets.env"]}
{"glob":"**/package.json"}
{"include_file_contents":true}
{"include_script_values":true}
{"include_dependency_names":true}
{"registry_url":"https://registry.example.test"}
{"command":"npm install"}
{"argv":["npm","ls"]}
```

## Manifest Allowlist

The first implementation plan may consider only these manifest basenames:

- `package.json`;
- `pyproject.toml`;
- `go.mod`;
- `Cargo.toml`;
- `pom.xml`;
- `build.gradle`;
- `requirements.txt`;
- `Gemfile`;
- `composer.json`.

Lockfiles may be detected as presence/count metadata only. A first implementation must not return
lockfile contents, lockfile dependency names, integrity hashes, registry URLs, or resolved package
source URLs.

## Proposed Output Shape

```json
{
  "workspace_id": "default",
  "root": ".",
  "manifest_count": 2,
  "truncated": false,
  "manifests": [
    {
      "manifest_id": "manifest_0001",
      "kind": "package.json",
      "ecosystem": "node",
      "size_bytes": 2310,
      "sha256": "sha256:...",
      "dependency_section_counts": {
        "dependencies": 12,
        "devDependencies": 8
      },
      "script_count": 4,
      "dependency_names_included": false,
      "script_values_included": false,
      "file_contents_included": false
    }
  ],
  "output_policy": {
    "file_contents_included": false,
    "dependency_names_included": false,
    "package_script_values_included": false,
    "registry_or_network_access_used": false,
    "metadata_is_untrusted": true
  }
}
```

Output must be structured metadata only. It must include no file contents, no package script values,
no dependency names by default, no package version constraints by default, no registry or network
access, no package-manager stdout/stderr, no lockfile body output, no credentials, no
environment values, and no shell output.

## Parser Contract Sketch

A future executor contract must specify a fixed parse-normalize-read flow:

1. Resolve the workspace through the existing workspace registry.
2. Resolve `root` as a relative path confined inside the workspace root.
3. Deny symlinks, hidden/sensitive path segments, `.git` internals, parent traversal, absolute
   paths, control characters, and non-NFC path text using the filesystem contract.
4. Inspect only the approved manifest allowlist at the selected root. A future recursive mode would
   require a separate proposal.
5. Open files through the existing read-tool path safety layer.
6. Enforce file-size and total-output limits before parsing.
7. Parse each manifest with structured parsers or deliberately tiny fixed parsers for count-only
   metadata. Avoid ad hoc extraction of sensitive values.
8. Emit response-local manifest IDs, ecosystem labels, section counts, byte sizes, digest evidence,
   parse-status evidence, and output-policy flags.
9. Treat all manifest text as untrusted repository-controlled metadata.

The executor must never use shell execution, package-manager commands, registry/network access,
caller-controlled argv, caller-controlled parser options, broad filesystem search, or package
lifecycle scripts.

## Privacy Policy

Project manifests can expose customer names, private package names, internal service names, private
registry URLs, scripts with secrets, install hooks, repository URLs, maintainer identities, and
dependency vulnerability context. First implementation planning must therefore be count-oriented.

Required privacy choices:

- no file contents;
- no package script values;
- no dependency names by default;
- no package version constraints by default;
- no registry URLs;
- no repository URLs;
- no maintainer or author fields;
- no license text values beyond a boolean or count if needed;
- no stable cross-response package identifiers without a separate HMAC/salt contract.

If a later reviewed mode wants dependency names, it must define a separate privacy contract, user
review UX, audit wording, and source-review packet.

## Policy Fixtures

Future policy fixtures should cover:

- read-capable principals receiving `allow` for in-scope manifest summary metadata;
- read-only/auditor principals receiving `allow` only if the default role/risk matrix permits this
  read metadata;
- unknown and disabled principals receiving deny-style results before execution;
- out-of-scope workspace roots and path traversal receiving deny-style results;
- dangerous/destructive risk rules remaining unaffected.

## Audit Fields

Runtime audit evidence, if implemented later, should include:

- tool name `project.manifest.summary`;
- manifest hash/version once a tool manifest exists;
- workspace ID and normalized root resource evidence;
- requested manifest kinds and effective manifest kinds;
- manifest count and truncation flag;
- file-content-included flag, expected `false`;
- dependency-names-included flag, expected `false`;
- package-script-values-included flag, expected `false`;
- registry-or-network-access-used flag, expected `false`;
- parse failure counts and safe failure reasons;
- policy version/hash, matched rules, and obligations;
- trusted principal ID/roles.

It must not audit raw manifest file contents, dependency names, script values, registry URLs,
repository URLs, package-manager output, environment values, or credentials.

## Resource Limits

Proposed limits for implementation planning:

- maximum manifest summaries returned: `20`;
- maximum manifest file size parsed: `131072` bytes;
- maximum total parsed bytes: `262144` bytes;
- maximum output bytes: `131072`;
- maximum executor runtime: `5` seconds;
- safe failure when parsing is ambiguous, oversized, unsupported, binary, or invalid UTF-8.

## Negative Transcripts

Negative transcript sketches should be added before implementation:

- parent traversal root denied;
- arbitrary manifest filename denied;
- recursive glob denied;
- `include_file_contents` denied;
- `include_script_values` denied;
- `include_dependency_names` denied;
- private registry URL field is not returned;
- oversized manifest fails safely;
- malformed JSON/TOML/XML fails safely without echoing content;
- symlinked manifest path denied.

## UI/review Evidence

If a review-console surface is added later, it should show:

- tool name and read-only category;
- selected workspace/root;
- manifest kinds summarized;
- output-policy flags showing raw contents, dependency names, and script values are not returned;
- safe parse failures and truncation status.

No execution controls or package-manager controls should be exposed.

## Accepted-Risk Impact

This candidate does not change the accepted local-preview risks by itself because it is proposal
only. A later implementation plan must re-evaluate metadata leakage risk for dependency names,
script names, script values, registry URLs, and manifest digests.

## No-New-Powers Analysis

This proposal keeps the same power class if implemented later: local read-only metadata mediation.
It must not become broad filesystem read, shell execution, package-manager execution, registry
access, arbitrary parser execution, plugin SDK work, browser automation, Docker/Kubernetes access,
or arbitrary network access.

## External/source Review Requirement

Implementation remains blocked until a later implementation-planning packet, focused source-review
bundle, internal xhigh review or external source review as appropriate, no-new-powers evidence,
tool-surface evidence, policy fixtures, negative transcripts, and an explicit implementation
decision are recorded.
