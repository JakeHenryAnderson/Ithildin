FROM nousresearch/hermes-agent@sha256:6705aac1f41c5faca559858611ce696b760d858b73fa3b51be11599c73ba1ffc

USER root
WORKDIR /opt/ithildin

COPY pyproject.toml uv.lock README.md ./
COPY apps ./apps
COPY packages ./packages
COPY tool-manifests ./tool-manifests
COPY tool-manifests.lock.json ./
COPY policies ./policies
COPY principals ./principals
COPY deploy/hermes-poc ./deploy/hermes-poc

RUN uv sync --frozen --no-dev \
    && mkdir -p /opt/ithildin/var/hermes-poc/db /opt/ithildin/var/hermes-poc/logs \
    && chown -R 10000:10000 /opt/ithildin

WORKDIR /opt/data/scratch
