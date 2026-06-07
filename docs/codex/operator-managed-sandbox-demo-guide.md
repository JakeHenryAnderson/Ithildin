# Operator-Managed Sandbox Demo Guide

Status: demo/readiness guide. This guide does not add runtime behavior, API endpoints, MCP tools,
tool manifests, policy rules, executors, sandbox orchestration, SIEM adapters, production identity,
runtime Postgres, hosted telemetry, shell, Docker, Kubernetes, browser automation, arbitrary HTTP,
broad filesystem writes, or new governed tool powers.
It does not add sandbox lifecycle control.

This guide shows how to demonstrate Ithildin as the governed control panel around an
operator-managed workspace or sandbox. The operator is responsible for starting, isolating,
mounting, supervising, and stopping any container, VM, or local workspace. Ithildin only mediates
the actions that pass through its registered tools.

## Demo Boundary

The demo may show:

- an operator-created workspace or sandbox label;
- a local MCP-capable agent or model client connected to Ithildin;
- governed read-only tool calls and approval-gated patch apply;
- Agent Run records, timeline evidence, and query filters in the review console;
- run evidence export through `GET /runs/{run_id}/evidence-export`;
- audit verification, local signed-export demos, negative denials, and incident reconstruction.

The demo must not claim:

- Ithildin starts containers or VMs;
- Ithildin mounts a Docker socket;
- Ithildin runs shell commands as a governed tool;
- Ithildin manages Kubernetes or browser automation;
- Ithildin proves OS isolation, activity outside mediated tools, SIEM-grade custody, compliance, or
  production security.

## Recommended Flow

1. Seed a safe local workspace:

   ```text
   make demo-seed
   ```

2. Start the local preview stack if the operator wants the API and UI in Compose:

   ```text
   make compose-up
   make compose-smoke
   ```

3. Launch the MCP server for a local client or model-side MCP configuration:

   ```text
   uv run python -m ithildin_mcp_server
   ```

4. From the MCP client, perform a narrow read such as `fs.list` or `fs.read` against the demo
   workspace, then attempt a write through `fs.patch.propose` and approval-gated `fs.patch.apply`.

5. Open the review console and inspect:

   - System Trust warnings;
   - Agent Run filters and summary chips;
   - selected run timeline evidence;
   - pending approval binding evidence;
   - patch diagnostics;
   - audit integrity.

6. Export the selected run evidence with the review-console Export Run Evidence action or the
   admin API:

   ```text
   GET /runs/{run_id}/evidence-export
   ```

7. Reconstruct the mediated action using the Agent Run timeline, approval record, patch diagnostics,
   audit head, and exported run evidence.

8. Demonstrate safe denials and local evidence helpers:

   ```text
   make negative-review-transcripts
   make signed-evidence-demo
   make signed-evidence-demo-verify
   ```

## Evidence Checklist

A successful demo should leave reviewers able to point to:

- workspace label and local preview support status;
- principal and session labels;
- Agent Run ID and selected timeline events;
- policy decision evidence and matched rules;
- approval ID and binding evidence for any write;
- patch diagnostic status;
- audit verification head;
- run evidence export bundle;
- optional non-production signed-evidence demo artifacts.

## Stop Conditions

Stop the demo and record the issue if:

- a step requires shell, Docker, Kubernetes, browser, or broad-write governed tools;
- the local client bypasses Ithildin for the action being demonstrated;
- evidence would expose prompts, model output, file contents, diffs, response bodies, secrets,
  package script values, dependency names, or raw sensitive paths;
- the operator cannot distinguish Ithildin-mediated evidence from activity outside Ithildin;
- the demo wording implies sandboxing, compliance automation, SIEM custody, production identity, or
  public/security-product readiness.

## Expected Conclusion

The right conclusion is:

> Ithildin can act as a local-preview governance dashboard and evidence recorder for actions
> mediated through its narrow registered tools around an operator-managed workspace.

The wrong conclusion is:

> Ithildin is a sandbox controller, SIEM, compliance product, production identity system, hosted
> control plane, or proof of activity outside Ithildin-mediated tools.
