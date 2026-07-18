# Mission Command Control Plane Authorization Record

Status: approved for bounded implementation.

Current governed tool count: `24`.

## Bound Inputs

- Capability decision: `docs/codex/mission-command-control-plane-capability-decision.md`.
- Architecture: `docs/codex/mission-command-control-plane-architecture.md`.
- Implementation tickets: `docs/codex/mission-command-control-plane-implementation-tickets.md`.
- Authorized baseline commit: `314b15979205523968ced42a569e66753c49cc19`.
- Ticket order: `MCC-001` through `MCC-006`.

## Authority

The project owner authorized autonomous project-related progress toward an enterprise-worthy,
self-hostable external-agent governance platform and specifically required an authoritative mission
and fleet Command Center, Node-mediated external-agent work, exact evidence, the 24-tool invariant,
and no arbitrary host control. That standing instruction authorizes the bounded API, persistence,
Node protocol, evidence, and UI work named by these tickets.

It does not authorize a runner bridge, shell/process/container control, production identity,
runtime Postgres, remote MCP, SIEM delivery, compliance automation, public security claims, release,
or UAT acceptance.

## Review Boundary

- One Sol implementation owner makes and reviews code changes.
- Sol xhigh may perform bounded independent read-only trust review.
- Sol Ultra requires separate prior user approval and is not authorized by this record.
- Each implementation ticket receives focused tests before broader exact-candidate gates.
- Tests and generated evidence do not authorize promotion, production use, closure, release, or UAT.

```yaml
decision: approved_for_bounded_implementation
baseline_commit: 314b15979205523968ced42a569e66753c49cc19
first_ticket: MCC-001
runner_bridge_allowed: false
arbitrary_host_control_allowed: false
tool_count: 24
```

The machine-readable contract binds the three reviewed planning inputs by their exact SHA-256
digests. The checker rejects stale or substituted inputs.

<!-- mission-command-contract:start -->
{"document_type":"authorization_record","schema_version":"1","decision":"approved_for_bounded_implementation","baseline_commit":"314b15979205523968ced42a569e66753c49cc19","ordered_tickets":["MCC-001","MCC-002","MCC-003","MCC-004","MCC-005","MCC-006"],"tool_count":24,"capability_decision_sha256":"sha256:a278023398c13b91206ab709cc8183ab6bdaf74fc6bfa776af154c77b537362a","architecture_sha256":"sha256:b61a1a091b84233e119818ed55d4628833cc7ed47cd564a7954a03dc2bba4171","implementation_tickets_sha256":"sha256:ec42310f10928002eb47076efe4687eaf518cc9ac2fe417bb4b219346d064b23","runner_bridge_authorized":false,"arbitrary_host_control_authorized":false,"sol_ultra_authorized":false}
<!-- mission-command-contract:end -->
