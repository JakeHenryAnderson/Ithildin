# Mission Command Control Plane POC Evidence Contract

Status: bounded `MCC-006` exact-candidate evidence contract. This document does not authorize a
runner bridge, production deployment, release, or UAT acceptance.

Current governed tool count: `24`.

## Purpose

The POC proves that one clean source candidate can admit a server-owned synthetic mission, deliver
it to an authenticated Ithildin Node, correlate one governed Agent Run, preserve Gateway and
runner-reported truth across a real Gateway restart, and fail closed under selected adversarial
conditions. The Node protocol remains the control and evidence boundary. No runner is launched and
no model provider is placed in Ithildin custody.

Generated evidence is written below
`var/mission-command-control-plane-poc-20260719/` and remains ignored runtime evidence. It is valid
only when the embedded commit equals the current clean checkout and the checker passes.

## Reproduction Sequence

Run the sequence on a clean exact candidate:

```sh
make agent-workflow-check
make mission-command-control-plane-focused-gates
make mission-command-control-plane-poc
make mission-command-control-plane-poc-check
make release-check
make review-candidate
```

`make review-candidate` depends on the MCC-006 POC checker so a stale, dirty, malformed, or
redaction-unsafe POC cannot be packaged as the exact candidate.

## Live Evidence

The harness starts a real loopback Gateway with isolated SQLite, JSONL, signing keys, and Node state;
enrolls and configures one synthetic Node; then records:

- response-loss admission followed by exact idempotent replay and drifted-replay denial;
- a single signed claim, runner-running report, and mission-bound governed read-only Agent Run;
- failed-closed governed access during a Gateway partition with no local fallback or queued retry;
- real Gateway restart using the same database and keys, nonce replay denial, report replay, admission
  replay, and a runner-succeeded report;
- a cancellation-versus-late-success race that preserves both the Gateway cancellation request and
  the later runner-reported outcome without claiming process stop;
- a revoked-Node late report that is authenticated, quarantined, and prevented from advancing the
  Gateway lifecycle.

The harness also runs the deterministic negative tests named in its evidence manifest. Those tests
cover stale heartbeat, configuration drift, below-minimum version, concurrent claim, retired-key
report, evidence failures, revocation, and the transition interruption boundaries required by
`MCC-006`.

## Audit Interruption And Recovery Boundary

SQLite is the committed audit index and JSONL is its append-only mirror. A process interruption after
JSONL append but before SQLite commit can leave an orphan mirror line. Every later audit write now
compares the full ordered committed SQLite payload sequence with JSONL while holding the SQLite write
lock. Any missing, orphaned, partial, or edited line produces `recovery_required` and blocks new audit
events. Mission cockpit projections and governed mission bindings also refuse that lifecycle. Ithildin
does not silently repair or discard evidence.

Focused tests distinguish interruption before audit insert, after JSONL append, after audit commit,
and before or after mission finalization. Tests and transcripts are evidence only; they do not perform
operator recovery or authorize a release.

## Redaction And File Controls

The checker requires the Node state and verified configuration files to remain mode `0600`. It scans
saved JSON, audit JSONL, and Gateway logs and fails if it finds the private Node key, the synthetic
runner-output sentinel, template payload fields, model output, prompt, or chain-of-thought keys. Saved
claim evidence is a safe projection and never contains the delivered template payload.

## Candidate Claim And Non-Claims

The only permitted claim is:

`mission_control_plane_candidate_ready_for_external_review`

Explicit non-claims are runner launch, runner process stop, model-inference custody, output
correctness, production deployment, release, UAT acceptance, and arbitrary host control. Independent
Sol xhigh source review must record no unresolved critical or high finding before `MCC-006` can be
closed. Sol Ultra is not authorized by this contract.
