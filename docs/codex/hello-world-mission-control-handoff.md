# Hello World Mission Control Handoff

Status: metadata-only handoff.

This packet is the safe bridge from Ithildin's observed Hello World evidence to Mission Control as
an operator display surface. Mission Control may import/display mission labels, evidence links,
approval status, artifact hashes, and warning chips. It does not execute the governed action,
replace Ithildin policy, call a local LLM, start a VM/container, orchestrate a sandbox, or promote
artifacts to the trusted host.

Run:

```sh
make hello-world-mission-control-handoff
make hello-world-mission-control-handoff-check
```

Generated packet:

```text
var/review-packets/v3/hello-world-mission-control-handoff/
```

## What Mission Control May Display

- Mission ID and operator intent label.
- Local model/client label as metadata only.
- `sandbox.artifact.write_text` request, approval, execution, and artifact hash status.
- Audit verification status and audit head hash.
- Attachment links to the observed Hello World and governed-tool evidence packets.
- Warning chips for local-preview only, Mission Control metadata only, local LLM not invoked,
  VM/container not started, and host promotion not performed.

## What Mission Control Must Not Claim

- Mission Control runtime behavior: `false`.
- local LLM runtime behavior: `false`.
- real VM or container started: `false`.
- sandbox orchestration performed: `false`.
- shell execution performed: `false`.
- host promotion performed: `false`.

Mission Control must not claim execution authority, policy authority, approval authority, VM or
sandbox lifecycle control, host promotion, production identity, SIEM custody, compliance automation,
or public/security-product readiness.

## Reading Order

1. `HELLO_WORLD_MISSION_CONTROL_HANDOFF.md` for this operator-facing guide.
2. `mission-control-handoff.json` for the importable metadata payload.
3. `observed-hello-world/HELLO_WORLD_SANDBOX_OBSERVED_DEMO.md` for the observed Hello World flow.
4. `observed-hello-world/hello-world-sandbox-observed-demo.json` for machine-readable evidence.
5. `observed-hello-world/observed-governed-tool/SANDBOX_ARTIFACT_OBSERVED_DEMO.md` for the
   underlying governed tool transcript.
6. `artifact-hashes.json` for packet digests.

## Boundary

This is not a Mission Control integration runtime. It is a local-preview evidence handoff contract
so the two products can remain distinct while still working together: Mission Control presents the
mission and evidence, while Ithildin mediates the governed tool call and records audit evidence.
