# Hello World Sandbox Observed Demo

Status: observed local fixture execution.

This is the first concrete Hello World version of the governed workbench loop:

```text
operator intent metadata
-> local model plan metadata
-> Ithildin-mediated sandbox.artifact.write_text request
-> approval_required
-> local admin fixture approval
-> completed sandbox-labeled artifact
-> audit verification and artifact hashes
```

Run:

```sh
make hello-world-sandbox-observed-demo
make hello-world-sandbox-observed-demo-check
```

Generated packet:

```text
var/review-packets/v3/hello-world-sandbox-observed-demo/
```

## What This Proves

- `sandbox.artifact.write_text` can perform the tiny Hello World artifact creation path through the
  governed tool-call service.
- The packet records governed tool calls performed: `true`.
- The action requires approval before execution.
- The approval is consumed and bound by content hash rather than raw content in approval scope.
- The artifact hash matches executor evidence.
- The local audit chain verifies after the flow.

## What This Does Not Prove

- Mission Control runtime behavior;
- a real local LLM invocation;
- VM/container startup;
- sandbox orchestration or OS isolation;
- host promotion or trusted-host copy;
- SIEM custody, compliance automation, production identity, or public/security-product readiness;
- activity outside Ithildin-mediated tool calls.

## Reading Order

1. `HELLO_WORLD_SANDBOX_OBSERVED_DEMO.md` for the operator-facing story.
2. `hello-world-sandbox-observed-demo.json` for machine-readable evidence.
3. `observed-governed-tool/SANDBOX_ARTIFACT_OBSERVED_DEMO.md` for the underlying governed tool
   transcript.
4. `observed-governed-tool/sandbox-artifact-observed-demo.json` for approval/execution/audit fields.
5. `artifact-hashes.json` for packet digests.

## Boundary

Mission Control runtime behavior: `false`.
Local LLM runtime behavior: `false`.
Real VM or container started: `false`.
Sandbox orchestration performed: `false`.
Shell execution performed: `false`.
Host promotion performed: `false`.

This is local-preview workbench evidence only. It moves the Hello World roadmap from simulated
packet shape toward observed Ithildin mediation, while leaving Mission Control integration, local
model execution, real VM/sandbox handling, and host promotion as separate future gates.
