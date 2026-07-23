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

## Ambient Environment And Transport Isolation

The POC target runs its Python entry point with `uv --offline`. The harness starts the Gateway and
its focused adversarial tests through the already-running Python interpreter rather than asking a
package runner to resolve dependencies.

Child processes receive a closed environment assembled by the harness. Git provenance queries use
a system-path executable, disable system/global configuration, hooks, fsmonitor, the untracked
cache, optional locks, terminal prompts, and non-file protocols, and exclude ambient `GIT_*`
overrides. Clean-tree checks force discovery of all nonignored untracked files even when
repository-local status configuration requests otherwise. Gateway and focused-test children carry
only a fixed system `PATH`, proxy-denial and Python-isolation settings, and explicit `ITHILDIN_*`
settings. The Gateway:

- runs from the ignored evidence root, where repository `.env` input is absent;
- forces the `sqlite` storage backend and an empty PostgreSQL DSN;
- forces the YAML policy engine and an empty OPA URL;
- binds manifest, policy, principal, and workspace inputs to explicit repository paths;
- binds database, audit, keys, trusted-host staging, and disabled runtime-authorization paths to
  the selected ignored evidence root;
- disables telemetry and external HTTP allowlisting; and
- does not inherit ambient credential, proxy, storage, policy, workspace, or runtime variables.

All harness and Node HTTP requests use a proxy-free, redirect-denying opener pinned to the fixed
loopback API URL. The startup path defers `SIGINT` and `SIGTERM` while acquiring the process handle,
then deterministically terminates-and-waits or kills-and-waits on timeout, startup failure,
Python interruption, restart, and normal completion. Shutdown also defers those signals until the
child has been reaped, then restores and delivers the prior signal behavior.

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
compares the raw mirror bytes with the canonical full ordered SQLite payload sequence while holding
the SQLite write lock. Canonical framing is exactly one UTF-8 payload followed by exactly one LF byte
for every committed event. The same exact-byte check drives write preflight, diagnostics, exports,
Mission cockpit projections, governed mission bindings, and this POC checker. Any missing terminal
newline, CRLF substitution, blank line, orphaned append, partial record, appended byte, or edited
payload produces `recovery_required` and blocks new audit events. Ithildin does not silently repair or
discard evidence.

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
