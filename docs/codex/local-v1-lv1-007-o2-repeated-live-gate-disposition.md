# LV1-007 O2 Repeated Live-Gate Disposition

Status: `STOP — repeated-gate condition reached`

- Local-v1 milestone: `LV1-007`
- Release outcome: `O2`
- Final attempted candidate: `00473f8a8e7ad16b15733a7476948c78646ea26f`
- Final attempted tree: `683edcc7a86e053aa5f4ae4b99a9e62dadb65ddc`
- Milestone status: `not_started`
- Outcome status: `not_started`
- Current progress: `6/8` outcomes and `7/8` milestones complete
- Governed tool count: `24`
- Runtime, release, promotion, production, and UAT authority: `false`
- Fourth O2 rehearsal in this task: `not_authorized`

This is a failure-and-cleanup disposition. It does not complete `O2`, start `O8`, qualify a
Local-v1 candidate, authorize human UAT, or change the 24-tool and no-arbitrary-host-control
boundaries.

## Why Work Stopped

The deliberate `make local-v1-real-agent-run` gate failed three exact-candidate executions in this
task:

| Attempt | Exact candidate | Safe failure | Disposition |
| --- | --- | --- | --- |
| 1 | `5b54d3c43507f5818d667b6af88c79e5f91abd4f` | `hermes_candidate_run_failed` | The harness incorrectly treated a nonzero runner process exit as authoritative before evaluating Gateway evidence. Candidate `8b19cd2e8811abaf4ca4b402c5f99bf4ccdebbc6` repaired that truth-source error. |
| 2 | `8b19cd2e8811abaf4ca4b402c5f99bf4ccdebbc6` | `runtime_evidence_inventory_invalid` | Source and isolated-container diagnostics established that the pinned native Hermes image did not supply the expected `HERMES_HOME`; the host-matching nonroot UID therefore could not use the tracked configuration. Candidate `00473f8a8e7ad16b15733a7476948c78646ea26f` supplied an explicit private runner home and fixed secret-free inventory classifications. |
| 3 | `00473f8a8e7ad16b15733a7476948c78646ea26f` | `gateway_o2_evidence_invalid` | Hermes produced capturable Gateway evidence, but the authoritative event set did not prove every required allowed, denied, approval-required, identity, and audit observation. Private evidence was removed by the harness, so the missing observation is not inferred. |

The same reused Sol-high reviewer returned `GO` with zero Critical, High, Medium, or Low findings
for each repaired exact candidate before its next live attempt. The final review specifically
confirmed the nonroot private-home topology, read-only configuration mount, absence of Docker
socket or credential mounts, fixed failure classifications, descriptor-anchored evidence capture,
and exact cleanup behavior. No xhigh or Ultra reviewer was used.

Repository instructions require the manager to stop when the same gate fails three times. No
private runtime artifact, model prose, prompt, request or approval identity, raw run identity,
container log, environment value, or credential was inspected to diagnose attempt 3. No fourth
attempt was made.

## Cleanup Verification

The success-only harness retained no report for any failed attempt. Independent sanitized queries
after attempt 3 observed:

- zero containers matching the fixed O2 container namespace;
- zero images matching the fixed O2 image namespace;
- zero Local-v1 real-agent success reports; and
- a clean tracked checkout at the attempted candidate.

The harness removed the exact container, exact candidate image, extracted candidate tree, candidate
archive, copied analysis evidence, and private runtime state before returning the safe failure.
There is no ambiguous live resource or retained private evidence requiring recovery.

## What Remains Unproved

`O2` remains incomplete. Current evidence does not prove that one pinned real agent produced, in a
single candidate-bound rehearsal, all of:

- an allowed and completed in-scope read;
- an out-of-scope read denied before execution;
- an unapproved HTTP request denied before execution;
- an approval-required write left pending without execution;
- fixed local stdio identity on all governed events; and
- a valid authoritative Gateway audit chain.

Historical Hermes Track A evidence remains useful lineage, but it is not current-candidate O2
evidence. Static tests and the three exact reviews do not replace the missing live observation.

## Resume Boundary

A fresh, explicitly resumed O2 recovery task should:

1. preserve `00473f8a8e7ad16b15733a7476948c78646ea26f` as the last attempted runtime candidate;
2. add the smallest secret-safe failure projection that reports only the fixed required-observation
   bitmap and event counts, never model output, prompts, fixture bodies, raw identities, or
   environment values;
3. reconsider whether the O2 contract needs both the extra directory-list and HTTP-denial
   observations or only its stated allowed, denied, and approval-required acceptance behavior,
   without weakening before-execution and audit-chain proof;
4. run focused validation and one proportional Sol-high review if the Docker/audit capture surface
   changes; and
5. authorize at most one new live attempt in that fresh recovery task.

The resumed task must stop on any Critical/High finding, unsafe diagnostic requirement, cleanup
ambiguity, product-boundary expansion, or its own repeated-gate condition. The 24-tool surface,
local stdio ingress, synthetic-only state, no Docker socket in the product or runner, no arbitrary
host control, and separation of Gateway, runner, and model-provider truth remain fixed.
