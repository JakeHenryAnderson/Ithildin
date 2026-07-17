# Track B Node Version Posture: Observed Results

Status: observed local-preview POC evidence; not production readiness or UAT approval.

Observed on: `2026-07-16`.

Current governed tool count: `24`.

## Accepted Evidence

A fresh loopback Gateway on `127.0.0.1:8014` used a dedicated SQLite database, signed audit chain,
configuration signing keypair, and one newly enrolled synthetic Hermes Node. The ignored evidence
root is `var/node-version-posture-poc-20260716/` and can be checked without printing enrollment or
private-key material:

```sh
make track-b-node-version-posture-evidence-check
```

The observed run established:

- a signed desired configuration persisted minimum Node version `0.2.0`;
- a Node-signed `0.1.0` heartbeat produced `below_minimum`;
- a later Node-signed `0.2.0` heartbeat produced `meets_minimum`, representing only an
  operator-managed upgrade observation;
- Gateway process restart preserved the `0.2.0` observation and posture;
- a later Node-signed `0.1.0` heartbeat returned to `below_minimum`, representing only an
  operator-managed rollback observation;
- invalid version grammar was rejected with HTTP 400;
- revocation persisted the last accepted `0.1.0` observation and denied later heartbeat traffic;
- three accepted heartbeat events remained in a valid audit chain;
- Node state remained mode `0600`, private material was absent from safe evidence and audit, and
  the manifest remained at 24 governed tools.

## Claim Boundary

The accepted claim is limited to Gateway-derived version-number posture from one signed desired
minimum and the latest accepted Node-signed heartbeat in a local-preview environment.
`meets_minimum` proves only tuple comparison. It does not prove Node self-update, package download
or installation, package authenticity, process restart, runner health, policy enforcement,
vulnerability status, automatic rollback, fleet rollout, production readiness, release approval,
or UAT acceptance.

The operator or service manager performed every implied maintenance action outside Ithildin. No
package URL, path, command, environment value, credential, or private key entered the API or audit
surface.
