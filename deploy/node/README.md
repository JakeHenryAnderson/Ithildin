# Ithildin Node Local-Preview Service

Status: bounded operator-managed deployment fixture. This is not a production endpoint agent.

The image runs only Ithildin Node's signed configuration and heartbeat loop. It does not start,
stop, inspect, invoke, or update Hermes or another runner. It exposes no port and receives no
Docker socket, host process namespace, host filesystem mount, or package-install authority.

## Build And Enroll

Start the local-preview API and create a one-time Node enrollment code through Command Center or
the authenticated API. Then build the image and pipe the code through stdin:

```sh
make node-service-image
printf '%s\n' "$ONE_TIME_CODE" | docker compose -f deploy/docker-compose.yml \
  --profile node run --rm -T ithildin-node enroll \
  --api-url http://ithildin-api:8000 \
  --state /var/lib/ithildin-node/state.json \
  --node-version 0.1.0 \
  --runner-adapter hermes \
  --deployment-topology docker_sidecar \
  --enrollment-code-stdin
```

The code is consumed once and is not stored in the Node state. Avoid shell history expansion or
command arguments containing the code; the environment variable above is illustrative shell-local
input, not a container environment variable.

Assign a signed per-Node configuration from Command Center before starting the service:

```sh
docker compose -f deploy/docker-compose.yml --profile node up -d ithildin-node
docker compose -f deploy/docker-compose.yml --profile node logs -f ithildin-node
```

## Operator-Managed Upgrade Or Rollback

Build or select the intended reviewed image, stop the old container, and recreate the service while
retaining the `ithildin-node-state` volume. A later signed heartbeat may report the version selected
by the operator. Ithildin does not fetch, verify, install, start, stop, or roll back the image.

```sh
ITHILDIN_NODE_VERSION=0.2.0 docker compose -f deploy/docker-compose.yml \
  --profile node up -d --force-recreate ithildin-node
```

This demonstrates identity and configuration continuity only. It does not prove artifact
provenance, installation correctness, runner health, policy enforcement, production transport, or
production readiness.

## Local Signed Artifact Selection

For a clean-checkout operator build, use the dedicated release-artifact workflow before replacing
the service:

```sh
make node-release-image NODE_RELEASE_VERSION=0.1.0
make node-release-artifact-keygen
make node-release-artifact-sign NODE_RELEASE_VERSION=0.1.0
make node-release-artifact-verify NODE_RELEASE_VERSION=0.1.0
```

Verification binds the explicitly selected local image to an immutable image ID, clean Git commit,
locked-input digests, version/revision labels, unprivileged user, fixed Node entrypoint, and zero
exposed ports. Rollback means verifying the previously approved image and manifest, then having the
operator replace the container.

This remains local operator evidence. It is not a registry, image transfer mechanism, updater,
remote attestation, reproducible-build proof, vulnerability assessment, official supply-chain
signature, Gateway enforcement, or permission for Ithildin to control Docker.
