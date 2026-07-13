# Hermes Governance POC Deployment

Status: operator-managed Track A compatibility fixture. This is not an enforcement node.

The image is pinned to Hermes Agent v0.18.2 (`upstream 0512f06a`) through the reviewed OCI index
digest. Ithildin does not start Docker or Hermes; the operator runs these commands.

```sh
make hermes-poc-image
make hermes-poc-config-check
make hermes-poc-run
uv run python scripts/hermes_poc_evidence_check.py
make hermes-poc-stop
```

The local Ollama endpoint must be available at `host.docker.internal:11434` with
`gemma4:e4b`. The POC uses the base model because the local fallback derivative's authored system
prompt prohibits direct tool use. No cloud model credential is required. The configuration also
waits up to ten seconds for the containerized stdio server to publish its tool schemas before the
first inference request. The repeatable run uses Hermes's normal single-query chat path because its
special `--oneshot` fast path can snapshot tools before a containerized stdio server finishes
discovery.

Known limitation: the current stdio MCP process runs inside the Hermes container, so the synthetic
workspace is also visible to Hermes's local process. Toolset filtering directs the evidence run to
Ithildin but is not a non-bypass boundary. Do not use this topology with sensitive data.

The POC mounts no Docker socket, runs the Hermes binary directly as UID/GID `10000` instead of
starting the image's root supervisor, drops all Linux capabilities, sets `no-new-privileges`, and
uses only synthetic fixture data. `make hermes-poc-stop` stops containers but preserves ignored
evidence under `var/hermes-poc`; deletion remains an explicit operator action.

`uv run python scripts/hermes_poc_evidence_check.py` accepts only database and audit evidence for allowed reads,
out-of-root and HTTP denials, a durable approval, one bound write, replay denial, fixed stdio
identity, and a valid audit chain. Its highest claim is `governed_surface_enforced`; it cannot
promote Track A to filesystem non-bypass or managed-runner evidence.
