# Enterprise Response Intake Drill

Status: fixture drill for enterprise response-intake paths.

Run:

```sh
make enterprise-response-intake-drill
```

This drill proves the enterprise response path is mechanically ready before a real external
response arrives. It aggregates the lane-specific response dry runs for the existing enterprise
review lanes and adds explicit checks for `ERG-010 public/security-product positioning`, which has
a normalizer area and fail-closed closure gate but no separate dry-run target.

The drill may temporarily write fixture normalized responses under ignored `var/review-runs/`
paths, then restores the original state. These fixture writes use a local advisory lock so parallel
operator/readiness commands do not observe each other's temporary normalized-response files as real
review evidence. It does not record external review, does not mutate committed findings, does not close any enterprise lane, does not approve runtime behavior, and does not approve Mission Control runtime behavior, live VM/container inspection, local model invocation, sandbox orchestration, trusted-host promotion, SIEM adapters, compliance automation, public/security-product positioning, or new governed tool powers.

## Covered Lanes

- `ERG-003`: static sandbox/VM preflight
- `ERG-002`: Mission Control display/import planning
- `ERG-005`: trusted-host promotion design review
- `ERG-006/ERG-007`: production identity and storage architecture
- `ERG-008`: SIEM export adapter architecture
- `ERG-009`: compliance mapping support architecture
- `ERG-004`: live sandbox/VM worker POC decision
- `ERG-010`: public/security-product positioning claim review

## What It Proves

- the response status board is clean before fixture writes;
- every enterprise status-board lane has normalizer coverage;
- the all-lane response inbox can be generated;
- lane-specific dry runs preserve ignored response state;
- packet-only, bad-hash, critical/high, and direct-closure fixture cases remain rejected where
  those lanes define dry runs;
- `ERG-010` accepts explicit no-finding fixture normalization, rejects wrong namespaces, rejects
  missing finding/no-finding statements, rejects secret markers, and blocks closure for
  critical/high findings.

## What It Does Not Prove

This drill does not prove that an external reviewer has approved anything. It does not prove that a
real future response is favorable. It does not replace lane-specific closure gates. It does not
approve implementation planning, runtime behavior, public/security-product positioning,
production/security/compliance positioning, or any new power class.

After a real response arrives, use the generated
[Enterprise Response Inbox](enterprise-response-inbox.md), run the exact normalization command for
that lane, and then run the lane-specific dry-run and closure gate.
