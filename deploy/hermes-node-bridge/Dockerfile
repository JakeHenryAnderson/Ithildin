FROM nousresearch/hermes-agent@sha256:6705aac1f41c5faca559858611ce696b760d858b73fa3b51be11599c73ba1ffc AS bridge-build

WORKDIR /src
COPY pyproject.toml uv.lock README.md ./
COPY apps ./apps
COPY packages ./packages
ENV UV_PROJECT_ENVIRONMENT=/opt/ithildin/.venv
RUN /usr/bin/python3 -c \
        "import sys; assert sys.version_info >= (3, 12), sys.version" \
    && uv sync --frozen --no-dev --no-editable --python /usr/bin/python3 \
    && test "$(readlink -f /opt/ithildin/.venv/bin/python)" = \
        "$(readlink -f /usr/bin/python3)" \
    && chmod -R a+rX /opt/ithildin/.venv \
    && /opt/ithildin/.venv/bin/python -c \
        "import sys; assert sys.prefix == '/opt/ithildin/.venv'; import ithildin_mcp_server.node_bridge, ithildin_schemas"

FROM nousresearch/hermes-agent@sha256:6705aac1f41c5faca559858611ce696b760d858b73fa3b51be11599c73ba1ffc

RUN test -x /usr/bin/timeout

USER 0:0

COPY --from=bridge-build /opt/ithildin/.venv /opt/ithildin/.venv
COPY deploy/hermes-node-bridge/profile.json /opt/ithildin/profile.json
COPY deploy/hermes-node-bridge/fixed-instruction.md /opt/ithildin/fixed-instruction.md
COPY deploy/hermes-node-bridge/config.yaml /opt/data/config.yaml

RUN mkdir -p /opt/data/scratch \
    && chmod -R a+rX /opt/ithildin/.venv \
    && chmod a+rX /opt/ithildin /opt/data \
        /opt/ithildin/profile.json /opt/ithildin/fixed-instruction.md \
        /opt/data/config.yaml \
    && chown 10000:10000 /opt/data/scratch \
    && chmod 0700 /opt/data/scratch

WORKDIR /opt/data/scratch
USER 10000:10000
RUN test -x /opt/ithildin \
    && test -x /opt/ithildin/.venv \
    && test -x /opt/ithildin/.venv/bin \
    && test -x /opt/ithildin/.venv/bin/python \
    && test -x /opt/data \
    && test -x /opt/data/scratch \
    && test -w /opt/data/scratch \
    && test -r /opt/ithildin/profile.json \
    && test -r /opt/ithildin/fixed-instruction.md \
    && test -r /opt/data/config.yaml \
    && /opt/ithildin/.venv/bin/python -c \
        "import sys; assert sys.version_info >= (3, 12); assert sys.prefix == '/opt/ithildin/.venv'; assert __import__('os').path.realpath(sys.executable) == __import__('os').path.realpath('/usr/bin/python3'); import ithildin_mcp_server.node_bridge, ithildin_schemas"
ENTRYPOINT ["/opt/hermes/.venv/bin/hermes"]
