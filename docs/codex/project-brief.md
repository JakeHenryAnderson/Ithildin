# Codex Project Brief

## Objective

Build Ithildin as a local-first governed MCP/tool gateway.

The first release should prove governance, not autonomy.

## MVP Definition

An MCP-capable agent can:

1. list permitted tools;
2. read approved workspace files;
3. inspect git status/diff;
4. propose a patch;
5. receive an approval-required response for writes;
6. apply an approved patch;
7. leave complete audit evidence.

## Architecture

```text
MCP client
  -> Ithildin gateway
  -> schema validation
  -> policy evaluation
  -> approval state machine
  -> scoped tool execution
  -> audit writer
```

## Guardrails

- Deny unknown tools, principals, resources, and policy outcomes.
- Canonicalize paths before policy decisions.
- Block private/link-local destinations for HTTP tools.
- Do not implement shell execution in the MVP.
- Do not mount broad user directories.
- Do not mount the Docker socket.
- Treat audit write failure as execution-blocking.

## Build Order

1. Scaffold the monorepo and developer tooling.
2. Define schemas.
3. Implement API skeleton and config.
4. Add manifest registry.
5. Add policy evaluator.
6. Add audit writer.
7. Add approval workflow.
8. Add MCP adapter.
9. Add read-only filesystem/git tools.
10. Add patch proposal and approved patch apply.
