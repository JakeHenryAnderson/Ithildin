# Ithildin Local v1.0 Golden Path

Status: `LV1-001` operator walkthrough, implementation candidate.

This is the authoritative executable walkthrough for assembling Ithildin's existing Local-v1
components. It is intentionally a **two-leg path**:

- **Leg A — real agent compatibility:** the normal local Gateway and Command Center plus an
  operator-managed Hermes agent using Ithildin's local stdio MCP surface.
- **Leg B — synthetic Node and Mission Command evidence:** authenticated Node enrollment, signed
  configuration, governed access, and Mission Command recovery evidence produced by isolated POCs.

The legs are not an integrated runner path. This walkthrough does not claim or demonstrate a real
Hermes-through-Node mission. `MCC-007` remains deferred to the separate `LV1-003` capability
decision; nothing here authorizes its implementation.

## Prerequisites And Trust Ceiling

Run commands from the repository root on a private local system. Install Python 3.12, `uv`, and
Node/npm. Docker Compose is required only for the normal API/UI path and the optional real Hermes
reproduction. A local Ollama service with the pinned model named in
[the Hermes deployment fixture](../../deploy/hermes-poc/README.md) is required only when deliberately
reproducing that real-agent leg.

Ithildin governs activity that reaches its bounded 24-tool surface. It does not sandbox the host,
control arbitrary processes, prevent an agent from using capabilities outside Ithildin, or provide
shell, Docker-socket, Kubernetes, browser, arbitrary-network, or broad-filesystem authority.
Gateway policy, approval, execution, audit, and evidence remain authoritative.

Use only synthetic, non-sensitive content. This path uses SQLite and local ignored state; it does
not require or authorize a DSN, PostgreSQL, production credentials, hosted services, or production
signing keys.

## 1. Create Operator-Owned Local State

Create the ignored `.env` file with owner-only permissions:

```sh
if [ -e .env ]; then
  chmod 600 .env
else
  install -m 600 .env.example .env
fi
make admin-token-generate
```

This conditional never copies over an existing `.env`; it only restricts that file to owner access.
For a missing `.env`, it installs the template directly with mode `0600`.

Paste the generated `ITHILDIN_ADMIN_TOKEN` assignment into `.env`, replacing the sample value, and
set `ITHILDIN_ALLOW_DEV_ADMIN_TOKEN=false`. Run the generator only in a private, non-captured
terminal: it prints the token but does not write it. Do not run it in a recorded/shared terminal,
paste the value into this document or a transcript, place it in an issue, or commit it.

Keep the template's SQLite, audit, and key paths under ignored `var/`. Confirm that
`ITHILDIN_POSTGRES_DSN` remains empty. Do not reuse production data or keys. Before continuing:

```sh
git status --short
make node-configuration-signing-status
# If and only if configured=false:
make node-configuration-keygen
make node-configuration-signing-ready
make local-v1-golden-path-check
make live-demo-preflight
make demo-readiness-summary
```

Expected: the source check reports the golden path valid; preflight identifies the 24-tool
local-preview boundary, confirms the existing `.env` has no group/world permission bits, and reports
Compose availability without starting services. The Node configuration signer is operator-created
under ignored `var/keys/` before API startup and its private key remains mode `0600`. On Linux,
align `ITHILDIN_CONTAINER_UID` and `ITHILDIN_CONTAINER_GID` with the operator UID/GID before
startup so the unprivileged API can read it. `.env` must not appear in `git status --short`.

**Stop** if `.env` is tracked, the tool count is not 24, the manifest/policy inputs are unexpected,
or preflight reports a required local dependency missing. Do not compensate by weakening a
guardrail.

## 2. Leg A — Normal Gateway And Command Center

Seed only the ignored demo workspace, then start and verify the normal local stack:

```sh
make demo-seed
make compose-up
make compose-smoke
make demo-operator-walkthrough
make demo-flow
```

Open `http://127.0.0.1:5173` and authenticate with the token held in `.env`. The API remains on
`http://127.0.0.1:8000`.

Bind every observation to the command or evidence source that establishes it:

| Observation | Actual source | Boundary |
| --- | --- | --- |
| System Trust says local preview and reports 24 tools. | Normal Command Center after `make compose-smoke`. | UI projection of Gateway state. |
| An allowed read completed and a redaction check passed. | `make demo-flow` and `DEMO_FLOW_RESULT.md`. | Governed local demo activity. |
| `fs.list` received an allow policy preview; `http.fetch` received a safe allow-or-deny preview. | `make demo-flow` console execution. | A preview is not an executed denied request. |
| One patch proposal created an approval, the script approved it, and the bound patch executed. | `make demo-flow` and `DEMO_FLOW_RESULT.md`. | The scripted lifecycle is automatically completed; no approval is left pending for the operator. |
| The selected run exposes bounded, redacted evidence and audit status. | Command Center and the generated workbench packet. | Evidence covers recorded Ithildin activity only. |

`make demo-flow` does not execute a denied request and does not pause for an operator to approve a
pending action. Denial-before-execution, durable pending approval across a Hermes container exit,
exact approval, single execution, and replay denial belong to the separately recorded historical
Hermes baseline below.

Run the read-only status and bounded export commands:

```sh
make live-demo-status
make demo-evidence-packet
make workbench-evidence-packet
```

Expected ignored outputs include:

- `var/review-packets/v3/live-demo/LIVE_DEMO_INDEX.md`
- `var/review-packets/v3/live-demo/LIVE_DEMO_EVIDENCE_SUMMARY.md`
- `var/review-packets/v3/operator-workbench/WORKBENCH_DEMO_INDEX.md`
- `var/review-packets/v3/operator-workbench/DEMO_FLOW_RESULT.md`

These exports cover Ithildin-mediated activity only. They are not custody-grade, externally
notarized, or evidence of activity outside Ithildin.

### Real Hermes MCP compatibility leg

The historical accepted real-agent baseline is described in
[Governed External Agent POC: Observed Track A Results](governed-external-agent-hermes-poc-observed-results.md).
Validate retained ignored local evidence without launching Hermes:

```sh
make hermes-governance-poc-plan-check
make local-v1-hermes-evidence-check
```

The Hermes checker validates the current contents retained under its ignored evidence path. It does
not embed or verify a source-candidate commit, so a passing check does not establish
current-candidate freshness or provenance. The historical observed-results document is the baseline
claim. If the ignored evidence is absent, malformed, or no longer accepted, record the check as
unavailable or failed as applicable. Do not silently regenerate it or relabel it as current-candidate
evidence.

Reproduction is a separate, deliberate operator action. It starts an operator-managed Hermes
container and requires the pinned local Ollama dependency:

```sh
make hermes-poc-image
make hermes-poc-config-check
make hermes-poc-run
make local-v1-hermes-evidence-check
make hermes-poc-stop
```

Always run `make hermes-poc-stop` after `make hermes-poc-run`, including after a failed check.
Hermes is operator-started and unmanaged by Ithildin. Its model prose is not authoritative evidence,
and the shared fixture filesystem is not a non-bypass boundary.

## 3. Leg B — Authenticated Node Onboarding Candidate And Synthetic Evidence

The normal local stack now has an explicit optional onboarding candidate. This sequence is
implemented but is **not yet recorded as an observed integrated journey** and therefore does not
close `LV1-002` or `O3`.

With the signer initialized before the API started, open **Nodes** in Command Center. Enter a
bounded display name, explicitly select an active workspace, and issue one short-lived code.
Command Center keeps the raw code only in mounted component memory; it does not persist it, copy it,
log it, export it, put it in a URL, or generate a command containing it. Dismissal, replacement,
navigation away from Nodes, sign-out, dashboard refresh, or page reload clears the displayed value;
delayed responses are invalidated when the component loses ownership.

Build the optional image, then use the fixed stdin-only target in a private, non-recorded terminal:

```sh
make node-service-image
make node-service-enroll
make node-service-status
```

Paste exactly one nonempty code line with no leading or trailing whitespace into
`make node-service-enroll`, press Return, then send EOF. Never place the code in an environment
variable, command argument, Make variable, note, or transcript. Before reading stdin, the CLI
atomically reserves a mode-`0600` regular state file and holds that exact inode through enrollment.
An existing file, directory, symlink, or competing reservation therefore fails before the secret is
read or the Gateway is contacted; do not overwrite or delete state to force re-enrollment.

Immediately before possible Gateway contact, that reservation becomes a secret-free
`recovery_required` marker. If the request may have reached the Gateway but its response is lost, or
if final state persistence fails, the marker remains and a blind retry is blocked. Run
`make node-service-status`, inspect the Gateway Node inventory, and revoke any identity that may
correspond to the ambiguous attempt. Only after revocation may the operator explicitly remove or
recreate the local Node state volume and issue a new code. Ithildin automatically removes only its
own still-empty reservation after a known pre-contact failure.

In Command Center, assign a signed desired configuration to the new Gateway-derived Node identity.
Then start and later stop only the optional Node service:

```sh
make node-service-up
make node-service-status
make node-service-stop
```

The optional profile has no environment, host mount, published port, Docker socket, Linux
capability, runner lifecycle, self-update, or arbitrary host control. The status command is a safe
client summary; it is not runner or model-provider health. This candidate sequence must be observed
and recorded separately before `LV1-002` or `O3` can complete.

The retained-evidence checks below validate ignored local evidence from already-recorded isolated
POCs; those checks do not start the optional Compose `ithildin-node` profile. That profile cannot
safely self-enroll: never place a one-time enrollment code, Node private key, or API admin token
into the optional `ithildin-node` service's environment variables or command arguments. The normal
`ithildin-api` service is different: Compose supplies its required API admin token from the
operator-owned `.env` file.

Run:

```sh
make track-b-node-evidence-check
make track-b-node-configuration-evidence-check
make track-b-node-governed-access-evidence-check
make track-b-node-configuration-trust-rotation-evidence-check
make track-b-node-version-posture-evidence-check
make track-b-node-identity-key-rotation-evidence-check
make track-b-node-service-lifecycle-evidence-check
make track-b-node-release-artifact-evidence-check
```

Expected: the legacy Node checkers accept the current retained redacted contents showing one-time
enrollment, Gateway-derived agent
identity and workspace, signed configuration, governed read access, network and cross-workspace
denials, restart continuity, durable replay rejection, partition failure without local fallback,
revocation/rotation/version posture, and bounded service/release evidence.

Most legacy Node content checkers do not bind the retained contents to the current source candidate
and do not establish current-candidate freshness or provenance. The Node release-artifact checker
is a partial exception: it compares the recorded current and rollback artifact `source_commit`
values with current `HEAD` and requires their recorded `source_dirty` values to be false. It does
not require the current worktree to be clean, so it is not exact-current-clean-candidate evidence.
The historical observed-results documents remain the baseline claims. These are synthetic sidecar
POCs, not proof that Hermes enforced configuration, not a managed fleet, and not a real agent
mission.

## 4. Leg B — Synthetic Mission Command Recovery Evidence

Validate the bounded plan and retained MCC-006 POC evidence:

```sh
make mission-command-control-plane-plan-check
make mission-command-control-plane-poc-check
```

The MCC-006 checker is uniquely stronger than the legacy Hermes and Node content checkers and the
partially bound Node release-artifact checker: it requires the embedded candidate commit to equal
the current commit and requires both the recorded candidate and current worktree to be clean. A pass
therefore binds the retained evidence to the exact current clean source candidate.

The Mission Command POC is isolated from the normal stack: reproduction uses a dedicated Gateway
on loopback port `8021` with separate state and cleans up its own child process. Its synthetic
mission is not visible in the normal Command Center started in Leg A. A deliberate reproduction,
when exact-candidate evidence is needed later, is:

```sh
make mission-command-control-plane-poc
make mission-command-control-plane-poc-check
```

Expected evidence preserves admission/replay behavior, signed claim and reports, governed read
correlation, partition failure, Gateway restart, cancellation-versus-late-success truth, and
revoked-Node quarantine. The POC launches no runner and places no model provider in Ithildin
custody.

## 5. Read The Four Truth Sources Separately

For every record inspected in either leg, use these labels:

| Truth source | What it can establish | What it cannot establish |
| --- | --- | --- |
| **Gateway truth** | Policy decision, approval state, governed execution result, accepted mission transition, audit and evidence records. | Runner health, model inference, or activity outside Ithildin. |
| **Node connectivity** | Signed enrollment/configuration/heartbeat/request observations accepted by the Gateway. | Runner execution, provider success, or whole-host enforcement. |
| **Runner-reported state** | A bounded report that a runner transition was attempted or observed. | Gateway admission, process stop, output correctness, or provider truth. |
| **Model-provider state** | Facts established by the configured provider's own surface. | Gateway policy, Node connectivity, or governed execution evidence. |

Never translate `cancel_requested` into process stopped, a Node heartbeat into runner health, a
runner success report into verified model output, or model prose into an Ithildin audit fact.

## 6. Stop And Clean Up

Stop the normal stack even if an earlier step failed:

```sh
make compose-down
make live-demo-status
git status --short
```

If the optional Hermes reproduction ran, confirm `make hermes-poc-stop` was also run. Generated
SQLite databases, audit logs, keys, Node state, workspaces, and packets remain ignored local
artifacts. Do not commit them. Deleting retained evidence is an explicit operator choice and is not
part of this walkthrough.

Expected: Compose services are stopped; the status report no longer treats the API/UI as reachable;
source status shows only intentional source edits. Stop and record a finding if services cannot be
stopped, a secret appears in source status or an export, audit verification requires recovery, or a
checker reports malformed/stale evidence.

## What This Path Proves

- A security-conscious power user has one ordered start/exercise/observe/export/stop route.
- The normal local Gateway and Command Center expose an allowed read, policy previews, an
  automatically completed approval lifecycle, audit, and bounded evidence behavior through the
  existing 24-tool surface.
- The historical baseline records that a real operator-managed Hermes agent separately produced
  accepted governed-MCP denial, durable-approval, execution, and replay evidence.
- Synthetic Node and Mission Command POCs separately demonstrate their recorded authentication,
  identity, governed-access, restart/replay/partition, and truth-separation claims.

## What This Path Does Not Prove

- It does not prove a real Hermes-through-Node mission or close Local-v1 outcome `O4`.
- It does not authorize or implement `MCC-007`, a runner bridge, generic process control, or
  arbitrary host control.
- It does not prove production identity/storage, production deployment, remote hosting, whole-host
  isolation, filesystem non-bypass, compliance, SIEM custody, or public security-product claims.
- It does not qualify a release candidate, complete human UAT, accept Local v1.0, or grant runtime,
  release, promotion, credential-custody, or external-system authority.

The deferred runtime seam remains `LV1-003`: a separately reviewed capability decision for the
smallest fixed runner bridge. Until that gate exists and passes, Leg A and Leg B remain deliberately
separate.
