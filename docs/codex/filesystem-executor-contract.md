# Filesystem Executor Contract

This contract documents the local-preview filesystem and race assumptions for Ithildin as a v0.2
review candidate for the v0.1 local-preview runtime boundary. It covers `fs.list`, `fs.stat`,
`fs.read`, `fs.search`, `fs.patch.propose`, and `fs.patch.apply`.

It is not a sandbox contract. Ithildin mediates scoped tool access; it does not isolate the host OS,
protect against a compromised local admin, or prove every filesystem race impossible.

## Supported Local-Preview Platforms

The local-preview filesystem security claims are documented for:

- macOS on a local filesystem with normal symlink, hardlink, and atomic same-directory replacement
  semantics;
- Linux on a local filesystem with `O_NOFOLLOW`, normal symlink/hardlink behavior, and atomic
  same-directory replacement semantics.

Windows and WSL are not security-supported for workspace/race claims until separately reviewed.
They may run some development commands, but Ithildin does not claim workspace confinement or race
semantics on those profiles for local preview.

Run the local capability check before relying on the contract:

```sh
make filesystem-contract-check
uv run python scripts/filesystem_contract_check.py --json
```

The check uses only temporary files. It reports platform profile, Python version, `O_NOFOLLOW`
availability, symlink and hardlink capability, temporary-filesystem case sensitivity, and whether
the host matches this documented local-preview support profile.

## Guarantees

For supported local-preview platforms, the filesystem executors are designed and tested to provide
these application-level guarantees:

- tool paths are relative inputs only;
- absolute paths, `..` traversal, encoded traversal tokens, and non-normalized Unicode path inputs
  are rejected;
- resolved targets must remain under the configured workspace root;
- hidden paths, `.git` internals, `.env`, `secret`, and `secrets` path components are rejected;
- symlink targets are rejected, including representative swap cases between path validation and
  file open;
- hardlinked regular file targets are rejected to avoid ambiguous review and replacement semantics;
- read and patch text targets must be UTF-8 text, not binary content;
- reads and searches are bounded by configured size/result limits;
- patch proposals target exactly one existing text file and reject creates, deletes, renames,
  binary diffs, multi-file diffs, oversized diffs, and stale hunk context;
- patch apply rechecks the stored proposal, approval scope, current base hash, manifest evidence,
  policy evidence, schema hash, requesting principal, request hash, and expiry before writing;
- patch apply generates modified content in memory and writes through a same-directory temporary
  file followed by atomic replacement;
- patch apply is the only local-preview write path; there is no shell execution, broad write/delete
  tool, chmod, archive extraction, Docker socket access, Kubernetes tool, or browser automation.

## Race Handling

Ithildin uses conservative application-level controls:

- it resolves paths under a trusted workspace root before use;
- it rejects symlinks during path resolution and uses `O_NOFOLLOW` for file reads when available;
- it rejects hardlinked regular files before read/proposal/apply use;
- it re-reads and hashes the patch target immediately before patch apply;
- it rejects stale-base patch apply without modifying the file;
- it writes patch output through a temporary file in the target directory and replaces the target
  atomically.

These controls reduce practical local-preview race risk. They do not constitute a kernel sandbox or
a proof against every possible race across all filesystems, mount options, network filesystems, or
host compromise scenarios. Broader race proofs remain an external/source review item before
Ithildin expands write capabilities or claims stronger platform coverage.

## Non-Guarantees

This contract does not claim:

- OS-level sandboxing or containment;
- protection from a compromised host, malicious local admin, or malicious trusted workspace root;
- production identity, custody-grade audit, immutable storage, or external notarization;
- security-supported Windows, WSL, network-filesystem, or remote-mounted workspace behavior;
- support for non-UTF-8 text, binary patching, symlink patching, hardlink patching, mode changes,
  renames, deletes, creates, chmod, archive extraction, or broad filesystem writes.

## Review Pointers

- Implementation: `apps/api/src/ithildin_api/read_tools.py` and
  `apps/api/src/ithildin_api/patches.py`.
- Capability check: `scripts/filesystem_contract_check.py`.
- Regression coverage: `tests/test_read_tools.py`, `tests/test_patch_proposals.py`,
  `tests/test_governed_tool_calls.py`, and `tests/test_security_regressions.py`.
- Review status: [internal-source-review-pass-1.md](internal-source-review-pass-1.md) and
  [source-review-closure-matrix.md](source-review-closure-matrix.md).
