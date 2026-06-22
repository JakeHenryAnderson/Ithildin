# Governed Artifact Transfer Lab

Status: future goal and Stage 1 proof-of-concept plan.

This lab is the first practical bridge between Ithildin and Mission Control. It keeps the projects
distinct: Mission Control is the operator/control plane, Ithildin is the governed MCP/tool gateway,
and a future VM or sandbox is the agent workshop.

## Product Thesis

Heavily regulated workflows should let agents move quickly inside a constrained workspace while
making every bridge back to trusted user data explicit, approval-gated, and evidenced.

The default posture is:

- the local OS hosts the operator surface, trusted source files, and reviewed outputs;
- the agent works on approved copies or agent-created artifacts;
- the agent writes only to working or staging zones by default;
- overwriting, deleting, or promoting non-agent-created artifacts requires approval;
- evidence correlates source hashes, sandbox copies, tool calls, approvals, outputs, and promotion.

## Roles

| Layer | Responsibility |
| --- | --- |
| Mission Control | Mission, operator intent, folder/workspace labels, approvals, dashboard, evidence review. |
| Ithildin | Tool mediation, schema validation, policy, approval binding, executor limits, audit, export evidence. |
| Sandbox or VM | Disposable working copy, agent scratch space, generated outputs, blast-radius containment. |
| Agent harness | Model invocation, structured tool-call requests, transcript, model/client label, stop conditions. |

## Zone Contract

A regulated-friendly workspace should eventually use explicit zones:

```text
source/      original files, no direct agent write
inbox/       operator-dropped files for approved intake
working/     sandbox or VM working copy
staging/     agent-created outputs awaiting review
approved/    human-approved outputs
evidence/    hashes, approvals, audit exports, transcripts, packets
```

The first implementation does not need all zones as enforced runtime behavior. The POC should
document which folders are fixture-only, which actions are manual, and which actions are mediated by
Ithildin.

## Stage 1: Local Mediated Summary

Goal: prove the governance loop with no VM and no risky data.

Use a harmless text fixture, such as a saved public article excerpt, in a dummy workspace. The agent
or harness should request only mediated read and output actions. The expected output is a summary
artifact in staging, plus evidence that the source file was read and the output was produced through
the governed path.

Evidence to collect:

- Mission Control mission or manual mission note;
- input artifact path label and SHA-256 hash;
- Ithildin tool-call and policy evidence;
- approval record if writing or promotion is required;
- output artifact SHA-256 hash;
- audit head before and after;
- local packet or export path.

## Stage 2: VM Working Copy Summary

Goal: prove artifact transfer into a disposable workshop.

The host file is hashed, copied into a VM or sandbox working area, summarized there, and returned to
host staging only after review. Hermes or another local model may run on the host or in the VM, but
the agent should request workspace actions through Ithildin rather than receive broad shell or
filesystem authority.

Evidence to collect:

- source hash on the host;
- sandbox copy hash;
- sandbox or VM label;
- model/client label;
- output hash inside the sandbox;
- promotion approval ID;
- final host staging hash.

## Stage 3: Promotion With Before/After Approval

Goal: distinguish agent-created artifacts from approved host artifacts.

The agent can revise its own staged draft quickly. Promotion back to an approved or trusted host
area is a separate, approval-gated action with evidence binding the input, output, operator decision,
and final hash.

## Non-Goals

This lab does not add shell execution, Docker socket access, Kubernetes tools, browser automation,
arbitrary HTTP, broad filesystem writes, production identity, runtime Postgres, hosted telemetry,
remote MCP hosting, plugin SDK behavior, sandbox orchestration, SIEM adapters, compliance
automation, or public/security-product claims.

It also does not claim that Ithildin governs actions an agent performs outside Ithildin-mediated
tools. A VM contains blast radius; Ithildin governs mediated actions; Mission Control explains and
reviews the mission.

## First Success Definition

Stage 1 is successful when a harmless local text file is summarized into a staged output and the
operator can compare at least three evidence sources:

1. source and output hashes;
2. Ithildin audit/tool-call evidence;
3. Mission Control mission or manual evidence note.

The POC should remain intentionally boring. A boring summary workflow with clean evidence is the
right first proof before VM lifecycle, sandbox promotion, or regulated-data templates.
