# Track B Ithildin Node Capability Decision

Status: **approved for the limited local-preview enrollment and identity vertical slice described
here**. Broader Track B execution remains gated.

Decision date: 2026-07-16

Decision authority: the project owner explicitly authorized autonomous, project-related evolution
toward a serious enterprise agent-governance product and requested that work continue until a
genuine external decision or meaningful UAT is required. This record is the separate explicit
implementation decision anticipated by the legacy capability report. It does not rewrite or close
historical `external_pending` source-review rows.

Current governed tool count: `24`.

## Approved First Slice

The first Ithildin Node runtime slice may add control-plane APIs and local-preview persistence for:

1. short-lived, one-time enrollment codes issued by an authenticated local administrator;
2. a closed Node descriptor containing safe labels, an Ed25519 public key, and a descriptor hash;
3. server-derived `node_id`, `principal_id`, and session identity;
4. signed heartbeat requests with timestamp and nonce replay protection;
5. admin-only Node inventory, detail, and revocation;
6. append-only audit events containing safe identifiers, hashes, decisions, and posture labels;
7. Command Center display of authoritative enrollment/revocation state and observed connectivity.

This slice may use the existing SQLite local-preview backend and existing `cryptography`, FastAPI,
Pydantic, and standard-library dependencies. It must not add a dependency or governed tool.

## Explicitly Not Approved In This Slice

- remote MCP hosting or forwarding governed tool calls over the Node transport;
- shell execution, Docker socket access, container or process lifecycle control;
- arbitrary filesystem, network, browser, Kubernetes, or endpoint-management powers;
- model inference proxying, prompt or chain-of-thought capture;
- production identity, multi-tenant authorization, runtime Postgres, hosted telemetry, or SIEM;
- automatic policy rollout, artifact promotion, sandbox orchestration, or compliance automation;
- claims of filesystem non-bypass, endpoint isolation, runner health, or production security.

## Authority Boundary

The legacy `capability-expansion-gate` remains a historical global gate and is expected to report
blocked while its matrix contains historical `external_pending` rows. This decision is narrower:
it authorizes only the named enrollment and identity slice. Any tool execution through the Node,
mission dispatch, policy distribution, lifecycle control, remote deployment, or stronger isolation
claim requires a subsequent slice decision backed by the relevant contracts and negative evidence.

## Required Evidence Before Slice Closure

- enrollment codes are stored only as digests, expire, and are consumed once;
- a Node identity is derived by the Gateway and cannot be selected by the enrolling caller;
- valid signatures succeed and invalid signatures, stale timestamps, unknown Nodes, revoked Nodes,
  and replayed nonces fail closed;
- heartbeat bodies cannot change identity or authority;
- restart preserves enrollment, revocation, and replay state;
- admin output and audit output exclude enrollment codes and private keys;
- the 24-tool manifest lock and policy parity remain unchanged;
- focused tests, release checks, source review, and a synthetic observed POC pass.

Implementation and test evidence are evidence only. They do not approve the next Track B slice,
production deployment, public security positioning, or regulated-data use.
