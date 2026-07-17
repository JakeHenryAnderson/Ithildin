# Track B Node Service Lifecycle Implementation Plan

Status: approved bounded implementation plan.

Current governed tool count: `24`.

## Milestones

1. Add one-cycle synchronization that reloads the enrolled identity, verifies the desired signed
   configuration, persists any trust promotion first, stores the generation atomically,
   acknowledges `stored_not_enforced`, and sends a signed heartbeat.
2. Add a long-running CLI loop with graceful termination, signed-configuration cadence, bounded
   exponential retry, safe JSON posture, and a deterministic cycle limit for testing only.
3. Add stdin-only noninteractive enrollment for container initialization. Reject an empty code and
   never accept the code through a command argument or environment variable.
4. Add an unprivileged Node Dockerfile and optional Compose profile with a read-only root, private
   state volume, no inbound port, no Docker socket, no capabilities, and `no-new-privileges`.
5. Cover successful synchronization, mode-0600 persistence, retry bounds, restart reuse,
   unavailable Gateway, revoked Node, and unchanged 24-tool surface.
6. Run a live Docker proof: enroll one synthetic Node, assign signed configuration, run a cycle,
   stop and replace the container while preserving state, observe an operator-managed version
   change and rollback, restart the Gateway, and verify revocation denial and the audit chain.
7. Record exact nonclaims and run focused checks, `make release-check`, and
   `make review-candidate` before treating the checkpoint as complete.

## Stop Conditions

Stop if the slice requires package transfer, self-update, service-manager APIs, runner invocation,
arbitrary host access, Docker socket access, remote transport, production identity, a schema or
tool-count change, or any claim stronger than the observed evidence.
