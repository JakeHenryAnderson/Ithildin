# CI and Platform Planning

Task 144 records the v0.4 CI/platform posture without adding broad platform claims.

## Current Local-Preview Claims

- Security-supported filesystem/race claims are limited to macOS and Linux local filesystems that
  satisfy `make filesystem-contract-check`.
- Windows and WSL remain unsupported/untested for local-preview workspace/race security claims.
- Stdio-only local MCP remains the transport boundary.
- SQLite remains the only runtime storage backend.
- Docker/Compose is local-demo only and does not imply production deployment support.

## Current Gates

The local gate remains:

```sh
make release-check
make filesystem-contract-check
make review-candidate
```

`make release-check` includes manifest lock verification, release guardrails, evidence schema
validation, reviewer finding checks, review-run manifest checks, filesystem capability evidence,
manifest-change review, determinism checks, adversarial corpus validation, resource-limit sanity,
evidence contract validation, policy fixtures, policy parity, pytest, ruff, mypy, docs-site build,
and UI build.

## Future CI Shape

A future CI workflow should be introduced only as evidence automation. It should:

- run `make release-check` on Linux;
- run `make filesystem-contract-check` and report platform support status;
- avoid claiming Windows/WSL security support until separately reviewed;
- avoid running Docker socket, Kubernetes, shell-tool, browser-automation, or remote-MCP tests;
- avoid uploading `.env`, private keys, runtime SQLite databases, audit JSONL files, generated
  review bundles, or seeded mutable workspaces;
- preserve local-preview warning labels in release artifacts.

CI passing would mean the repository gates pass on that runner. It would not prove production security.
It also would not prove OS sandboxing, custody-grade audit, hosted MCP readiness, or enterprise
identity.

## External Review Gate

Before using CI status for public/security-product claims, an external/source reviewer should inspect
the CI workflow, runner assumptions, filesystem-support evidence, secret-handling behavior, and
artifact upload boundaries.
