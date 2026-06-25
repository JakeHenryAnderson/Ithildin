# Sandbox/VM Static Profile Negative Fixtures

Status: fixture-contract negative cases only.

This document defines rejected sandbox/VM static profile fixture shapes for the future read-only
preflight lane. It does not add runtime behavior, API endpoints, MCP tools, executors, tool
manifests, policy rules, local model invocation, Mission Control runtime behavior, VM/container
lifecycle control, Docker socket access, Kubernetes control, browser automation, shell execution,
arbitrary HTTP, broad filesystem writes, trusted-host promotion, SIEM adapters, production identity,
runtime Postgres, hosted telemetry, plugin SDK behavior, compliance automation, public
security-product claims, or new governed tool powers.

Validate these negative fixture expectations with:

```sh
make sandbox-vm-static-profile-negative-fixtures-check
```

## Fixture Source

The positive seed fixture is:

```text
docs/codex/fixtures/sandbox-vm-static-profile.local-preview.example.json
```

The negative fixtures mutate that seed in memory. They do not write runtime artifacts, inspect host
workspace contents, call Mission Control, invoke a model, start a VM, start a container, run shell,
or promote artifacts.

## Required Rejections

A future static profile preflight implementation must reject or mark `review_required` for these
fixture families before treating a profile as usable local-preview evidence:

| Fixture ID | Mutation | Expected outcome |
| --- | --- | --- |
| `SANDBOX-PROFILE-NEG-001` | missing `schema_version` | reject as unsupported schema |
| `SANDBOX-PROFILE-NEG-002` | unsupported `schema_version` | reject as unsupported schema |
| `SANDBOX-PROFILE-NEG-003` | unknown top-level section | reject as closed-schema violation |
| `SANDBOX-PROFILE-NEG-004` | missing required warning label | reject as missing warning state |
| `SANDBOX-PROFILE-NEG-005` | `support_status: supported_local_preview` before implementation | reject as support overclaim |
| `SANDBOX-PROFILE-NEG-006` | raw host path-shaped mount label | reject as raw path leak |
| `SANDBOX-PROFILE-NEG-007` | `network.broad_network_access: true` | reject as network overclaim |
| `SANDBOX-PROFILE-NEG-008` | `decision.promotion_status` changed away from `not_promoted` | reject as promotion overclaim |
| `SANDBOX-PROFILE-NEG-009` | `decision.decision: go` before implementation | reject as readiness overclaim |
| `SANDBOX-PROFILE-NEG-010` | `ithildin_starts_vm: true` | reject as VM lifecycle overclaim |
| `SANDBOX-PROFILE-NEG-011` | `ithildin_has_docker_socket: true` | reject as Docker authority overclaim |
| `SANDBOX-PROFILE-NEG-012` | `ithildin_has_kubernetes_control: true` | reject as Kubernetes authority overclaim |
| `SANDBOX-PROFILE-NEG-013` | `ithildin_runs_shell: true` | reject as shell authority overclaim |
| `SANDBOX-PROFILE-NEG-014` | `mission_control_executes_actions: true` | reject as Mission Control authority overclaim |
| `SANDBOX-PROFILE-NEG-015` | `local_model_invoked: true` | reject as model invocation overclaim |
| `SANDBOX-PROFILE-NEG-016` | `trusted_host_promotion_enabled: true` | reject as trusted-host promotion overclaim |
| `SANDBOX-PROFILE-NEG-017` | malformed `network.posture` | reject as unsupported network posture |
| `SANDBOX-PROFILE-NEG-018` | injected secret-like field | reject as sensitive payload shape |

## Safe Error Expectations

Negative fixture validation should report stable reason labels only. It must not echo file contents,
raw prompts, raw host paths, environment values, tokens, private keys, package script values,
response bodies, VM disk paths, Docker socket paths, Kubernetes contexts, usernames, home
directories, model outputs, or stack traces.

## Current Implementation Boundary

This is an Ithildin-side fixture contract and validation aid. It does not implement a profile
loader, preflight runner, Mission Control importer, local model invocation, sandbox orchestration,
VM/container lifecycle management, trusted-host promotion, broad network access, SIEM adapter, or
production/security-product posture.
