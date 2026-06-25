# Sandbox/VM Static Preflight Implementation Decision

Status: CLI-only implementation boundary approved; runtime runner not yet implemented.

This decision approves only a local CLI script and Make target that validate a static
operator-managed sandbox/VM profile fixture and emit a secret-free preflight report. It does not
approve an API endpoint, MCP tool, governed executor, policy rule, Mission Control runtime behavior,
local model invocation, VM/container lifecycle control, sandbox orchestration, trusted-host
promotion, SIEM adapter, production identity, runtime Postgres, hosted telemetry, plugin SDK
behavior, compliance automation, public/security-product positioning, or new governed tool power.

Validate this decision with:

```sh
make sandbox-vm-static-preflight-implementation-gate
```

## Approved Implementation Shape

The future runner may be implemented as:

- `scripts/sandbox_vm_static_preflight.py`;
- `make sandbox-vm-static-preflight`;
- a deterministic local CLI that reads a JSON fixture path;
- a secret-free report with coarse labels, warning labels, safe reasons, and false authority flags.

The runner may read only the supplied fixture file and repo-local validation helpers. It must not
inspect a live VM, container, host mount, sandbox filesystem, Docker socket, Kubernetes context,
Mission Control runtime, local model, network endpoint, shell, browser profile, or trusted-host
promotion path.

## Required Output Boundary

The report must be a closed object containing only:

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

Allowed decisions are `go`, `no_go`, and `review_required`. Reasons must be safe snake-case labels.

## Required Denials

The runner must fail closed or return `no_go`/`review_required` for:

- missing required sections;
- unsupported schema versions;
- unknown top-level fields;
- raw path-shaped mount/root labels;
- broad network posture;
- missing `not_os_isolation_proof`, `operator_managed`, or `local_preview_only` warnings;
- Mission Control execution authority claims;
- local model invocation claims;
- Docker socket, Kubernetes, shell, browser, or arbitrary HTTP authority claims;
- trusted-host promotion claims;
- malformed JSON;
- oversized fixtures.

## Non-Leak Requirements

The runner output and errors must not include raw host paths, VM disk paths, usernames, home
directories, secrets, environment variables, model prompts, model outputs, command lines, shell
output, Docker socket paths, Kubernetes contexts, browser profiles, network credentials, file
contents, diffs, response bodies, package scripts, dependency names, or raw sandbox internals.

## Current Decision Flags

- tool count remains `24`;
- governed tool surface changes allowed: `false`;
- API/MCP behavior changes allowed: `false`;
- policy rule changes allowed: `false`;
- runtime sandbox control allowed: `false`;
- Mission Control runtime allowed: `false`;
- local model invocation allowed: `false`;
- sandbox orchestration allowed: `false`;
- trusted-host promotion allowed: `false`;
- network expansion allowed: `false`;
- new power classes allowed: `false`;
- CLI-only fixture preflight runner allowed: `true`;

Broader capability expansion remains blocked.
