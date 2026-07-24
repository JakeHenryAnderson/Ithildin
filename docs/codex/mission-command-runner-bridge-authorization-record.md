# MCC-007 Fixed Hermes Runner-Bridge Authorization Record

Status: `approved_for_bounded_code_implementation`

Current governed tool count: `24`.

This record authorizes only the code, tests, deployment profile, evidence harness, and supporting
product-control updates named by the exact reviewed MCC-007 decision. It does not authorize a live
Hermes run, Docker/container lifecycle actions, O4 evidence execution, release, promotion,
production use, or UAT completion.

## Authority Basis

The user directed Ithildin toward a bounded Local v1.0 candidate for a security-conscious power
user and authorized routine in-repository product and technical work until genuine UAT, a critical
trust issue, an external dependency, or an irreversible product decision. The Local-v1 contract
requires the fixed constrained mission seam for `O4`.

That standing direction is applied only after the separate MCC-007 capability-decision sequence:

- design-only candidate evaluation exact review: `GO`, zero findings;
- rejected decision candidate `f9036be5db4e79cf3716096d892d3f1a05add163`: `NO-GO`, three Medium
  findings;
- repaired decision candidate `43d39456a8034528ed0a189b715c3fac213589b2`: `GO`, zero findings; and
- packaging-safe exact decision candidate `6cc8a4f1f9deceee231b185cf0d7f0acd63bb313`:
  `GO`, zero Critical, High, Medium, or Low findings.

The final reviewed candidate tree is `542f6d3b146b8bb5fa07f7cd73f80329d6de8ab6`. The reviewed capability
decision SHA-256 is `3edb0ce71c01e9e3763a622642ab531b64bfa1d001575e9cad9a601f05101b98`.

## Authorized Code Boundary

Implementation may change only the reviewed runtime, deployment, test, and evidence paths:

- `apps/node/src/ithildin_node/client.py`
- `apps/node/src/ithildin_node/service.py`
- `apps/node/src/ithildin_node/fixed_runner_bridge.py`
- `apps/mcp-server/src/ithildin_mcp_server/node_bridge.py`
- `deploy/hermes-node-bridge/`
- `tests/test_node_client.py`
- `tests/test_node_service.py`
- `tests/test_node_fixed_runner_bridge.py`
- `tests/test_node_mcp_bridge.py`
- `tests/test_api_service.py`
- `scripts/local_v1_constrained_mission_journey.py`
- `scripts/local_v1_constrained_mission_journey_check.py`
- `tests/test_local_v1_constrained_mission_journey.py`

Supporting product-control changes may touch the MCC-007 decision/authorization/checker records,
their focused tests, Make target wiring, Local-v1 contract/golden-path status, README, and docs-site
navigation. They do not add runtime power.

The implementation may add closed signed Node methods for existing mission endpoints, one
configuration-current mission-cycle branch, the reviewed fixed Unix-socket protocol, the packaged
no-argument MCP bridge, exclusive-owner closed receipt state, the pinned operator-managed profile,
and synthetic evidence generation/checking code. It must reuse the existing two governed read
tools, Gateway APIs, mission schema, policy, dependencies, and package mapping.

## Explicitly Unauthorized

No change is authorized to:

- `pyproject.toml`, `uv.lock`, Gateway runtime/API/schema/migrations, policies, tool manifests, or
  the 24-tool lock;
- public listeners, Node TCP/HTTP transport, remote MCP, generic runner/plugin SDKs, dynamic tool
  selection, free-form prompts, arbitrary commands/paths/environment/provider/model inputs, or
  broad host mounts;
- Node private-key, Gateway-admin-token, provider-credential, prompt, model-output, or reasoning
  custody in the runner/bridge evidence surface;
- runner start/stop/kill/update/retry, Docker socket, Kubernetes, SSH, browser automation, shell or
  generic process control, filesystem/network non-bypass claims, or model-provider authority; or
- live Hermes execution, Docker/container lifecycle, O4 evidence collection, production identity,
  release, promotion, production use, or UAT completion.

If an implementation owner needs any unauthorized path or power, implementation stops and returns
to capability review. A clean exact implementation candidate must pass focused, Local-v1,
Mission Command, policy/tool-surface, release, and independent Sol xhigh review before a separate
live-evidence authorization can be recorded. Sol Ultra remains prohibited without prior user
approval.

<!-- mission-command-runner-bridge-authorization:start -->
{"document_type":"runner_bridge_authorization_record","schema_version":"1","ticket_id":"MCC-007","decision":"bounded_code_implementation_authorized","tool_count":24,"authority_source":"user_local_v1_to_uat_direction_and_standing_delegation","reviewed_candidate_commit":"6cc8a4f1f9deceee231b185cf0d7f0acd63bb313","reviewed_candidate_tree":"542f6d3b146b8bb5fa07f7cd73f80329d6de8ab6","decision_sha256":"sha256:3edb0ce71c01e9e3763a622642ab531b64bfa1d001575e9cad9a601f05101b98","review_disposition":"GO","critical_findings":0,"high_findings":0,"medium_findings":0,"low_findings":0,"code_implementation_authorized":true,"runtime_adapter_code_authorized":true,"runner_bridge_code_authorized":true,"live_hermes_execution_authorized":false,"docker_lifecycle_authorized":false,"o4_evidence_execution_authorized":false,"runner_lifecycle_authority":false,"model_provider_authority":false,"prompt_output_evidence_custody_authorized":false,"arbitrary_host_control_authorized":false,"generic_process_control_authorized":false,"shell_execution_authorized":false,"docker_socket_authorized":false,"network_non_bypass_claimed":false,"filesystem_non_bypass_claimed":false,"gateway_api_change_authorized":false,"gateway_schema_change_authorized":false,"policy_change_authorized":false,"manifest_change_authorized":false,"dependency_change_authorized":false,"package_mapping_change_authorized":false,"new_governed_tool":false,"production_identity_authorized":false,"release_allowed":false,"production_promotion_allowed":false,"uat_complete":false,"sol_ultra_authorized":false,"allowed_runtime_paths":["apps/node/src/ithildin_node/client.py","apps/node/src/ithildin_node/service.py","apps/node/src/ithildin_node/fixed_runner_bridge.py","apps/mcp-server/src/ithildin_mcp_server/node_bridge.py","deploy/hermes-node-bridge","tests/test_node_client.py","tests/test_node_service.py","tests/test_node_fixed_runner_bridge.py","tests/test_node_mcp_bridge.py","tests/test_api_service.py","scripts/local_v1_constrained_mission_journey.py","scripts/local_v1_constrained_mission_journey_check.py","tests/test_local_v1_constrained_mission_journey.py"],"forbidden_runtime_paths":["pyproject.toml","uv.lock","apps/api/src/ithildin_api","policies","tool-manifests","tool-manifests.lock.json"],"exact_implementation_review_required":true,"separate_live_evidence_authorization_required":true}
<!-- mission-command-runner-bridge-authorization:end -->
