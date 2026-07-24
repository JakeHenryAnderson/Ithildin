FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim@sha256:e5b65587bce7de595f299855d7385fe7fca39b8a74baa261ba1b7147afa78e58 AS bridge-build

WORKDIR /src
COPY pyproject.toml uv.lock README.md ./
COPY apps ./apps
COPY packages ./packages
RUN uv sync --frozen --no-dev --no-editable \
    && mkdir -p /opt/ithildin \
    && cp -a /src/.venv /opt/ithildin/.venv

FROM nousresearch/hermes-agent@sha256:6705aac1f41c5faca559858611ce696b760d858b73fa3b51be11599c73ba1ffc

RUN test -x /usr/bin/timeout

COPY --from=bridge-build /opt/ithildin/.venv /opt/ithildin/.venv
COPY deploy/hermes-node-bridge/profile.json /opt/ithildin/profile.json
COPY deploy/hermes-node-bridge/fixed-instruction.md /opt/ithildin/fixed-instruction.md
COPY deploy/hermes-node-bridge/config.yaml /opt/data/config.yaml

WORKDIR /opt/data/scratch
USER 10000:10000
RUN /opt/ithildin/.venv/bin/python -c \
    "import ithildin_mcp_server.node_bridge, ithildin_schemas"
ENTRYPOINT ["/opt/hermes/.venv/bin/hermes"]
