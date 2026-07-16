# Track B Ithildin Node Architecture

Status: approved architecture for the limited local-preview enrollment and identity slice.

Current governed tool count: `24`.

## Purpose

Ithildin Node is the deployable identity and enforcement boundary that will eventually sit beside an
external agent. The first slice establishes who the Node is and whether the Gateway has recently
observed it. It does not yet carry governed tool calls or control the runner.

```text
local administrator -> Ithildin API -> one-time enrollment code digest
Ithildin Node        -> enrollment  -> Gateway-derived Node and principal identity
Ithildin Node        -> signed heartbeat -> nonce/timestamp/signature verification
Command Center       -> admin read APIs -> authoritative enrollment and observed connectivity
```

## Trust Zones

- **Gateway:** authoritative for Node identity, enrollment status, revocation, nonce consumption,
  and last accepted heartbeat.
- **Node:** owns its Ed25519 private key and reports only closed descriptor and heartbeat fields.
- **Runner:** is not trusted as identity authority and is not controlled in this slice.
- **Command Center:** displays Gateway records; it does not infer model or runner health.
- **Model provider:** remains outside Ithildin inference custody and observation.

## Enrollment Protocol

1. A local administrator requests a random, short-lived enrollment code.
2. The Gateway stores `sha256(code)` with expiry and unused status; the code is returned once.
3. The Node generates an Ed25519 key pair locally and submits the code, public key, and a closed
   descriptor.
4. The Gateway validates and atomically consumes the code, creates `node_<random>`, derives
   `principal_id = agent:node.<node_id>`, records the descriptor hash, and returns safe identity
   labels. Caller-supplied Node or principal identifiers are forbidden.
5. Reuse, expiration, malformed keys, unsafe labels, or descriptor drift fails closed.

The enrollment response is not a bearer credential. The private key never crosses into Ithildin.

## Signed Request Contract

Each Node request supplies:

- `X-Ithildin-Node`: the assigned Node identifier;
- `X-Ithildin-Timestamp`: UTC Unix seconds;
- `X-Ithildin-Nonce`: a random 128-bit-or-stronger lowercase hexadecimal nonce;
- `X-Ithildin-Signature`: base64 Ed25519 signature.

The signed canonical message is:

```text
ITHILDIN-NODE-V1\n
METHOD\n
PATH\n
TIMESTAMP\n
NONCE\n
SHA256_BODY
```

The Gateway rejects timestamps outside the configured skew, malformed fields, invalid signatures,
unknown or revoked Nodes, and a `(node_id, nonce)` already persisted. Nonce insertion and heartbeat
update occur in one SQLite transaction. Authentication derives the principal from the stored Node;
the body cannot supply or override identity.

## Heartbeat Contract

The closed body contains protocol version, Node software version, runner adapter label, deployment
topology label, configuration digest, and an optional current mission correlation label. It excludes
hostnames, usernames, IP addresses, environment variables, raw paths, prompts, model output, and
secrets.

Gateway state distinguishes:

- `enrolled`: durable administrative state;
- `revoked`: durable administrative state;
- `observed_connected`: derived from a recently accepted heartbeat;
- `stale`: derived when the last accepted heartbeat exceeds the display threshold;
- `never_observed`: enrolled but no heartbeat accepted.
- `evidence_incomplete`: the state transition was written but its append-only audit event did not
  complete, so further Node transitions fail closed pending explicit recovery.

None of these labels means the runner or model is healthy.

## Failure And Restart Semantics

- Enrollment-code consumption is atomic with Node creation.
- Enrollment-code issuance, Node creation, heartbeat acceptance, and revocation begin with
  `evidence_status = pending`. The API marks the record `complete` only after the corresponding
  audit event is durably appended; pending codes cannot enroll and pending Nodes cannot heartbeat
  or revoke.
- Accepted nonces persist across Gateway restart until their bounded retention window expires.
- Revocation is durable and takes effect before another heartbeat can be accepted.
- Re-registration requires a new code and creates a new identity; it does not resurrect a revoked
  Node.
- Clock disagreement fails closed and is reported as authentication failure without echoing signed
  content or secret material.

## Deployment Posture

The first observed POC is local-preview and synthetic-only. HTTP transport may bind only to a loopback
or isolated local container network. Signatures provide authentication and integrity, not transport
confidentiality. Remote deployment and TLS or mTLS are later, separately gated slices.

## Non-Claims

This architecture does not establish filesystem non-bypass, sandbox isolation, endpoint monitoring,
remote MCP, mission orchestration, policy distribution, lifecycle control, production identity, or
Tanium-equivalent fleet management. It establishes the identity and authenticated-connectivity
foundation required before those claims can be designed honestly.
