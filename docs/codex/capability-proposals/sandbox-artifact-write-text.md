# Capability Proposal: sandbox.artifact.write_text

Status: design-only proposal. Implementation is blocked until a later explicit implementation gate.

`sandbox.artifact.write_text` is the proposed minimal write capability for the Hello World sandbox
demo. It is a bounded text-artifact creation lane for operator-approved sandbox or staging roots. It
is not shell execution, broad filesystem write, patch apply, VM control, Mission Control runtime
behavior, or host promotion.

## Intended Use

The first intended task is:

```text
create sandbox://hello-demo/hello.txt with content Hello World
```

The tool should create agent-owned text artifacts inside a configured sandbox/staging root and
return secret-free evidence about what was created.

## Proposed Input Shape

```json
{
  "workspace_id": "demo",
  "sandbox_id": "local-demo-sandbox",
  "root": ".",
  "relative_path": "hello-demo/hello.txt",
  "content": "Hello World\n",
  "create_parent_directories": true,
  "overwrite": false,
  "idempotency_key": "mission-run-action-id"
}
```

Input constraints:

- `workspace_id` and `sandbox_id` must resolve to trusted local configuration.
- `root` and `relative_path` must be relative and workspace/sandbox confined.
- `content` is UTF-8 text only.
- content size is capped.
- `overwrite` defaults to false and requires separate approval semantics before it can ever be true.
- unknown fields are rejected.

## Proposed Output Shape

```json
{
  "status": "created",
  "workspace_id": "demo",
  "sandbox_id": "local-demo-sandbox",
  "artifact_label": "sandbox://hello-demo/hello.txt",
  "parent_created": true,
  "bytes_written": 12,
  "content_sha256": "sha256:...",
  "created_artifact_id": "artifact_...",
  "output_policy": {
    "content_returned": false,
    "raw_host_path_returned": false,
    "promotion_performed": false
  }
}
```

The response must not include raw host paths, file contents, prompts, model chain-of-thought,
secrets, environment values, shell output, VM logs, or unrelated directory listings.

## Policy And Approval

This proposal is a new write-adjacent power class and must require:

- explicit implementation gate;
- manifest review;
- policy fixture coverage;
- policy preview/runtime parity for a future `sandbox_artifact` resource type;
- approval binding for non-idempotent writes;
- audit metadata with hashes and labels only;
- source-review handoff before broader use.

Initial implementation should be restricted to demo/local-preview principals and operator-approved
sandbox or staging roots.

## Audit Evidence

Audit metadata should include:

- tool name;
- principal ID;
- workspace ID;
- sandbox ID;
- resource type;
- artifact label;
- proposal/action hash;
- content hash;
- bytes written;
- parent-created flag;
- overwrite flag;
- approval ID when required;
- policy hash;
- manifest hash;
- output-policy keys.

Audit metadata must not include file contents, raw host paths, secrets, prompts, response bodies, or
VM/shell output.

## Negative Cases

The executor must deny or safely fail:

- path traversal;
- absolute path;
- encoded traversal or ambiguous path;
- control characters;
- hidden path;
- `.git` path;
- symlink target or ancestor;
- hardlink target ambiguity;
- directory target;
- unsupported encoding;
- oversized content;
- overwrite without explicit approval;
- host write without promotion;
- missing sandbox profile;
- disabled workspace;
- unknown or disabled principal;
- model request for shell, Docker, Kubernetes, browser automation, or arbitrary filesystem access.

## Non-Goals

This proposal does not approve:

- shell execution;
- Docker socket access;
- Kubernetes tools;
- browser automation;
- arbitrary HTTP;
- broad filesystem writes/deletes/moves/chmod/archive extraction;
- VM/container lifecycle control;
- Mission Control runtime behavior;
- automatic host promotion;
- production identity;
- runtime Postgres;
- hosted telemetry;
- remote MCP hosting;
- plugin SDK behavior;
- SIEM adapters;
- compliance automation;
- public/security-product positioning.
