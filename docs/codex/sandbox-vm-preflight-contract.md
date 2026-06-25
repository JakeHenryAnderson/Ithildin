# Sandbox/VM Preflight Contract

Status: design-only preflight contract for a future operator-managed sandbox/VM worker proof of
concept.

This contract defines the evidence a future sandbox/VM worker proof of concept must collect before
any model/client action is treated as a governed demo step. It does not add runtime behavior, API
endpoints, MCP tools, tool manifests, policy rules, executors, sandbox orchestration,
VM/container lifecycle management, local model invocation, Mission Control runtime behavior,
trusted-host promotion, SIEM adapters, production identity, runtime Postgres, hosted telemetry,
shell, Docker, Kubernetes, browser automation, arbitrary HTTP, broad filesystem writes, compliance
automation, or new governed tool powers.

Validate this contract with:

```sh
make sandbox-vm-preflight-contract-check
```

## Relationship To Existing Contracts

The [Sandbox/VM Worker Boundary Charter](sandbox-vm-worker-boundary-charter.md) defines role
separation. The [Sandbox/VM Profile Contract](sandbox-vm-profile-contract.md) defines the
operator-supplied metadata profile. This preflight contract defines the future go/no-go evidence
that must be captured after a profile exists and before any sandbox/VM worker demo action is
displayed as ready.

The preflight result is evidence metadata only. It is not a sandbox launcher, VM health probe,
container API, model runner, shell command, promotion operation, or Mission Control runtime action.

## Required Preflight Sections

A future preflight result must be secret-free and include these sections:

| Section | Required evidence |
| --- | --- |
| `profile` | `sandbox_id`, `workspace_id`, profile schema version, support status, warning state, and `promotion_status: not_promoted`. |
| `platform` | host platform label, sandbox platform label, support status, unsupported reason if any, and review-required warning state. |
| `mounts` | working root label, host staging label, approved-output label state, mount posture label, write posture label, and raw-paths-redacted flag. |
| `network` | network posture label, outbound policy label, DNS policy label, proxy policy label, and broad-network-access flag set to `false`. |
| `ingress_egress` | source/inbox label, sandbox working label, host staging label, approved-output label state, artifact hash requirement, and promotion state. |
| `cleanup` | lifecycle owner, cleanup posture, cleanup evidence label, stale-work warning state, and manual cleanup note label if needed. |
| `warnings` | visible warning chips for local-preview, not OS-isolation proof, not production, not compliance, and mediated-actions-only. |
| `decision` | `ready`, `blocked`, or `review_required`, with secret-free reasons. |

## Supported Platform Matrix

The first real proof of concept may only claim a local-preview support profile when:

- host platform is macOS or Linux;
- sandbox/VM platform is explicitly labeled by the operator;
- profile support status is `demo_only` or `review_required`;
- warning state includes `not_os_isolation_proof`;
- preflight does not infer OS isolation from platform labels;
- Windows, WSL, remote hosts, managed Kubernetes, and browser-based sandboxes remain
  `unsupported` or `review_required` until separately reviewed.

## Mount And Root Posture

Preflight evidence may use labels only:

- `source-inbox://...`;
- `sandbox://...`;
- `host-staging://...`;
- `approved://...` only as `not_configured` or future design-only label until promotion exists;
- `evidence://...`.

It must not expose raw host paths, VM paths, container paths, mount internals, home-directory paths,
Docker socket paths, credentials, shell commands, environment values, or directory listings.

Preflight must fail closed or require review if:

- the working root label is missing;
- the host staging label is missing;
- any label looks like a raw absolute path;
- approved-output is presented as active before the trusted-host promotion lane exists;
- cleanup posture is missing;
- the profile claims Ithildin starts, stops, repairs, snapshots, or controls the VM/container.

## Network Posture

Preflight evidence must record a coarse network posture such as:

- `offline`;
- `operator_managed`;
- `unknown`;
- `review_required`.

It must not record credentials, proxy URLs, broad allowlists, request bodies, cookies, raw DNS
resolver details, or endpoint secrets. Broad network access remains false until a separate reviewed
network design exists.

## Artifact Ingress And Egress

Preflight evidence must preserve the zone distinction:

1. source/inbox label;
2. sandbox working label;
3. host staging label;
4. approved-output label state;
5. evidence label.

Any artifact movement claim must be hash-bound in future runtime work. Current proof may only record
`promotion_status: not_promoted`. Preflight must not claim trusted-host promotion, overwrite,
delete, move, archive extraction, or automatic repair.

## Failure And Cleanup Transcript Requirements

A future implementation plan must include secret-free transcripts for:

- missing profile;
- unsupported platform;
- missing warning state;
- raw path-shaped label;
- missing cleanup posture;
- broad network posture;
- approved-output active before promotion exists;
- artifact hash mismatch;
- stale sandbox working state;
- Mission Control claiming execution or sandbox authority;
- local model request for shell, Docker, Kubernetes, browser automation, arbitrary HTTP, or broad
  filesystem writes.

Transcripts must show scenario, expected decision, observed decision, safe reason, and evidence
pointer. They must not include prompts, model output, file contents, diffs, response bodies,
secrets, raw paths, VM logs, container logs, shell output, dependency names, package scripts, or
sandbox internals.

## Current Allowed State

Current Ithildin work may document this preflight contract, generate static review packets, and
record sandbox-labeled evidence. It may not run a live sandbox preflight, load live profiles, start
a VM/container, call a local model, grant Mission Control runtime behavior, promote artifacts, or
claim OS isolation.

## Future Implementation Gate

Any future live preflight runner must receive a separate proposal, implementation plan,
implementation gate, source-review handoff, negative transcripts, release/readiness update, and
explicit external/source-review disposition. Until then, `make sandbox-vm-preflight-contract-check`
must continue reporting:

- runtime changes allowed: `false`;
- Mission Control runtime allowed: `false`;
- local model invocation allowed: `false`;
- sandbox orchestration allowed: `false`;
- trusted-host promotion allowed: `false`;
- network expansion allowed: `false`;
- new power classes allowed: `false`.
