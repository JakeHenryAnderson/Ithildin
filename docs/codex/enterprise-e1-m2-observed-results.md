# Enterprise E1-M2 Policy and Node-Configuration Observed Results

Status: `E1-O2` and `E1-M2` complete as a bounded engineering checkpoint. This is not release
acceptance, production enforcement, fleet UAT, or proof of non-bypass on a general-purpose host.

## Exact checkpoint

- Source commit: `e15c524804f6b7d16704db3f4124eed2bda89a01`
- Command: `make enterprise-e1-configuration-check`
- Result: `20 passed`; Ruff and strict mypy passed.
- Governed tool count: `24`.
- State contract:
  [`enterprise-e1-configuration-state-contract.json`](enterprise-e1-configuration-state-contract.json)

The focused checkpoint exercised the existing authenticated API flows for administrator
assignment, inventory/history observation, and compare-and-set rollback; Node-signed retrieval,
storage acknowledgment, and trust-transition acknowledgment; and request-scoped Node-governed
read admission. It also exercised signature/target/time/manifest rejection, desired-versus-stored
drift, private atomic storage semantics, rollback as a fresh monotonic generation, trust-transition
expiry, and read-only workspace/profile binding.

## State disposition

The E1 contract now keeps seven operator-visible meanings distinct:

- `desired`: the Gateway-selected evidence-complete signed generation;
- `acknowledged`: Node-attested storage of that exact generation and digest;
- `stored`: crash-safe private verified storage, explicitly `stored_not_enforced`;
- `enforced`: one specific request passed current Gateway admission checks;
- `stale`: one or more desired, acknowledged, observed, time, policy, manifest, or version bindings
  is not current;
- `rejected`: verification or admission failed without accepted storage acknowledgment or governed
  action; and
- `rollback`: an earlier payload was issued as a new signed monotonic generation.

Configuration-signing trust rotation remains separately staged, Node-acknowledged, activated only
after complete evidence, and fail-closed on expiry. The Node cannot self-select configuration,
broaden its read-only profile, or perform governed actions offline.

## Claim boundary

`stored_not_enforced` remains literal. The checkpoint proves policy and manifest binding in the
signed bundle and request-scoped Gateway admission; it does not prove that a runner, model
provider, or whole host enforced the configuration. No new MCP tool, host authority, production
identity, remote transport claim, or UAT completion was added. The next ordered checkpoint is
`E1-M3`.
