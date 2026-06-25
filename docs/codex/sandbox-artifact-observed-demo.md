# Sandbox Artifact Observed Demo

Status: observed local fixture execution.

The sandbox artifact observed demo is the first deterministic packet that exercises the implemented
`sandbox.artifact.write_text` governed tool in a temporary workspace and records the approval,
execution, artifact, and audit evidence that results. It complements the simulated Hello World
sandbox packet: the simulated packet shows the future Mission Control plus local LLM story shape,
while this observed packet proves Ithildin's current bounded write path can require approval,
consume the approval once, write a sandbox-labeled text artifact, and verify the local audit chain.

Run it with:

```sh
make sandbox-artifact-observed-demo
make sandbox-artifact-observed-demo-check
```

The generated packet is ignored under:

```text
var/review-packets/v3/sandbox-artifact-observed-demo/
```

## Evidence Shape

The packet contains:

- `SANDBOX_ARTIFACT_OBSERVED_DEMO.md` - human-readable observed local fixture execution transcript.
- `sandbox-artifact-observed-demo.json` - machine-readable evidence for the observed flow.
- `artifact-hashes.json` - SHA-256 hashes and byte counts for generated packet artifacts.

The observed evidence records:

- tool name and tool count;
- governed tool calls performed status;
- initial governed request ID and `approval_required` status;
- approval ID, approval status, and whether raw content was excluded from approval scope;
- execution request ID and completed result status;
- sandbox artifact label, content hash, byte count, and hash-match status;
- audit verification validity, event count, and head hash;
- explicit boundary flags showing no Mission Control runtime behavior, no VM/container lifecycle,
  no sandbox orchestration, no shell execution, and no host promotion.

## Boundary

This is local-preview only operator evidence. It does not start a VM, orchestrate a sandbox, invoke
Mission Control runtime behavior, execute shell commands, promote an artifact to a trusted host
location, or claim production sandboxing, external custody, SIEM integration, compliance automation,
or enterprise deployment readiness.

The transcript intentionally avoids file contents, raw host paths, prompts, secrets, VM logs,
Mission Control state, and sandbox internals. The artifact payload is bound by SHA-256 and byte
count so an operator can compare evidence without exposing the payload text in the review packet.

## Review Use

Reviewers should treat this packet as an observed local fixture for the bounded write path, not as
external/source-review closure. It helps bridge the current v1.0 workbench story: Ithildin can
mediate a sandbox-labeled artifact write through approval and audit evidence, while broader
agent-in-VM operation, Mission Control orchestration, host promotion, and enterprise deployment
remain separate future work.
