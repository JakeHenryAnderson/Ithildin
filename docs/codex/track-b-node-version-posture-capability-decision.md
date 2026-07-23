# Track B Node Version Posture Capability Decision

Status: **approved for bounded local-preview implementation** under the project owner's continuing
enterprise-governance goal.

Current governed tool count: `24`.

## Decision

Ithildin may derive and display one enrolled Node's software-version posture by comparing:

- the `minimum_node_version` in that Node's current, immutable, signed desired configuration; and
- the `node_version` in the latest Gateway-accepted, Node-signed heartbeat.

The accepted version grammar is a closed `MAJOR.MINOR.PATCH` form with non-negative decimal
components and no prerelease, build, wildcard, range, or caller-defined comparison syntax. The
Gateway owns the comparison and returns a closed posture label. Command Center displays that label
and both source values without inventing package or process health.

This slice may observe an operator-managed upgrade or rollback only after a later signed heartbeat
reports the changed version. The observation is evidence that the Node asserted a version and the
Gateway accepted the signed request. It is not evidence that Ithildin installed the binary, that the
binary is authentic, or that a runner is healthy.

## Allowed Runtime Change

- Persist the latest reported Node version with the accepted heartbeat transaction.
- Enforce the closed version grammar for new enrollment, heartbeat, and signed configuration input.
- Derive `unassigned`, `never_observed`, `meets_minimum`, `below_minimum`,
  `evidence_incomplete`, or `revoked` from authoritative stored records.
- Return and display current version, minimum version, posture, and explicit source/claim labels.
- Exercise a synthetic operator-managed version change across real signed heartbeats and Gateway
  restart, with safe ignored evidence and negative cases.

## Explicit Non-Approvals

This decision does not approve Node self-update, package download or installation, process restart,
service-manager integration, automatic rollback, fleet rollout, update rings, runner lifecycle
control, binary provenance or signature claims, vulnerability scanning, remote transport,
production identity, production storage, or a new governed tool.

No Node package URL, path, command, argument, environment value, credential, or private key may enter
the API or audit surface. The existing signed desired-configuration rollback remains configuration
rollback only; it does not become software rollback.

## Authority And Evidence

The project-owner authorization for the continuing goal starts this bounded capability sprint. It
does not rewrite or close historical external-review findings, enterprise lanes, release approval,
or UAT acceptance. Tests and generated evidence prove only the local-preview behavior they observe.
