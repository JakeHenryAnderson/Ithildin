# Sandbox/VM Static Profile And Preflight Implementation Plan

Status: implementation-planning only.

This document plans a future static, operator-managed sandbox/VM profile fixture and read-only
preflight runner. It does not add runtime behavior, API endpoints, MCP tools, executors, tool
manifests, policy rules, local model invocation, Mission Control runtime behavior, VM/container
lifecycle control, Docker socket access, Kubernetes control, browser automation, shell execution,
arbitrary HTTP, broad filesystem writes, trusted-host promotion, SIEM adapters, production identity,
runtime Postgres, hosted telemetry, plugin SDK behavior, compliance automation, public
security-product claims, or new governed tool powers.

Implementation state: blocked.

The future implementation may be planned only as a local-preview diagnostic and fixture-validation
lane. It must not manage a VM, start a container, call a model, move host files, promote artifacts,
or become a sandbox orchestrator.

Validate this plan with:

```sh
make sandbox-vm-static-profile-preflight-plan-check
```

## Relationship To Existing Evidence

This plan follows the current sandbox/VM proof-of-concept review packet:

- [enterprise-readiness-runway.md](enterprise-readiness-runway.md);
- [sandbox-vm-worker-boundary-charter.md](sandbox-vm-worker-boundary-charter.md);
- [sandbox-vm-profile-contract.md](sandbox-vm-profile-contract.md);
- [sandbox-vm-preflight-contract.md](sandbox-vm-preflight-contract.md);
- [hello-world-sandbox-demo-roadmap.md](hello-world-sandbox-demo-roadmap.md);
- [hello-world-sandbox-observed-demo.md](hello-world-sandbox-observed-demo.md);
- [hello-world-mission-control-handoff.md](hello-world-mission-control-handoff.md);
- [sandbox-artifact-write-text-source-review.md](sandbox-artifact-write-text-source-review.md);
- [sandbox-promotion-evidence-contract.md](sandbox-promotion-evidence-contract.md).

The current packet is generated with `make sandbox-vm-poc-review-packet`. This plan does not close
that review. It records what the first later implementation proposal should look like if the packet
is accepted for continued local-preview work.

## Future Static Profile Fixture

A future fixture may be a committed or operator-provided JSON file used only for local-preview
preflight validation. It should contain labels and posture evidence, not host secrets or raw
authority handles.

Required fixture sections:

- `schema_version`;
- `sandbox_id`;
- `workspace_id`;
- `profile_label`;
- `trusted_config_source`;
- `support_status`;
- `platform`;
- `mounts`;
- `network`;
- `ingress_egress`;
- `cleanup`;
- `warnings`;
- `decision`.

Required false authority flags:

- `ithildin_starts_vm: false`;
- `ithildin_starts_container: false`;
- `ithildin_has_docker_socket: false`;
- `ithildin_has_kubernetes_control: false`;
- `ithildin_runs_shell: false`;
- `mission_control_executes_actions: false`;
- `local_model_invoked: false`;
- `trusted_host_promotion_enabled: false`;
- `broad_network_access: false`.

The fixture must use labels such as `sandbox://demo`, `host-staging://demo`, `approved://demo`, and
`evidence://demo`. It must not expose raw host paths, VM disk paths, usernames, home directories,
secrets, environment variables, model prompts, model outputs, command lines, shell output, Docker
socket paths, Kubernetes contexts, browser profiles, network credentials, file contents, diffs,
response bodies, package scripts, dependency names, or raw sandbox internals.

## Future Read-Only Preflight Runner

If approved later, a preflight runner may load the static profile fixture and return a secret-free
go/no-go report. It may inspect only the fixture contents and existing Ithildin readiness evidence.

Allowed future checks:

- verify required sections are present;
- verify schema version is supported;
- verify platform support status is one of `supported_local_preview`, `unsupported`, or
  `review_required`;
- verify unsupported Windows/WSL/remote/cloud/Kubernetes/browser sandbox profiles do not claim
  local-preview security support;
- verify required false authority flags are false;
- verify mount/root values are labels, not raw paths;
- verify network posture is `offline`, `operator_managed`, `unknown`, or `review_required`, with
  broad network access false;
- verify ingress/egress zones remain separated;
- verify `promotion_status: not_promoted`;
- verify cleanup transcript expectations are present;
- verify warning chips include `not_os_isolation_proof`, `operator_managed`, and
  `local_preview_only`;
- emit a `decision` of `go`, `no_go`, or `review_required` with safe reasons only.

Forbidden future behavior:

- starting, stopping, snapshotting, or controlling VMs or containers;
- reading VM disks or sandbox filesystem contents;
- mounting or unmounting filesystems;
- calling Docker, Kubernetes, shell, browsers, package managers, CI systems, Git, network clients,
  local models, Mission Control runtime APIs, or hosted services;
- creating, overwriting, deleting, moving, or promoting files;
- granting trust to host paths or sandbox roots;
- changing policy, manifests, approvals, audit semantics, MCP exposure, or API behavior.

## Proposed Output Contract

The future preflight output should be a closed, secret-free object:

- `schema_version`;
- `profile_id`;
- `workspace_id`;
- `sandbox_id`;
- `support_status`;
- `platform_label`;
- `mount_label_count`;
- `network_posture`;
- `ingress_egress_status`;
- `cleanup_status`;
- `warning_labels`;
- `false_authority_flags`;
- `promotion_status`;
- `decision`;
- `safe_reasons`;
- `output_policy`.

The output must not include raw paths, file contents, model prompts, model outputs, shell output,
Docker/Kubernetes handles, environment values, network endpoints beyond coarse labels, usernames,
home directories, VM disk paths, or sensitive workspace details.

## Future Negative Transcript Plan

Any future implementation must include observed negative transcripts for:

- missing required section;
- unsupported platform claiming support;
- raw path-shaped mount label;
- broad network posture;
- missing `not_os_isolation_proof` warning;
- Mission Control execution authority claim;
- local model invocation claim;
- Docker socket or Kubernetes control claim;
- shell/browser/arbitrary HTTP claim;
- trusted-host promotion enabled;
- stale cleanup transcript;
- artifact ingress/egress zone collapse;
- malformed JSON fixture;
- oversized fixture;
- unknown additional fields.

Negative transcripts must record command/scenario, expected denial, observed status/reason, and
evidence pointer without file contents, raw paths, prompts, secrets, model output, or stack traces.

## Future Source Review Requirements

Before any runtime preflight implementation is accepted, a source-review bundle must include:

- this plan;
- the sandbox/VM proof-of-concept review packet;
- static profile fixture schema and examples;
- implementation decision document;
- preflight runner source;
- focused tests;
- negative transcripts;
- no-new-powers evidence;
- tool-surface invariant evidence;
- release-check evidence;
- packet redaction scan evidence.

Finding IDs should use `EXT-SANDBOX-PREFLIGHT-###`.

## Current Allowed State

- tool count remains `24`;
- runtime changes allowed: `false`;
- Mission Control runtime allowed: `false`;
- local model invocation allowed: `false`;
- sandbox orchestration allowed: `false`;
- trusted-host promotion allowed: `false`;
- network expansion allowed: `false`;
- new power classes allowed: `false`.

## Future Implementation Gate

A later implementation sprint must add a separate implementation decision document and gate. That
gate must fail closed unless:

- the implementation remains read-only and fixture-only;
- no new MCP/API/governed tool surface is added unless separately approved;
- no VM/container lifecycle, shell, Docker, Kubernetes, browser, arbitrary HTTP, broad write,
  Mission Control runtime, local model, trusted-host promotion, SIEM adapter, production identity,
  runtime Postgres, hosted telemetry, plugin SDK, or compliance behavior appears;
- static profile fixture tests and negative transcripts pass;
- release-check and packet redaction scan pass.

Until that separate gate exists and passes, implementation remains blocked.
