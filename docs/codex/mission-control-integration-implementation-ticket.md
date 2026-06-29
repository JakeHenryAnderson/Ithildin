# Mission Control Integration Implementation Ticket

Status: planning-only cross-repo implementation ticket for a future Mission Control display/importer
slice.

This ticket translates Ithildin's current Mission Control display proposal, importer plan, schema
contract, negative fixtures, and generated review packet into a narrow Mission Control repository
task. It is intended to be pasted into the Mission Control project when that project is ready to
implement a display-only importer.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Runtime importer implementation remains blocked on the Ithildin side. This ticket does not add
runtime behavior to Ithildin, and it does not approve Mission Control execution, policy, approval,
audit, local-model, VM/container, sandbox, host-promotion, SIEM, identity, storage, telemetry, or
compliance authority.

## Objective

Implement a local, operator-selected file/import display surface in Mission Control for
Ithildin-generated evidence handoff packets.

The first Mission Control implementation should let an operator select an Ithildin packet directory
or handoff JSON file, validate the packet, and render safe metadata only: labels, short IDs,
warning chips, digest status, relative evidence links, and import state.

## Authoritative Ithildin Inputs

Use these Ithildin artifacts as the implementation source of truth:

- `docs/codex/mission-control-display-integration-proposal.md`
- `docs/codex/mission-control-display-importer-plan.md`
- `docs/codex/mission-control-side-handoff-plan.md`
- `docs/codex/mission-control-handoff-schema-contract.md`
- `docs/codex/mission-control-handoff-negative-fixtures.md`
- `docs/codex/mission-control-handoff-fixture-pack.md`
- `docs/codex/mission-control-importer-acceptance-matrix.md`
- `docs/codex/mission-control-handoff-reference-validator.md`
- `docs/codex/hello-world-mission-control-handoff.md`
- `docs/codex/enterprise-status-export.md`
- `docs/codex/mission-control-enterprise-status-import-contract.md`
- `docs/codex/mission-control-enterprise-status-fixtures.md`
- `docs/codex/mission-control-enterprise-status-acceptance-matrix.md`
- `docs/codex/mission-control-enterprise-status-reference-validator.md`
- `var/review-packets/v3/mission-control-display/`
- `var/review-packets/v3/hello-world-mission-control-handoff/mission-control-handoff.json`
- `var/review-packets/v3/mission-control-handoff-fixtures/`
- `var/review-packets/v3/mission-control-enterprise-status-fixtures/`

Use these observed Mission Control-side artifacts when present:

- `docs/ithildin-integration-roadmap.md`
- `README.md` integration boundary section
- `scripts/check-ithildin-integration-docs.mjs`
- `apps/desktop/src/App.tsx`
- `apps/desktop/src/App.test.ts`

The observed Mission Control repository path during this planning pass was
`/Users/jake/Projects/Mission-Control`. That local path is evidence for the current workstation, not
a portable release requirement.

## Mission Control Implementation Slices

Complete the future Mission Control work in this order:

1. **Docs/status alignment**: update Mission Control docs so the integration is described as
   display/import only, with Ithildin remaining the governed gateway.
2. **Packet import parser**: accept only operator-selected local packet directories or handoff JSON
   files; reject remote URLs, callbacks, commands, globs, and hidden runtime instructions.
3. **Packet validation**: validate schema version, `metadata_only` status, authority flags,
   display allowlist, hidden-field denylist, packet-relative attachments, warning chips, artifact
   hashes, and freshness fields.
4. **Display surface**: render safe labels, warning chips, short hashes, import status, and relative
   evidence links without raw contents.
   For enterprise status exports, render `next_action` and `action_commands` as copyable
   display-only text. Do not render them as executable buttons, task runners, callbacks, polling
   controls, or shell commands.
5. **Mission-local linkage**: store only Mission Control-local display metadata and optional
   mission/evidence references.
6. **Negative fixtures**: add tests for stale packets, hash mismatch, unsafe paths, authority
   overclaims, and raw-content leakage.
7. **Source-review handoff**: generate a Mission Control-side review packet that includes source,
   fixtures, command output, and artifact hashes for the display-only importer.

## Allowed Mission Control Files

The future Mission Control task may touch only the smallest necessary subset of:

- `docs/ithildin-integration-roadmap.md`
- `README.md`
- `scripts/check-ithildin-integration-docs.mjs`
- `apps/desktop/src/App.tsx`
- `apps/desktop/src/App.test.ts`
- Mission Control-local parser/test helpers, if needed for a display-only importer
- Mission Control-local mission metadata storage, if needed to persist display/import state

Any need to edit supervisor policy, execution, approval, audit, worker lifecycle, VM/container,
local-model, secrets, deployment, or remote-integration surfaces stops the task.

## Validation Commands

Run from the Ithildin repository before handing off:

```sh
make mission-control-integration-implementation-ticket-check
make mission-control-display-review-packet
make hello-world-mission-control-handoff-check
make mission-control-handoff-fixture-pack-check
make mission-control-importer-acceptance-matrix-check
make mission-control-handoff-reference-validator
make mission-control-enterprise-status-fixtures-check
make mission-control-enterprise-status-acceptance-matrix-check
make mission-control-enterprise-status-reference-validator
```

Run from the Mission Control repository after future implementation, adjusted only for the current
Mission Control package scripts:

```sh
node scripts/check-ithildin-integration-docs.mjs
npm test
```

If Mission Control adds a dedicated importer check, include it in the Mission Control source-review
handoff packet before requesting review.

## Required Mission Control Tests

The future Mission Control implementation should include tests for:

- valid metadata-only handoff import;
- valid fixture accepted as metadata-only display evidence;
- valid enterprise status fixture accepted as display-only status evidence;
- all `MC-HANDOFF-NEG-001` through `MC-HANDOFF-NEG-014` fixtures rejected with safe reason labels;
- all `MC-STATUS-NEG-001` through `MC-STATUS-NEG-012` fixtures rejected with safe reason labels;
- `MC-STATUS-NEG-011` unsafe action command rejection with `unsupported_action_command`;
- `MC-STATUS-NEG-012` unsafe handoff artifact rejection with `unsafe_handoff_artifact`;
- unsupported schema rejection;
- non-`metadata_only` status rejection;
- missing display allowlist rejection;
- missing hidden-field denylist rejection;
- missing warning chips rejection;
- absolute attachment path rejection;
- parent-traversal attachment path rejection;
- URL attachment rejection;
- hash mismatch warning or rejection;
- stale packet warning;
- Mission Control execution-authority overclaim rejection;
- Mission Control policy/approval/audit-authority overclaim rejection;
- local-model, VM/container, sandbox, shell, host-promotion, SIEM, identity, and compliance
  overclaim rejection;
- raw prompt, file content, diff, response-body, token, private-key, environment-value, dependency,
  package-script, raw host-path, or sandbox-internal display rejection.

## Required Mission Control Evidence

The future Mission Control handoff should produce:

- implementation summary;
- source-review packet;
- command transcript for the integration docs check;
- command transcript for the importer tests;
- valid import transcript;
- stale packet transcript;
- hash mismatch transcript;
- unsafe attachment transcript;
- authority overclaim transcript;
- content-leak rejection transcript;
- fixture-pack import transcript for `mission-control-handoff-fixtures/`;
- enterprise-status fixture import transcript for `mission-control-enterprise-status-fixtures/`;
- enterprise-status `action_commands` rendering transcript showing copyable text only, no execute
  buttons or command runners;
- UI screenshot or test evidence showing warning chips remain visible;
- artifact hashes for generated review files;
- no-new-authority evidence confirming Mission Control remains display/import only.

## Explicit Non-Goals

This ticket does not approve:

- Mission Control execution authority;
- Mission Control policy authority;
- Mission Control approval authority;
- Mission Control audit authority;
- Mission Control callbacks into Ithildin;
- Mission Control polling or mutating Ithildin APIs;
- Mission Control-created approvals;
- Mission Control replay, repair, or promotion actions;
- Mission Control execution of imported `action_commands`;
- local model invocation;
- VM/container lifecycle control;
- sandbox orchestration;
- trusted-host promotion;
- shell execution;
- direct filesystem mutation by Mission Control outside its own local display metadata;
- remote MCP;
- SIEM adapters;
- production IAM;
- runtime Postgres;
- hosted telemetry;
- compliance automation;
- public/security-product positioning.

## Stop Conditions

Stop the Mission Control implementation task and return for design review if it requires:

- executing, approving, replaying, repairing, promoting, or rolling back actions;
- reading files outside the operator-selected packet directory;
- accepting remote packet sources;
- calling Ithildin APIs or MCP servers;
- changing Ithildin policy, approval, audit, execution, sandbox, or promotion state;
- rendering raw prompts, file contents, diffs, response bodies, tokens, keys, environment values,
  dependency names, package scripts, raw host paths, or sandbox internals;
- treating Mission Control as a trusted host, sandbox controller, SIEM adapter, compliance engine,
  identity provider, or source of gateway truth.

## Done When

The future Mission Control slice is done when:

- display/import behavior is covered by Mission Control tests;
- unsafe handoff fixtures are rejected or warning-state-only;
- no authority flags are accepted as true;
- warning chips are visible in the operator UI;
- generated review artifacts include source, tests, command output, and hashes;
- Ithildin review artifacts still show tool count `24` and no new Ithildin runtime powers.

## Ithildin Validation

Run from the Ithildin repository:

```sh
make mission-control-integration-implementation-ticket-check
```
