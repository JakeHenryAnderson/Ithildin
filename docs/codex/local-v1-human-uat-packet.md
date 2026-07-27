# Ithildin Local v1.0 Human UAT Packet

Status: ready for human execution against one frozen candidate.

- Candidate commit: `ab4162d8f4b6d3f45a68f33316f4b765a45765db`
- Candidate tree: `25be9f049ca3ff3ccf6721100944e36baa0c3b05`
- Governed tool count: `24`
- Automated candidate gate: `PASS`
- Independent candidate review: `GO`, zero open findings
- Human UAT: `not_started`
- Release acceptance: `false`

This is the remaining Local v1.0 product gate. Automated evidence already covers the fixed
trust-boundary, recovery, real-agent, Node, mission, operations, UI, typing, and regression
contracts. Human UAT answers a different question: can a security-conscious power user understand,
operate, and trust the product's actual local workflow without the implementation agent explaining
away confusing behavior?

## Safety and stop lines

- Use only synthetic, non-sensitive data on a private local system.
- Do not use production credentials, a PostgreSQL DSN, hosted trust, or signing keys.
- Do not paste tokens, one-time enrollment codes, raw Node identities, run identifiers, or approval
  identifiers into the UAT record.
- Stop immediately if the tool count is not `24`, the worktree is not the exact candidate, a
  guardrail suggests weakening a check, cleanup would affect an unrecognized resource, or the UI
  presents runner/model claims as Gateway truth.
- A defect, confusing result, or aborted test is a valid UAT finding. Do not convert it into a pass
  by editing evidence or rerunning until it looks green.

## 1. Create an exact disposable checkout

From a clean Ithildin checkout, create a detached worktree so the evidence-record descendants are
not mistaken for the runtime candidate:

```sh
ITHILDIN_UAT_PARENT="$(mktemp -d "${TMPDIR:-/tmp}/ithildin-local-v1-uat.XXXXXX")"
ITHILDIN_UAT_ROOT="$ITHILDIN_UAT_PARENT/candidate"
git worktree add --detach "$ITHILDIN_UAT_ROOT" \
  ab4162d8f4b6d3f45a68f33316f4b765a45765db
cd "$ITHILDIN_UAT_ROOT"
git rev-parse HEAD
git status --short
```

Expected: the printed commit is the exact candidate above and `git status --short` is empty.

Use the prerequisites and trust ceiling in
`docs/codex/local-v1-golden-path.md`. Python 3.12, `uv`, Node/npm, and Docker Compose are required
for the normal local route. Ollama and the pinned Hermes model are required only if the operator
chooses to reproduce the optional historical Hermes container leg.

## 2. Preflight and initialize private local state

Follow **Create Operator-Owned Local State** in `docs/codex/local-v1-golden-path.md` exactly. Keep
the generated admin token only in the owner-readable ignored `.env`; do not record it.

Run:

```sh
make node-configuration-signing-status
# If and only if configured=false:
make node-configuration-keygen
make node-configuration-signing-ready
make local-v1-golden-path-check
make live-demo-preflight
make demo-readiness-summary
```

Human acceptance question: do the prerequisites, trusted-local boundary, 24-tool ceiling, optional
dependencies, and secret-handling instructions make sense without needing undocumented help?

## 3. Start and understand the normal product

Run:

```sh
make demo-seed
make compose-up
make compose-smoke
make demo-operator-walkthrough
make demo-flow
```

Open `http://127.0.0.1:5173`, sign in with the private token, and inspect the normal Command Center.

The operator should be able to:

1. identify that this is a local-preview governance gateway with exactly 24 tools;
2. find a mission or governed activity and understand its current Gateway-owned state;
3. distinguish an allowed action, a denied-before-execution action, and an approval lifecycle;
4. find the matching policy reason, approval, audit entry, and bounded evidence;
5. distinguish Gateway truth, Node connectivity, runner-reported state, and model-provider state;
6. use the interface with keyboard-only navigation and visible focus; and
7. understand what Ithildin does not govern, including activity an agent performs outside Ithildin.

Record confusion as a finding even if the underlying data is technically correct.

## 4. Exercise the optional authenticated Node path

Follow **Authenticated Node Onboarding Candidate And Synthetic Evidence** in
`docs/codex/local-v1-golden-path.md`.

In Command Center, issue one one-time enrollment code for an active synthetic workspace. In a
private, non-recorded terminal:

```sh
make node-service-image
make node-service-enroll
make node-service-status
```

Supply the one-time code only over stdin as documented. Assign signed desired configuration, then:

```sh
make node-service-up
make node-service-status
make node-service-stop
```

The operator should confirm that identity and workspace assignment come from the Gateway; Node
status does not masquerade as runner or provider health; configuration truth is not overstated; and
revocation/recovery instructions are understandable if enrollment becomes ambiguous.

## 5. Inspect mission, failure, recovery, and operations evidence

Use the retained, candidate-checked evidence and operator documents rather than rerunning closed
one-shot journeys:

- `docs/codex/local-v1-lv1-003-o4-attempt-021-disposition.md`
- `docs/codex/local-v1-lv1-004-disposition.md`
- `docs/codex/local-v1-lv1-006-operations.md`
- `docs/codex/local-v1-lv1-006-disposition.md`

In Command Center, verify that the constrained mission and its evidence remain comprehensible. The
operator should be able to explain, in their own words:

- why `runner_reported_succeeded` is not proof of model-provider success;
- how restart, replay, partition, revocation, stale configuration, and rollback fail closed;
- what the operator owns in `.env`, `var/`, `workspaces/`, Docker, backup, restore, and cleanup; and
- why the evidence export is bounded local evidence rather than custody-grade or whole-host proof.

Run the read-only exports:

```sh
make live-demo-status
make demo-evidence-packet
make workbench-evidence-packet
```

Confirm the exported packets are understandable and do not expose the secrets excluded above.

## 6. Stop and clean up

Run:

```sh
make compose-down
make live-demo-status
make node-service-stop
```

If the optional Hermes reproduction was deliberately run, also run `make hermes-poc-stop`.

Expected: normal services are stopped, unrecognized resources are untouched, and remaining ignored
state is clearly operator-owned. Do not delete ambiguous Node state until the documented
revoke/re-enroll procedure has been followed.

## 7. Record the result

Copy `docs/codex/local-v1-human-uat-record-template.md` outside the exact candidate checkout and
complete it without secrets or raw identifiers.

Use:

- `PASS` only if every required step completed and no release-blocking finding remains;
- `FAIL` if a defect, trust-boundary ambiguity, inaccessible interaction, unsafe cleanup, or
  incomprehensible core flow remains; or
- `ABORTED` if prerequisites or environment conditions prevented a meaningful test.

Human UAT and release acceptance are separate. A `PASS` permits preparation of the bound UAT
record; it does not by itself authorize release. Explicit human acceptance of the same frozen
candidate remains a later, separate record.
