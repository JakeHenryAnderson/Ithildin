# Sandbox/VM Static Profile Fixture Contract

Status: fixture-contract only.

This document defines the first committed, non-production fixture shape for a future read-only
sandbox/VM preflight runner. It does not add runtime behavior, API endpoints, MCP tools, executors,
tool manifests, policy rules, local model invocation, Mission Control runtime behavior, VM/container
lifecycle control, Docker socket access, Kubernetes control, browser automation, shell execution,
arbitrary HTTP, broad filesystem writes, trusted-host promotion, SIEM adapters, production identity,
runtime Postgres, hosted telemetry, plugin SDK behavior, compliance automation, public
security-product claims, or new governed tool powers.

Implementation state: fixture validation only.

Validate this contract and the example fixture with:

```sh
make sandbox-vm-static-profile-fixture-contract-check
```

## Relationship To The Preflight Plan

This contract follows [sandbox-vm-static-profile-preflight-plan.md](sandbox-vm-static-profile-preflight-plan.md).
The plan describes a future static profile fixture and read-only preflight runner. This contract
commits only the safe fixture shape and one example fixture so reviewers can inspect the expected
evidence before any runner is implemented.

The example fixture is
[sandbox-vm-static-profile.local-preview.example.json](fixtures/sandbox-vm-static-profile.local-preview.example.json).
It is non-production, contains no host paths, and grants no authority.

## Required Fixture Sections

The fixture must be a closed JSON object with these top-level sections:

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

Unknown top-level sections are rejected by the contract check.

## Required False Authority Flags

The fixture must include these false authority flags under `decision.false_authority_flags`:

- `ithildin_starts_vm: false`;
- `ithildin_starts_container: false`;
- `ithildin_has_docker_socket: false`;
- `ithildin_has_kubernetes_control: false`;
- `ithildin_runs_shell: false`;
- `mission_control_executes_actions: false`;
- `local_model_invoked: false`;
- `trusted_host_promotion_enabled: false`;
- `broad_network_access: false`.

If any flag is absent or true, the fixture is invalid.

## Safe Labels Only

The fixture may use only coarse labels for roots, mounts, and evidence zones. Example labels:

- `sandbox://demo`;
- `sandbox-working://demo`;
- `host-staging://demo`;
- `approved://demo`;
- `evidence://demo`.

The fixture must not expose raw host paths, VM disk paths, usernames, home directories, secrets,
environment variables, model prompts, model outputs, command lines, shell output, Docker socket
paths, Kubernetes contexts, browser profiles, network credentials, file contents, diffs, response
bodies, package scripts, dependency names, or raw sandbox internals.

## Supported Values

`support_status` may be:

- `supported_local_preview`;
- `unsupported`;
- `review_required`.

`network.posture` may be:

- `offline`;
- `operator_managed`;
- `unknown`;
- `review_required`.

`decision.decision` may be:

- `go`;
- `no_go`;
- `review_required`.

The example fixture uses `review_required` because it is evidence for a planned preflight lane, not
proof that any live sandbox is safe.

## Required Warning Labels

The fixture must include these warning labels:

- `not_os_isolation_proof`;
- `operator_managed`;
- `local_preview_only`.

Additional warning labels are allowed only if they are coarse labels and do not describe runtime
authority that Ithildin does not have.

## Current Allowed State

- tool count remains `24`;
- runtime changes allowed: `false`;
- Mission Control runtime allowed: `false`;
- local model invocation allowed: `false`;
- sandbox orchestration allowed: `false`;
- trusted-host promotion allowed: `false`;
- network expansion allowed: `false`;
- new power classes allowed: `false`.

This contract is a preparation step for reviewer confidence only. A later implementation sprint
must still add an implementation decision, focused tests, negative transcripts, source-review
handoff, and release/readiness evidence before any preflight runner exists.
