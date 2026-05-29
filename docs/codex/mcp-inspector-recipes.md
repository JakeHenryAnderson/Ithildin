# MCP Inspector Recipes

These recipes exercise the local stdio MCP adapter through the same governed pipeline used by the
API and review console. They are for local preview only. Ithildin does not add hosted MCP,
production identity, shell access, Docker/Kubernetes tools, browser automation, broad filesystem
writes, or arbitrary network access.

## Prerequisites

Run from the repository root:

```sh
make admin-token-generate
cp .env.example .env
make demo-seed
make mcp-inspector-recipes
```

Paste the generated `ITHILDIN_ADMIN_TOKEN=...` into `.env`, keep the workspace root narrow, and
start the API/UI separately when you want to approve patch apply requests from the review console.

## Stdio Server Configuration

Use this server configuration in MCP Inspector or another local MCP client that supports stdio:

```json
{
  "mcpServers": {
    "ithildin-local": {
      "command": "uv",
      "args": ["run", "python", "-m", "ithildin_mcp_server"],
      "cwd": "/absolute/path/to/Ithildin"
    }
  }
}
```

The MCP adapter reads the same trusted local config as the API: manifests, policy, principal
registry, workspace registry, audit paths, and tool limits. It uses the local MCP principal and only
lists tools allowed for that principal.

## Recipe: List Tools

Call `tools/list`.

Expected result:

- only registered, MCP-exposed tools appear;
- role visibility filters the list;
- no shell, Docker, Kubernetes, browser, or broad-write tools appear.

## Recipe: Allowed Workspace Read

Call `fs.list` with:

```json
{
  "path": ".",
  "workspace_id": "demo"
}
```

Expected result:

- entries are returned from the configured demo workspace;
- hidden, sensitive, and out-of-scope paths remain denied by the executor.

## Recipe: Safe Denial

Call an unknown tool such as `unknown.tool` with `{}`.

Expected result:

- the call is denied safely;
- the response does not expose host internals or sensitive content;
- audit evidence records the denial.

## Recipe: Approval-Required Patch Apply

First call `fs.patch.propose` with a one-file unified diff against a demo workspace file:

```json
{
  "path": "README.md",
  "workspace_id": "demo",
  "unified_diff": "--- README.md\n+++ README.md\n@@ -1 +1 @@\n-demo workspace\n+demo workspace updated\n"
}
```

Expected result:

- a `patch_...` proposal is stored;
- no workspace file is modified by proposal creation.

Then call `fs.patch.apply` with:

```json
{
  "proposal_id": "patch_replace_with_returned_id"
}
```

Expected result:

- the response is `approval_required`;
- safe metadata includes approval ID, request ID, proposal ID/hash, target path, and expiry.

Open the review console, inspect the approval binding evidence, approve it, then call
`fs.patch.apply` again with:

```json
{
  "approval_id": "appr_replace_with_approved_id"
}
```

Expected result:

- the stored proposal applies once;
- replay is denied;
- audit verification remains valid.

## Verify Evidence

After the recipes, run:

```sh
make audit-diagnostics
make release-evidence
```

The diagnostics should explain the audit state without rewriting evidence. The release evidence
should continue to report local-only MCP posture and the current audit head.
