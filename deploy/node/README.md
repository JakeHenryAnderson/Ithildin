# Ithildin Node Local-Preview Service

Status: bounded operator-managed deployment fixture. This is not a production endpoint agent.

The image runs only Ithildin Node's signed configuration and heartbeat loop. It does not start,
stop, inspect, invoke, or update Hermes or another runner. It exposes no port and receives no
Docker socket, host process namespace, host filesystem mount, or package-install authority.

## Initialize Signing Trust Before API Startup

Node enrollment requires an operator-owned configuration-signing trust root. Check the ignored
local key paths before starting the API:

```sh
make node-configuration-signing-status
```

If the result says `"configured": false`, create the keypair once:

```sh
make node-configuration-keygen
make node-configuration-signing-ready
```

Key generation refuses to overwrite either key. The private key is created mode `0600`; the public
key is mode `0644`. Keep both under ignored `var/keys/`, do not use production signing material, and
do not paste either key into Command Center. On Linux, set `ITHILDIN_CONTAINER_UID` and
`ITHILDIN_CONTAINER_GID` in the owner-only `.env` to the operator UID/GID so the unprivileged API
process can read the owner-only private key. Confirm ownership and mode without printing key
contents:

```sh
ls -ln var/keys/node-configuration-ed25519-*.pem
```

Then start the normal API/UI stack. An API started without the signer remains usable for non-Node
local-preview work, but enrollment-code issuance and enrollment fail closed until the signer is
initialized and the API is restarted.

## Build And Enroll

Build the optional image and start the normal API/UI stack first:

```sh
make node-service-image
make compose-up
make compose-smoke
```

In Command Center, open **Nodes**, enter a bounded display name, explicitly select an active
workspace, and issue one short-lived code. Command Center keeps the raw value only in that mounted
React component and clears it on dismissal, replacement, navigation away from Nodes, sign-out,
refresh, or page reload. Delayed responses are invalidated when that component loses ownership. It
does not persist, log, export, copy, or generate a shell command containing the code.

In a private, non-recorded terminal, run the fixed stdin-only enrollment target:

```sh
make node-service-enroll
```

Paste exactly one nonempty code line with no leading or trailing whitespace, press Return, then send
EOF. The target uses
`docker compose run --rm -T --no-deps`; the code is not accepted as a Make variable, environment
variable, or command argument. Before reading the code, enrollment atomically reserves the Node
state destination as a mode-`0600` regular file and keeps that exact inode open through enrollment.
An existing regular file, directory, symlink, or competing reservation fails before stdin is read or
the Gateway is contacted. Inspect the safe summary:

```sh
make node-service-status
```

Immediately before possible Gateway contact, the reservation becomes a secret-free
`recovery_required` marker. A lost Gateway response or local finalization failure leaves that marker
in place and blocks blind retry because the remote enrollment outcome is unknown. Use the status
command, inspect the Gateway Node inventory, and revoke any identity that may correspond to the
ambiguous attempt. Only after that revocation may the operator explicitly remove or recreate the
local Node state volume and issue a new code. Ithildin never deletes a nonempty recovery reservation
automatically; known pre-contact input failures clean up only the still-empty reservation created by
that invocation.

Assign a signed per-Node configuration from Command Center, then start the optional service:

```sh
make node-service-up
make node-service-status
```

`node-service-status` emits the client's bounded safe summary. There is intentionally no onboarding
logs target because raw container logs are not part of the secret-safe operator contract.

Stop only the optional Node service with:

```sh
make node-service-stop
```

## Repeatable Local-v1 Synthetic Journey

For a committed clean candidate, the deliberately live automation wraps the manual enrollment
sequence in a uniquely named, isolated Compose project:

```sh
make local-v1-node-journey
# Then run the exact check command printed by the journey, for example:
make local-v1-node-journey-check \
  LOCAL_V1_NODE_JOURNEY_REPORT=var/local-v1-node-journey/<run-id> \
  LOCAL_V1_NODE_JOURNEY_CANDIDATE=<40-lowercase-hex-commit>
```

The first command requires Docker Compose and free local ports `8000` and `5173`. It generates only
local synthetic credentials under ignored owner-only runtime state, passes the one-time enrollment
code exclusively over stdin to the same fixed `run --rm -T --no-deps` Node path, verifies
Gateway-derived identity and workspace binding, observes signed configuration storage and
acknowledgment plus a Gateway-accepted heartbeat, then stops and revokes the Node and confirms a
subsequent signed heartbeat is rejected. The second command reads only the explicitly selected
redacted report under `var/local-v1-node-journey/`, requires the exact expected candidate commit,
and rejects stale evidence; it never searches for a "latest" run or reruns the live sequence.
Owner-only run directories and inode revalidation reduce accidental path substitution, but they are
not a security boundary against a malicious concurrent process running as the same host UID while
the Docker CLI opens a validated path.

Successful cleanup removes only the journey's unique project resources, volume, run-specific Node
image, and isolated state. An ambiguous enrollment retains the isolated runtime and volume for
explicit recovery and blocks any claim of completion. Neither command demonstrates governed tool
execution, a real agent mission, runner or model-provider health, configuration enforcement,
restart/replay/partition behavior, production identity/storage, release, promotion, or UAT.

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
