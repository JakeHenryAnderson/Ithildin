# Hello World Sandbox Demo Roadmap

Status: roadmap and staged demo target.

This roadmap defines the concrete end-to-end proof of concept for Mission Control, a local LLM,
Ithildin, and an operator-managed sandbox or VM:

```text
Mission Control intent
-> local LLM plan
-> operator approval
-> Ithildin-mediated bounded sandbox artifact creation
-> evidence timeline
-> host staging review
-> approved host copy
```

The demo goal is intentionally tiny: create a directory named `hello-demo` and a text file named
`hello.txt` containing `Hello World`, then prove where that artifact came from and how it moved.

This document now tracks the staged demo path around the bounded
`sandbox.artifact.write_text` tool. It does not add Mission Control runtime behavior, VM lifecycle
control, shell execution, sandbox orchestration, broad filesystem writes, SIEM adapter behavior,
production identity, runtime Postgres, hosted telemetry, remote MCP hosting, plugin SDK behavior,
compliance automation, or public/security-product claims.

## Current Baseline

Ithildin already has the governed artifact transfer lab through Stage 2:

- Stage 1 Part 1: Ithildin-only known-good fixture summary.
- Stage 1 Part 2: Mission Control metadata handoff.
- Stage 2: simulated sandbox working-copy transfer with host/sandbox/staging hash comparisons.

Run:

```sh
make governed-artifact-transfer-stage2
make governed-artifact-transfer-stage2-check
make hello-world-sandbox-demo-packet
make hello-world-sandbox-demo-packet-check
make hello-world-sandbox-observed-demo
make hello-world-sandbox-observed-demo-check
make hello-world-mission-control-handoff
make hello-world-mission-control-handoff-check
make sandbox-promotion-evidence-contract-check
```

Generated packet:

```text
var/review-packets/v3/governed-artifact-transfer-lab/
var/review-packets/v3/hello-world-sandbox-demo/
var/review-packets/v3/hello-world-sandbox-observed-demo/
var/review-packets/v3/hello-world-mission-control-handoff/
```

The Hello World packet is evidence-only:

- bounded sandbox artifact write is implemented;
- tool count remains `24`;
- no governed tool calls are performed;
- no Mission Control runtime behavior is performed;
- no real VM startup, sandbox orchestration, shell execution, or host promotion occurs.

The observed Hello World packet performs the existing governed `sandbox.artifact.write_text`
approval/execution path in a temporary local fixture workspace, while Mission Control behavior,
local LLM execution, real VM/container lifecycle, sandbox orchestration, shell execution, and host
promotion remain disabled.

The Mission Control handoff packet is metadata-only. It wraps the observed Hello World evidence in
a display/import contract for Mission Control, but Mission Control does not execute the action,
replace Ithildin policy, call a local model, start a VM/container, orchestrate a sandbox, approve
promotion, or write to the trusted host.

The sandbox promotion evidence contract defines the future trusted-host movement evidence shape,
including `not_promoted`, `promotion_requested`, `promotion_approved`, `promotion_completed`, and
`promotion_rejected` states. The current Hello World flow records only `not_promoted`.

## Phase 1: Mission Control Evidence Attachment

Mission Control should import or reference:

- `mission-control-handoff/mission-control-handoff.json`;
- `evidence/manifest.json`;
- `evidence/stage2-simulated-sandbox-manifest.json`;
- `artifact-hashes.json`.

Expected Mission Control behavior:

- display operator intent;
- show source/output hashes;
- show review status and promotion status;
- link to Ithildin evidence artifacts;
- warn that Mission Control is metadata/display only.

Mission Control must not claim it executed governed actions, replaced Ithildin policy, started a
VM, provided OS isolation, or approved production/security/compliance use.

## Phase 2: Sandbox Profile Contract

Before runtime writes, a sandbox profile must be explicit and operator-managed:

```json
{
  "sandbox_id": "local-vm-demo-001",
  "sandbox_label": "operator-managed local VM demo",
  "workspace_id": "demo",
  "sandbox_working_root_label": "sandbox://demo",
  "host_staging_root_label": "host-staging://demo",
  "trusted_config_source": "operator-configured",
  "support_status": "demo_only",
  "warning_state": "not_os_isolation_proof"
}
```

Ithildin may record or validate these labels in a future implementation, but this roadmap does not
give Ithildin VM/container lifecycle control.

## Phase 3: Local LLM Plan Dry Run

Mission Control asks the local model for a plan only:

```text
Create a directory named hello-demo and a file named hello.txt containing Hello World.
```

Expected normalized proposal:

```json
{
  "intent": "create hello world demo artifact",
  "proposed_actions": [
    {
      "action": "create_directory",
      "path_label": "sandbox://hello-demo"
    },
    {
      "action": "write_text_file",
      "path_label": "sandbox://hello-demo/hello.txt",
      "content_sha256": "sha256:...",
      "content_preview_label": "fixed hello world fixture"
    }
  ],
  "requires_approval": true
}
```

The local model does not receive broad filesystem authority. It proposes a plan that Mission Control
and Ithildin can review.

## Phase 4: Bounded Artifact Creation Capability

The bounded artifact creation capability is now implemented as
[sandbox.artifact.write_text](capability-proposals/sandbox-artifact-write-text.md).

It is not shell and not broad filesystem write. It is a narrow artifact-creation lane:

- creates agent-owned text artifacts only;
- writes only under an operator-approved sandbox or staging root;
- denies overwrite by default;
- requires explicit approval for trusted host promotion;
- records hashes and labels, not raw sensitive paths;
- enforces size, encoding, path, symlink, hardlink, hidden-path, and `.git` denials.

Implementation is limited to the approved local-preview `sandbox.artifact.write_text` boundary.
Mission Control runtime integration, local LLM invocation, VM/container lifecycle, sandbox
orchestration, and host promotion remain separate future gates.

## Phase 5: Hello World Sandbox Run

Expected happy path after Mission Control/local-model/VM layers are separately approved:

1. Mission Control creates a mission.
2. Local LLM proposes the `hello-demo/hello.txt` plan.
3. Operator approves the bounded artifact creation.
4. Ithildin creates the artifact inside the sandbox/staging root through the reviewed
   `sandbox.artifact.write_text` executor.
5. Ithildin records action evidence:
   - run ID;
   - principal ID;
   - model/client label;
   - sandbox ID;
   - workspace ID;
   - action/proposal hash;
   - file hash;
   - policy hash;
   - approval ID;
   - audit head.
6. Mission Control displays the run timeline and evidence attachments.

## Phase 6: Host Promotion

Promotion is separate from creation:

```text
sandbox artifact -> host staging -> approved host copy
```

Promotion evidence must prove:

- the sandbox output hash;
- the host staging hash;
- the approved host copy hash;
- approval ID;
- operator/principal label;
- timestamp;
- no automatic promotion occurred.

## Negative Cases

The implementation plan must include denials for:

- `../` traversal;
- absolute paths;
- control characters;
- hidden paths;
- `.git` paths;
- symlinks;
- hardlinks;
- overwrite without explicit approval;
- oversized content;
- unsupported encoding;
- host write without promotion;
- model requests for shell, Docker, Kubernetes, browser automation, or broad write access.

## Success Definition

The end goal is successful when an operator can follow a guided path where Mission Control asks a
local model for the Hello World task, Ithildin mediates the bounded artifact creation inside an
operator-managed sandbox/staging root, and the final host artifact can be compared against an
evidence timeline with matching hashes.

The current observed packet proves the Ithildin-mediated artifact creation slice. The complete
Mission Control plus local LLM plus real VM/sandbox plus host-promotion workflow remains future
staged work.
