# v3 project.config.summary Implementation Decision

Status: approved_limited_read_only runtime implementation.

This record approves the narrow runtime implementation boundary for `project.config.summary`.
It may add one tool manifest, one executor dispatch path, schema/policy/audit parity wiring, tests,
and source-review handoff artifacts. Runtime behavior is bounded read-only.

## Approved Boundary

- tool name: `project.config.summary`;
- risk `read`;
- category `project`;
- resource type `project_config`;
- input fields: `workspace_id`, `root`, `max_depth`, `limit`, and `include_categories`;
- output boundary: count-only config posture metadata and allowlisted labels only;
- allowed output sections: `config_category_counts`, `config_location_counts`, and
  `skipped_counts`.

The implementation may summarize broad config posture by allowlisted filename/category mappings. It
must not parse config values, execute config tools, call package managers, inspect registries, or
use network access.

## Required Non-Goals

The implementation must preserve:

- no config file names;
- no raw paths;
- no raw recursive listing;
- no file contents;
- no config contents;
- no config values;
- no dependency names;
- no package names;
- no package script names or values;
- no environment names or values;
- no registry URLs;
- no config parser execution;
- no command discovery;
- no command output;
- no shell;
- no package-manager execution;
- no registry/network access;
- no broad filesystem writes;
- no deployment-readiness, sandbox, SIEM, compliance, SBOM, vulnerability, or secret-scanning
  claims.

## Evidence Requirements

The implementation must add:

- strict JSON Schema with `additionalProperties: false`;
- policy preview/runtime parity for resource type `project_config`;
- safe audit metadata with counts and section keys only;
- executor tests for traversal, hidden/sensitive paths, `.git`, symlink, hardlink, malformed input,
  truncation, and suppressed sensitive output;
- governed-call tests for policy allow/deny and safe audit metadata;
- a focused source-review handoff bundle.

## Gate

Run:

```bash
make project-config-summary-implementation-gate
```

Broader capability expansion remains blocked. This decision does not approve shell execution,
Docker socket access, Kubernetes tools, browser automation, arbitrary HTTP, broad filesystem
writes, production identity, runtime Postgres, hosted telemetry, remote MCP, sandbox orchestration,
SIEM adapters, plugin SDK work, compliance automation, or public/security-product claims.
