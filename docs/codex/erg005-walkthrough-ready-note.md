# ERG-005 Walkthrough Ready Note

Status: walkthrough-ready operator checkpoint for the trusted artifact promotion lane.

This note records that the ERG-005 trusted artifact promotion operator demo packet and validation
checks are ready for a guided human walkthrough. It is a navigation note, not new runtime evidence
and not approval for broader host promotion.

## Ready For Walkthrough

The current walkthrough-ready packet is:

- `var/review-packets/v3/trusted-artifact-promotion-operator-demo/`
- `var/review-packets/v3/trusted-artifact-promotion-operator-demo/05_LIVE_WALKTHROUGH_PREP.md`

The current validation commands are:

```sh
make trusted-artifact-promotion-operator-demo-check
make trusted-artifact-promotion-operator-demo
make release-check
make review-candidate
```

At the recorded checkpoint, the walkthrough packet is intended to guide an operator through one
digest-bound artifact promotion story: sandbox/workspace artifact, SHA-256 evidence, approval-bound
promotion proposal, create-exclusive trusted-host staging placement, post-stage digest verification,
and audit/proposal/approval evidence.

## Not A Hard Development Stop

The walkthrough is a human-facing checkpoint, not a hard stop for every other development lane.
Bounded documentation, evidence packaging, review-packet cleanup, planning, and non-runtime
readiness work may continue while the operator walkthrough waits.

Work that should still pause for explicit review includes:

- new governed tool powers;
- broader trusted-host promotion behavior;
- direct host writes beyond the existing approved staging-only slice;
- Command Center runtime authority;
- sandbox/VM orchestration;
- SIEM adapters or compliance automation;
- public/security-product positioning;
- production identity, runtime Postgres, hosted telemetry, or remote MCP.

## Next Human Step

When ready, use `05_LIVE_WALKTHROUGH_PREP.md` as the front door for the guided walkthrough. The
walkthrough should confirm that the operator can follow the evidence trail and understand where
Ithildin is enforcing the boundary versus where Command Center is only displaying or reviewing
Ithildin-owned evidence.
