# Enterprise E2 Synthetic Scale Fixture

Status: deterministic test-only fixture generator. It is not a runtime importer, load-test result,
supported-scale claim, performance certification, human UAT, or production evidence.

The generator models one synthetic organization with:

| Collection | Count |
| --- | ---: |
| Workspaces | 8 |
| Missions | 96 |
| Nodes | 64 |
| Configuration cohorts | 8 |
| Version cohorts | 4 |
| Approvals | 48 |
| Evidence records | 144 |
| Attention items | 24 |

The canonical reference payload has SHA-256
`59222ee08c0c14f60e2dac1a63c491b2bb757de67f39e2e9e1203e2b162d9acd`.
The preparation contract recomputes and binds this digest so generator drift fails closed.

It deliberately preserves separate Gateway, Node-connectivity, runner-reported, and model-provider
truth. Model-provider and Node runner-health state remain `unknown`. Desired, acknowledged, stored,
enforced, stale, rejected, and rollback configuration states remain distinct. Approval decision and
application state remain separate. Evidence records declare their source and are authoritative only
when sourced from the Gateway.

The payload contains no human identity, email, token, cookie, credential, DSN, private key, raw
prompt, file content, or local path. Its identity-looking values are deterministic synthetic
references only.

## Validation

Run the in-memory deterministic check and focused tests:

```sh
make enterprise-e2-scale-fixture-check
```

Build a fixture only at a new absolute path whose non-symlink parent directory already exists:

```sh
uv run python scripts/enterprise_e2_scale_fixture.py build \
  --output /absolute/new/path/enterprise-e2-scale-fixture.json
uv run python scripts/enterprise_e2_scale_fixture.py verify \
  --fixture /absolute/new/path/enterprise-e2-scale-fixture.json
```

Publication is exclusive and refuses an existing path. The generator does not delete or overwrite
an earlier fixture.

## Intended later use

A separately authorized test lane may adapt this payload into API fixtures, Command Center mocks,
or browser-performance scenarios. Any adapter must preserve source meaning, remain synthetic,
avoid runtime import, and record its own candidate identity and acceptance limits.

Passing this fixture check proves deterministic shape, cross-reference integrity, redaction-safe
fields, closed authority, and semantic coverage only. It does not prove the UI can render these
counts within a target latency, that an operator can understand them, or that Ithildin supports
this deployment scale. It is not a supported-scale or performance claim.
