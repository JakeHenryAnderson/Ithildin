# Trusted Host Descriptor Contract

Status: design-only descriptor contract for `ERG-005` and `PRD-TRUSTED-HOST-001`.

Current governed tool count: `24`.

Current `ERG-005` status: `blocked`.

Current selected capability: `not selected`.

This contract defines the minimum secret-free host descriptor evidence Ithildin may use for
trusted-host promotion planning. It does not approve runtime behavior, host writes, host registry
mutation, automatic host enrollment, VM/container lifecycle management, sandbox orchestration,
Mission Control runtime authority, local model invocation, shell, Docker/Kubernetes/browser
governed powers, arbitrary HTTP, broad filesystem writes, production identity, runtime Postgres,
hosted telemetry, SIEM adapters, compliance automation, public/security-product positioning, or
trusted-host promotion.

Validate this descriptor contract with:

```sh
make trusted-host-descriptor-contract-check
```

The descriptor contract is a prerequisite evidence layer for the existing
[trusted-host-promotion-zone-contract.md](trusted-host-promotion-zone-contract.md) and
[trusted-host-promotion-implementation-plan.md](trusted-host-promotion-implementation-plan.md). It
answers what kind of operator-reviewed host posture evidence may be referenced before any future
runtime promotion plan is considered.

## Descriptor Meaning

For local preview, a trusted host descriptor means:

- an operator-reviewed local evidence record describing a host posture;
- a planning input for later review packets;
- a warning and support-status source for future operator UI or packet text;
- a stable descriptor ID that can be cited by future design documents.

It does not mean:

- the host is secure;
- the host is remotely attested;
- Ithildin may control the host;
- Ithildin may write to host-managed locations;
- Ithildin may start, stop, inspect, or orchestrate a VM or container;
- Mission Control may act as a runtime authority;
- a sandbox/VM POC is approved;
- any production or compliance claim is approved.

## Required Descriptor Fields

Future descriptor evidence must be stable, secret-free, and normalized:

```json
{
  "schema_version": "1",
  "descriptor_id": "thd_local_preview_macos_example",
  "host_label": "local-preview-host",
  "operator_reviewed": true,
  "review_status": "operator_review_required",
  "support_status": "supported_local_preview",
  "os_family": "macos",
  "architecture": "arm64",
  "filesystem_profile": {
    "case_sensitivity": "case_insensitive",
    "nofollow_supported": true,
    "symlink_supported": true,
    "hardlink_supported": true
  },
  "workspace_posture": {
    "workspace_id": "demo_workspace",
    "mount_root_label": "workspace://demo",
    "sandbox_id": "sandbox_descriptor_only",
    "sandbox_runtime_control": false,
    "host_write_allowed": false
  },
  "warning_state": {
    "warnings": ["descriptor_only"],
    "operator_notes_present": true
  },
  "evidence_timestamp": "2026-07-04T00:00:00Z",
  "source": "operator-local-descriptor"
}
```

Allowed `os_family` values are `macos` and `linux` for security-supported local-preview claims.
`windows`, `wsl`, and unknown profiles must be reported as unsupported/untested for workspace and
race-security claims until separately reviewed.

Allowed `support_status` values are:

- `supported_local_preview`;
- `unsupported_untested`;
- `operator_review_required`.

Allowed `review_status` values are:

- `operator_review_required`;
- `operator_reviewed_for_planning`;
- `rejected`.

## Forbidden Descriptor Fields

Descriptor evidence must not contain:

- secrets, tokens, private keys, credentials, cookies, or bearer tokens;
- raw environment variables, environment names, or environment values;
- usernames, home directories, raw host paths, or raw sandbox-internal paths;
- process lists, open files, shell history, shell output, stack traces, or VM logs;
- network interface details, IP addresses, hostnames beyond a coarse operator label, or routing
  details;
- file contents, prompts, diffs, response bodies, model outputs, dependency names, package script
  values, registry URLs, database DSNs, or remote service endpoints;
- arbitrary destination paths, absolute paths, parent traversal, encoded traversal, URL-shaped host
  paths, Unicode ambiguity, or control characters.

## Accepted Descriptor Fixture

The contract check validates a tiny accepted fixture with:

- `operator_reviewed: true`;
- `support_status: supported_local_preview`;
- `os_family: macos`;
- `host_write_allowed: false`;
- `sandbox_runtime_control: false`;
- descriptor-only warning state;
- no forbidden fields.

## Rejected Descriptor Fixture

The contract check validates a rejected fixture that includes forbidden sensitive evidence such as
raw host paths, environment variables, process lists, network interface details, and host-write
claims. Any future implementation or review packet that needs those fields must stop and request a
new product-boundary decision before continuing.

## Relationship To ERG-004

ERG-004 descriptor-only work may cite a trusted host descriptor only as planning evidence. A
descriptor does not approve live VM/container inspection, lifecycle control, sandbox orchestration,
local model invocation, Mission Control runtime behavior, host writes, or trusted-host promotion.

Before an ERG-004 live runtime POC can resume, ERG-005 must provide a reviewed descriptor contract
and a later decision record must still approve the exact live-runtime surface.

## Current Output Flags

Current outputs must continue to report:

- decision record required: `true`;
- implementation approved: `false`;
- runtime changes allowed: `false`;
- trusted-host promotion allowed: `false`;
- direct host writes allowed: `false`;
- host registry mutation allowed: `false`;
- automatic host enrollment allowed: `false`;
- VM/container lifecycle allowed: `false`;
- Mission Control runtime allowed: `false`;
- local model invocation allowed: `false`;
- sandbox orchestration allowed: `false`;
- SIEM adapter allowed: `false`;
- new power classes allowed: `false`;
- public/security-product positioning allowed: `false`.
