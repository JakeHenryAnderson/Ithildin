# Metadata Privacy Policy

Status: capability-expansion preparation. This policy does not add runtime behavior.

Repository, package, dependency, and project metadata can leak sensitive information even when no
file contents are returned. This policy defines the default privacy posture for future read-only
local metadata capabilities.

## Sensitive By Default

Treat these values as sensitive by default:

- branch names;
- tag names;
- commit author/committer names and emails;
- changed-file paths;
- dependency names when private package scopes are possible;
- package registry URLs;
- remote URLs;
- project names;
- issue IDs, incident IDs, customer names, or unreleased product names embedded in metadata;
- repository-controlled free text such as commit bodies, tag messages, package descriptions, and
  script names.

## Default Output Rule

Future metadata tools should default to name-free or redacted metadata when names are not essential
to the workflow. If names are necessary, the proposal must justify why, cap and redact output, label
the data as untrusted metadata, and include negative tests for leakage.

## Stable Identifier Rule

Stable hashes are not anonymity guarantees. Raw `sha256(value)` digests of sensitive names are not a
privacy boundary because common values can be guessed and correlated.

If a future capability requires cross-response correlation, it must define one of:

- response-local opaque IDs, preferred when correlation is needed only within a single response;
- domain-separated keyed HMACs with explicit key scope and rotation;
- repository/workspace-scoped salted digests with explicit salt scope and rotation.

The proposal must define:

- canonical input string;
- digest/HMAC algorithm and version;
- scope of key or salt;
- rotation behavior;
- audit wording;
- whether identifiers can correlate across workspaces, sessions, exports, or releases.

## Repository-Controlled Text

Repository-controlled text must be treated as untrusted. Future tools must cap, redact, and label
such text. They must deny or sanitize:

- invalid UTF-8;
- control characters;
- terminal-control sequences;
- path traversal-like text where paths are involved;
- secret-like strings;
- oversized fields;
- malformed structured records.

## Audit Rule

Audit records must favor summaries over raw metadata. Safe audit fields include:

- selector kind;
- count;
- truncation status;
- redaction mode;
- whether names were returned;
- whether stable identifiers were returned;
- safe denial or failure reason.

Audit records must not include raw sensitive metadata unless a future capability has explicit
reviewed approval for that exact field and the audit contract explains why it is necessary.

## UI Rule

The review console must label repository/project metadata as untrusted if displayed. It should show
redaction and truncation status instead of encouraging reviewers to treat metadata as authoritative
or safe text.
