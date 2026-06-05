# Read-Only Capability Source Review Template

Status: reusable source-review bundle guidance. This template does not add runtime behavior.

Future read-only local metadata tools should use this template before creating a focused review
bundle. The goal is to keep capability review packets consistent and reduce one-off packet scripts.

## Ten-Artifact Bundle Shape

Preferred focused handoff shape:

1. `00_<CAPABILITY>_SOURCE_REVIEW_INDEX.md`
2. `01_<CAPABILITY>_SOURCE_REVIEW_PROMPT.md`
3. `02_<CAPABILITY>_DISPATCH_PACKET.md`
4. `03_<CAPABILITY>_SOURCE_BUNDLE.md`
5. `04_<CAPABILITY>_TESTS_BUNDLE.md`
6. `05_<CAPABILITY>_CONTRACTS_BUNDLE.md`
7. `06_<CAPABILITY>_EVIDENCE.md`
8. `07_<CAPABILITY>_FOCUSED_TESTS.txt`
9. `08_<CAPABILITY>_INTAKE_COMMANDS.md`
10. `<capability>-source-review-artifact-hashes.json`

## Required Source Bundle Sections

- manifest and manifest-lock evidence;
- executor source;
- policy preview/runtime resource construction;
- governed call dispatch path;
- MCP adapter path;
- relevant UI/tool-list path if applicable;
- configuration and resource-limit wiring.

## Required Test Bundle Sections

- schema validation tests;
- executor happy-path tests;
- negative executor tests;
- policy fixture/parity tests;
- governed call tests;
- MCP list/call tests;
- audit evidence tests;
- release-readiness wiring tests.

## Required Contract Sections

- read-only local metadata contract;
- metadata privacy policy;
- capability-specific executor contract;
- implementation record;
- accepted-risk impact;
- no-new-powers evidence;
- source-review closure target rows.

## Prompt Requirements

The review prompt must ask the reviewer to decide whether the lane can close for the local-preview
runtime boundary. It must not ask for production/security-product approval or broader capability
approval.

Finding IDs should use a capability-specific namespace, for example:

- `EXT-GITREF-###` for `git.show.ref_summary`;
- `EXT-DEPMETA-###` for dependency metadata tools.

## Evidence Requirements

The bundle should include command output for:

- focused pytest group;
- capability-specific implementation gate;
- `make policy-parity`;
- `make tool-surface-invariant-gate`;
- `make no-new-powers-guardrail`;
- `make release-check` or a same-commit release-check transcript when practical.

Every generated artifact should be hashed. Bundles must exclude `.env`, private keys, runtime DBs,
audit JSONL, node modules, UI build output, and local secrets.
