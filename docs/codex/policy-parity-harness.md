# Policy Preview/Runtime Parity Harness

Task 096 added a repeatable local harness for checking that policy preview decisions match the
policy decision evidence emitted by the governed runtime path. Task 133 extends the same harness to
cover pre-policy denial parity for invalid arguments and role/risk visibility denials.

The harness is intentionally narrow:

- it uses committed tool manifests, the default YAML policy, and the local principal registry;
- it calls `PolicyPreviewService.preview` and `GovernedToolCallService.call_tool` for the same
  fixture case;
- it reads the resulting `policy.evaluated` audit event from a temporary SQLite/JSONL audit store;
- it compares the preview `decision_evidence` fields against runtime audit metadata;
- for pre-policy denials, it verifies matching denial decisions/status while requiring that preview
  does not claim full policy-decision evidence;
- it uses a fixture HTTP opener for network cases so no external internet request is made.

Run:

```sh
make policy-parity
```

or:

```sh
uv run python scripts/policy_parity.py --json
```

The default fixtures live in `policies/tests/parity.yaml` and cover in-scope read allow,
write approval requirement, write-proposal allow, allowlisted network allow, out-of-scope network
denial, schema-invalid argument denial, and read-only principal network denial.

## Boundaries

The parity harness is an assurance check, not a new runtime endpoint or tool power. It does not
mutate configured policy, create persistent runtime approvals, call external network destinations,
or close external source-review rows. OPA parity remains a separate Task 097 decision point.
