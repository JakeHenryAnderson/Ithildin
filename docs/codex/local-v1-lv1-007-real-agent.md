# Local v1 LV1-007 Real-Agent Evidence Contract

Status: bounded exact-candidate O2 rehearsal; no release or UAT authority.

This rehearsal closes only the missing current-candidate evidence for `O2`. It runs the already
pinned operator-managed Hermes image against an immutable archive of one clean Git candidate and
the existing local stdio MCP surface.

```sh
make local-v1-real-agent-static-check
make local-v1-real-agent-run
make local-v1-real-agent-check \
  LOCAL_V1_REAL_AGENT_REPORT=var/local-v1-real-agent/<run-id>/local-v1-real-agent.json \
  LOCAL_V1_REAL_AGENT_CANDIDATE=<exact-commit>
```

The live run requires Docker and the pinned `gemma4:e4b` model at the local Ollama endpoint. It
uses synthetic tracked fixtures and does not read `.env`, cloud credentials, ambient Gateway data,
or production state.

## Required observations

The candidate-bound Gateway audit must show all of the following under the fixed local stdio
identity:

- an in-scope directory listing and file read allowed and completed;
- an out-of-scope read denied before execution;
- the fixed HTTP request denied before execution because the fixture has no allowlist; and
- a bounded synthetic artifact write classified `approval_required`, with the approval still
  pending and no write execution.

Hermes prose is discarded. Gateway policy, execution, approval, and audit state are authoritative.
The Hermes process exit is recorded as a runner observation only and does not override complete
Gateway evidence. Ollama availability is a model-provider dependency observation only.

## Boundaries

The harness builds from `git archive` of the recorded candidate, starts one uniquely named
candidate-specific container, mounts only its private synthetic evidence directory plus the tracked
read-only Hermes configuration, and removes that exact container and image. It never mounts the
Docker socket into Ithildin or Hermes. It grants no generic container control, API change, new
governed tool, new power, production authority, release acceptance, or UAT completion.

The final mode-`0600` report contains candidate identity, booleans, counts, truth-source labels, and
non-claims only. It excludes model output, prompts, fixture bodies, approval/request IDs, raw run
identity, environment values, and credentials. All private runtime evidence and the extracted
candidate tree are removed before success is recorded.
