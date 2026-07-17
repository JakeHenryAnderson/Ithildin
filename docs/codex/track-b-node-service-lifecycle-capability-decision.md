# Track B Node Service Lifecycle Capability Decision

Status: **approved for bounded local-preview supervised Node synchronization and
operator-managed container lifecycle**.

Decision date: 2026-07-16

Current governed tool count: `24`.

## Decision

Ithildin Node may run as a long-lived local-preview control-plane client. Each cycle may load an
already enrolled mode-0600 identity, retrieve and verify the current signed per-Node configuration,
atomically store it, acknowledge only `stored_not_enforced`, and send a Node-signed heartbeat. The
verified configuration's closed heartbeat interval controls the next successful cycle. Transient
failure uses bounded exponential retry and safe status output.

The repository may provide an unprivileged, read-only-root Docker image and an optional Compose
profile for an operator to install, start, stop, replace, or roll back this Node process. The image
mounts a dedicated private state volume, exposes no port, mounts no Docker socket, and receives no
enrollment code through an environment variable or command-line argument. One-time enrollment may
read the code from standard input.

## Required Safety Semantics

- Node and verified configuration files remain regular, non-symlinked mode-0600 files written
  atomically.
- Signing-trust promotion is persisted before the newly trusted configuration becomes the local
  stored generation.
- A successful cycle always records configuration storage before acknowledgment and heartbeat.
- SIGTERM and SIGINT request graceful loop shutdown. Restart reloads durable identity and
  configuration state rather than enrolling a replacement identity.
- A nonblocking mode-0600 lease beside the private state prevents two local service processes from
  concurrently using the same persisted Node identity.
- Retry output contains bounded error categories and posture only; it contains no private key,
  enrollment code, configuration payload, package path, command, credential, or response body.
- The container runs without root, capabilities, writable root filesystem, inbound port, Docker
  socket, or host process namespace.

## Explicit Non-Approvals

This decision does not approve Node self-update, package download, package authenticity claims,
automatic software rollback, update rings, group rollout, service-manager control, arbitrary
command execution, shell execution, runner lifecycle control, runner invocation, policy
enforcement at the Node, filesystem non-bypass, Docker socket access, Kubernetes behavior, remote
MCP, production identity, TLS or mTLS, production storage, SIEM behavior, compliance automation,
or a new governed tool.

An operator replacing a container and a later signed heartbeat reporting another version prove
only process restart continuity and an accepted Node assertion. They do not prove which artifact
was installed, its provenance, vulnerability posture, runner health, or enforcement.

Tests and generated evidence are evidence only. They do not authorize production deployment,
promotion, release, UAT acceptance, or public security-product claims.
