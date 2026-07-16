# Track B Ithildin Node Configuration Capability Decision

Status: **approved for the limited local-preview signed configuration distribution and
acknowledgment slice described here**. Governed action forwarding and runner control remain gated.

Decision date: 2026-07-16

Decision authority: the project owner explicitly authorized autonomous project-related evolution
toward a serious enterprise agent-governance product. This is the subsequent slice decision
required by the enrollment/identity packet. It does not rewrite or close historical
`external_pending` review rows.

Current governed tool count: `24`.

## Approved Slice

The Gateway and Ithildin Node may add:

1. a dedicated local Ed25519 configuration-signing keypair, separate from Node, audit, and
   manifest-lock keys;
2. immutable, monotonically increasing configuration generations targeted to one Gateway-derived
   Node identity and its assigned workspace;
3. a closed configuration payload binding policy version/digest, the exact manifest-lock digest,
   minimum Node version, heartbeat interval, offline posture, and evidence-buffer bound;
4. authenticated Node retrieval using the existing signed request and durable nonce contract;
5. client-side signature, key-id, target, digest, generation, and time-window verification before
   crash-safe local storage;
6. a signed Node acknowledgment that reports only `stored_not_enforced` for the exact generation
   and digest;
7. append-only audit evidence and Command Center desired-versus-stored drift visibility.

This slice may use existing SQLite, `cryptography`, FastAPI, Pydantic, and standard-library
dependencies. It must not add a governed tool or dependency.

## Explicitly Not Approved

- forwarding or executing governed tool calls through the Node;
- claiming that a stored configuration is applied or enforced by Hermes or another runner;
- shell, process, Docker, Kubernetes, browser, filesystem, credential, or endpoint control;
- automatic group rollout, remote MCP, remote deployment, TLS/mTLS, or production identity;
- rollback execution, self-update, binary/package distribution, or runner lifecycle control;
- prompt, model-output, chain-of-thought, hostname, username, IP, raw-path, or secret collection;
- filesystem non-bypass, isolation, runner-health, compliance, or production-security claims.

## Required Evidence

- the configuration signing trust root is distinct and its private key never reaches a Node;
- a bundle is rejected for a wrong key, Node, workspace, generation, digest, time window, or
  manifest-lock digest;
- retrieval requires an enrolled, active Node and consumes replay state durably;
- acknowledgments cannot select another Node or acknowledge a non-current generation/digest;
- assignment and acknowledgment fail closed when audit evidence is incomplete;
- restart preserves desired, stored, drift, revocation, and replay state;
- Command Center distinguishes Gateway desired state, Node-reported storage, and unknown
  enforcement/runner health;
- the governed tool count remains 24 and policy parity remains 24/24.

Tests and generated evidence remain evidence only. They do not approve action-path enforcement,
production rollout, group policy, upgrade execution, or broader security claims.
