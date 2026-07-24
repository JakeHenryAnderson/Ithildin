# MCC-007 Fixed Hermes Runner-Bridge Authorization Record

Status: `combined_candidate_exact_review_required`

Current governed tool count: `24`.

This record does not authorize the current code, deployment profile, evidence harness, Docker
lifecycle, live Hermes/provider access, `O4` evidence, release, promotion, production, or UAT. It
records that the prior code-only authorization does not cover the revised decision and combined
implementation candidate.

It does not authorize a live Hermes run or any container lifecycle action.

## Disposition

The earlier packaging-safe decision candidate
`6cc8a4f1f9deceee231b185cf0d7f0acd63bb313` received `GO` and permitted bounded code
implementation. The first combined implementation candidate later received `NO-GO` with zero
Critical, three High, one Medium, and one Low finding. The decision and implementation have since
changed to repair those findings. Neither the old decision review nor that superseded `NO-GO`
reviews the current candidate.

The current combined candidate is therefore `REVIEW_REQUIRED`. Its exact review scope is the
revised decision, this disposition, Node mission client/service/receipt/socket code, MCP bridge,
established-project Compose overlay, immutable profile, evidence assembler/checker, tests, and
Local-v1 status wording. A `GO` review may support a new candidate-bound code disposition. A
separate record would still be required before any Docker, Hermes, provider, or `O4` execution.

## Closed Boundary

The candidate remains limited to the previously named runtime/test/evidence paths and supporting
product-control files. It reuses the current Gateway API, schema, policy, package mapping,
dependencies, and exactly 24 governed tools. It adds no dynamic tool, arbitrary input, public
listener, generic process control, Docker socket, broad host mount, runner lifecycle API, provider
authority, or non-bypass claim.

If an implementation owner needs any unauthorized path or power, work stops and returns to
capability review. Exact implementation review and a later live-evidence authorization remain
mandatory. Sol Ultra remains prohibited without prior user approval.

<!-- mission-command-runner-bridge-authorization:start -->
{
  "document_type": "runner_bridge_authorization_record",
  "schema_version": "1",
  "ticket_id": "MCC-007",
  "decision": "combined_candidate_exact_review_required",
  "tool_count": 24,
  "authority_source": "user_local_v1_to_uat_direction_and_standing_delegation",
  "previous_reviewed_candidate_commit": "6cc8a4f1f9deceee231b185cf0d7f0acd63bb313",
  "previous_reviewed_candidate_tree": "542f6d3b146b8bb5fa07f7cd73f80329d6de8ab6",
  "previous_decision_sha256": "sha256:3edb0ce71c01e9e3763a622642ab531b64bfa1d001575e9cad9a601f05101b98",
  "current_decision_sha256": "sha256:2a5792c80b672e9e44b24e9ef1e7201990386c90c89e496f17ac2073e04efc72",
  "review_disposition": "REVIEW_REQUIRED",
  "superseded_candidate_critical_findings": 0,
  "superseded_candidate_high_findings": 3,
  "superseded_candidate_medium_findings": 1,
  "superseded_candidate_low_findings": 1,
  "code_implementation_authorized": false,
  "runtime_adapter_code_authorized": false,
  "runner_bridge_code_authorized": false,
  "live_hermes_execution_authorized": false,
  "docker_lifecycle_authorized": false,
  "o4_evidence_execution_authorized": false,
  "runner_lifecycle_authority": false,
  "model_provider_authority": false,
  "prompt_output_evidence_custody_authorized": false,
  "arbitrary_host_control_authorized": false,
  "generic_process_control_authorized": false,
  "shell_execution_authorized": false,
  "docker_socket_authorized": false,
  "network_non_bypass_claimed": false,
  "filesystem_non_bypass_claimed": false,
  "gateway_api_change_authorized": false,
  "gateway_schema_change_authorized": false,
  "policy_change_authorized": false,
  "manifest_change_authorized": false,
  "dependency_change_authorized": false,
  "package_mapping_change_authorized": false,
  "new_governed_tool": false,
  "production_identity_authorized": false,
  "release_allowed": false,
  "production_promotion_allowed": false,
  "uat_complete": false,
  "sol_ultra_authorized": false,
  "allowed_runtime_paths": [
    "apps/node/src/ithildin_node/client.py",
    "apps/node/src/ithildin_node/service.py",
    "apps/node/src/ithildin_node/fixed_runner_bridge.py",
    "apps/mcp-server/src/ithildin_mcp_server/node_bridge.py",
    "deploy/hermes-node-bridge",
    "tests/test_node_client.py",
    "tests/test_node_service.py",
    "tests/test_node_fixed_runner_bridge.py",
    "tests/test_node_mcp_bridge.py",
    "tests/test_api_service.py",
    "scripts/local_v1_constrained_mission_journey.py",
    "scripts/local_v1_constrained_mission_journey_check.py",
    "tests/test_local_v1_constrained_mission_journey.py"
  ],
  "forbidden_runtime_paths": [
    "pyproject.toml",
    "uv.lock",
    "apps/api/src/ithildin_api",
    "policies",
    "tool-manifests",
    "tool-manifests.lock.json"
  ],
  "exact_implementation_review_required": true,
  "separate_live_evidence_authorization_required": true
}
<!-- mission-command-runner-bridge-authorization:end -->
