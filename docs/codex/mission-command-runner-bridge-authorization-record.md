# MCC-007 Fixed Hermes Runner-Bridge Authorization Record

Status: `exact_candidate_go_code_only`

Current governed tool count: `24`.

This record authorizes the original exact-reviewed code candidate
`5dab3654391c14fe214a9dfe302c099d0fe5fbf8` plus the seven exact-reviewed repair stages terminating
at authorized runtime tip `8cd307e3ce2ca20e6fdc1b53fc1937bfa5568685` for bounded
runtime-adapter, fixed runner-bridge, constrained-journey assembler, and `O4` producer code use. It
does not authorize Docker lifecycle, live Hermes/provider access, `O4` evidence, release,
promotion, production, or UAT.

It does not authorize a live Hermes run or any container lifecycle action.

## Disposition

The earlier packaging-safe decision candidate received `GO` and permitted bounded code
implementation. The fixed-bridge review lineage was an initial dirty-worktree audit with
`0/3/1/1`, a first exact review with `0/2/1/1`, an exact rereview with `0/0/1/0`, and the final
exact review of `da5fd021bddb48ad663aa0a409da036bc854b516` with `0/0/0/0`.
That historical bridge review remains durable. A later independent `producer_exact_review` of the
frozen producer candidate also returned `0/0/0/0` and `GO`.

Seven later repair stages each received a separate exact review with `0/0/0/0` and `GO`:
Compose correction, runtime-native bridge construction, bounded startup diagnostics, API container
state diagnostics, application-startup stage diagnostics, image runtime readability, and closed
enrollment-output projection. Their exact commits, trees, review-record digests, and cumulative
allowed-runtime delta inventories are bound below. This reconciles the current code-only
authorization to the reviewed runtime lineage; it does not retroactively describe those repairs as
part of the original producer candidate.

The current exact candidate is therefore `GO_CODE_ONLY`. Its reviewed tree is
`f9a0cb66ac12e6e0ecca7fc23a0071be0dbe3075`, its parent is
`7b293a30823b20aef7a32a2f22910b66f822c35f`, and its exact 11-path inventory is bound below. The
durable producer review is `docs/codex/local-v1-lv1-003-o4-producer-exact-review.md`; the earlier
fixed-bridge review remains `docs/codex/local-v1-lv1-003-exact-review.md`. A separate live-evidence
authorization is still required before any Docker, Hermes, provider, or `O4` execution.

## Closed Boundary

The candidate remains limited to the previously named runtime/test/evidence paths and supporting
product-control files. It reuses the current Gateway API, schema, policy, package mapping,
dependencies, and exactly 24 governed tools. It adds no dynamic tool, arbitrary input, public
listener, generic process control, Docker socket, broad host mount, runner lifecycle API, provider
authority, or non-bypass claim.

The authorization checker validates every reviewed repair stage from the original producer
candidate through the authorized runtime tip, including exact Git order, tree, review-record
digest, and allowed-runtime delta inventory. It then compares the current Git index and worktree
directly with authorized runtime tip `8cd307e3ce2ca20e6fdc1b53fc1937bfa5568685` across every allowed
runtime and producer path. The `deploy/hermes-node-bridge` prefix is recursive. Any staged,
unstaged, deleted, renamed, or untracked runtime-path delta invalidates code authority; bounded
post-review control records and their validators may differ.

If an implementation owner needs any unauthorized path or power, work stops and returns to
capability review. The exact implementation review is complete; a later live-evidence authorization
remains mandatory. Sol Ultra remains prohibited without prior user approval.

<!-- mission-command-runner-bridge-authorization:start -->
{
  "document_type": "runner_bridge_authorization_record",
  "schema_version": "1",
  "ticket_id": "MCC-007",
  "decision": "exact_candidate_go_code_only",
  "tool_count": 24,
  "authority_source": "user_local_v1_to_uat_direction_and_standing_delegation",
  "previous_reviewed_candidate_commit": "da5fd021bddb48ad663aa0a409da036bc854b516",
  "previous_reviewed_candidate_tree": "f489dee60235d04eb8bc64cc6bb55e8534db1f8e",
  "previous_decision_sha256": "sha256:2a5792c80b672e9e44b24e9ef1e7201990386c90c89e496f17ac2073e04efc72",
  "previous_review_document": "docs/codex/local-v1-lv1-003-exact-review.md",
  "previous_review_document_sha256": "sha256:3b9bb240810995ce97a963445912e7d0f7431def2e84f590c1e8e60e0e5990c5",
  "current_decision_sha256": "sha256:2a5792c80b672e9e44b24e9ef1e7201990386c90c89e496f17ac2073e04efc72",
  "reviewed_candidate_commit": "5dab3654391c14fe214a9dfe302c099d0fe5fbf8",
  "reviewed_candidate_parent": "7b293a30823b20aef7a32a2f22910b66f822c35f",
  "reviewed_candidate_tree": "f9a0cb66ac12e6e0ecca7fc23a0071be0dbe3075",
  "review_document": "docs/codex/local-v1-lv1-003-o4-producer-exact-review.md",
  "reviewer": "independent GPT-5.6 Sol xhigh",
  "review_disposition": "GO_CODE_ONLY",
  "review_lineage": [
    {"stage": "initial_dirty_audit", "critical": 0, "high": 3, "medium": 1, "low": 1, "disposition": "NO_GO"},
    {"stage": "first_exact_review", "critical": 0, "high": 2, "medium": 1, "low": 1, "disposition": "NO_GO"},
    {"stage": "exact_rereview", "critical": 0, "high": 0, "medium": 1, "low": 0, "disposition": "NO_GO"},
    {"stage": "final_exact_review", "critical": 0, "high": 0, "medium": 0, "low": 0, "disposition": "GO"},
    {"stage": "producer_exact_review", "critical": 0, "high": 0, "medium": 0, "low": 0, "disposition": "GO"}
  ],
  "authorized_runtime_tip_commit": "8cd307e3ce2ca20e6fdc1b53fc1937bfa5568685",
  "authorized_runtime_tip_tree": "4dacc4015a51d61b29dc3e089900b2e12ab1d7b6",
  "authorized_runtime_lineage": [
    {
      "stage": "compose_repair",
      "reviewed_commit": "7e6eb9f0fcad35016f611096543fa4a81017259c",
      "reviewed_tree": "fef080b85db9b44675150954d6af5afd5d6fec0d",
      "review_document": "docs/codex/local-v1-lv1-003-o4-compose-repair-exact-review.md",
      "review_document_sha256": "sha256:3209b958f6a7810e753e0c50dccdd113349faf96d6a9b45329d1966924d009dc",
      "authorized_runtime_delta_paths": [
        "deploy/hermes-node-bridge/compose.yaml",
        "scripts/local_v1_lv1_003_o4_producer.py",
        "tests/test_local_v1_lv1_003_o4_producer.py",
        "tests/test_node_fixed_runner_bridge.py"
      ],
      "critical": 0,
      "high": 0,
      "medium": 0,
      "low": 0,
      "disposition": "GO"
    },
    {
      "stage": "runtime_native_repair",
      "reviewed_commit": "49db93d80a71855d9ae223826a9849749377c376",
      "reviewed_tree": "23950855584316daba76acd65be0bfdfd20fbcb9",
      "review_document": "docs/codex/local-v1-lv1-003-o4-runtime-native-repair-exact-review.md",
      "review_document_sha256": "sha256:635f2e473985f4eef18d541c455ddabb7c09ec782c8c67d37b37da0fbf45e551",
      "authorized_runtime_delta_paths": [
        "deploy/hermes-node-bridge/Dockerfile",
        "scripts/local_v1_lv1_003_o4_producer.py",
        "tests/test_local_v1_lv1_003_o4_producer.py",
        "tests/test_node_fixed_runner_bridge.py"
      ],
      "critical": 0,
      "high": 0,
      "medium": 0,
      "low": 0,
      "disposition": "GO"
    },
    {
      "stage": "diagnostic_repair",
      "reviewed_commit": "dea1e48acb411e9afd3c6e2c777c05c08e0c5386",
      "reviewed_tree": "40e1a7c862b1031dbab1bba9a7f7a30af0beb976",
      "review_document": "docs/codex/local-v1-lv1-003-o4-diagnostic-repair-exact-review.md",
      "review_document_sha256": "sha256:f4307fb338c82b6513228641c9437d08c33c948d05b1689102a574b39e60f716",
      "authorized_runtime_delta_paths": [
        "scripts/local_v1_lv1_003_o4_producer.py",
        "tests/test_local_v1_lv1_003_o4_producer.py"
      ],
      "critical": 0,
      "high": 0,
      "medium": 0,
      "low": 0,
      "disposition": "GO"
    },
    {
      "stage": "api_container_state_diagnostic",
      "reviewed_commit": "3f207b8f390742b956ed62cea674b0e5c557b514",
      "reviewed_tree": "e3bc1d84ab798e34b297b659fa4698003f3423fe",
      "review_document": "docs/codex/local-v1-lv1-003-o4-api-container-state-diagnostic-exact-review.md",
      "review_document_sha256": "sha256:561411e152df0f8f49210ec3380fd39df138a170053c99d48a315a34d498a8d2",
      "authorized_runtime_delta_paths": [
        "scripts/local_v1_lv1_003_o4_producer.py",
        "tests/test_local_v1_lv1_003_o4_producer.py"
      ],
      "critical": 0,
      "high": 0,
      "medium": 0,
      "low": 0,
      "disposition": "GO"
    },
    {
      "stage": "application_startup_stage_diagnostic",
      "reviewed_commit": "cce80b5cc71e9387237d18b588d294c39351a362",
      "reviewed_tree": "4701443cd266cd86d6654a295f6277caddc117f2",
      "review_document": "docs/codex/local-v1-lv1-003-o4-application-startup-stage-diagnostic-exact-review.md",
      "review_document_sha256": "sha256:4d14b14e6fe881b0d1d5487ed7d4e2a84dd671520e7e7c917e7e9e525e6e76b4",
      "authorized_runtime_delta_paths": [
        "scripts/local_v1_lv1_003_o4_producer.py",
        "tests/test_api_service.py",
        "tests/test_local_v1_lv1_003_o4_producer.py"
      ],
      "critical": 0,
      "high": 0,
      "medium": 0,
      "low": 0,
      "disposition": "GO"
    },
    {
      "stage": "image_readability_repair",
      "reviewed_commit": "7cc1da575074895a7210c5f15a34ae136f4f932a",
      "reviewed_tree": "b448eb922619e59af74275cf1070deb33b6813ef",
      "review_document": "docs/codex/local-v1-lv1-003-o4-image-readability-repair-exact-review.md",
      "review_document_sha256": "sha256:3d95c58d0c50d1ae229f0484b3a27cabfaee8d181f39b3285772b54384d0b423",
      "authorized_runtime_delta_paths": [
        "deploy/hermes-node-bridge/Dockerfile"
      ],
      "critical": 0,
      "high": 0,
      "medium": 0,
      "low": 0,
      "disposition": "GO"
    },
    {
      "stage": "enrollment_output_projection_repair",
      "reviewed_commit": "8cd307e3ce2ca20e6fdc1b53fc1937bfa5568685",
      "reviewed_tree": "4dacc4015a51d61b29dc3e089900b2e12ab1d7b6",
      "review_document": "docs/codex/local-v1-lv1-003-o4-enrollment-output-projection-repair-exact-review.md",
      "review_document_sha256": "sha256:79c6ca4354895005c499b1bea8c62e03001fdc63d8a1b5c376f8c956a71005a0",
      "authorized_runtime_delta_paths": [
        "scripts/local_v1_lv1_003_o4_producer.py",
        "tests/test_local_v1_lv1_003_o4_producer.py"
      ],
      "critical": 0,
      "high": 0,
      "medium": 0,
      "low": 0,
      "disposition": "GO"
    }
  ],
  "code_implementation_authorized": true,
  "runtime_adapter_code_authorized": true,
  "runner_bridge_code_authorized": true,
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
    "tests/test_local_v1_constrained_mission_journey.py",
    "scripts/local_v1_lv1_003_o4_producer.py",
    "tests/test_local_v1_lv1_003_o4_producer.py"
  ],
  "forbidden_runtime_paths": [
    "pyproject.toml",
    "uv.lock",
    "apps/api/src/ithildin_api",
    "policies",
    "tool-manifests",
    "tool-manifests.lock.json"
  ],
  "reviewed_path_inventory": [
    "Makefile",
    "README.md",
    "docs/codex/local-v1-lv1-003-o4-execution-authorization.json",
    "docs/codex/local-v1-lv1-003-o4-execution-authorization.md",
    "docs/codex/local-v1-lv1-003-o4-producer-contract.md",
    "scripts/local_v1_constrained_mission_journey.py",
    "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
    "scripts/local_v1_lv1_003_o4_producer.py",
    "tests/test_local_v1_constrained_mission_journey.py",
    "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    "tests/test_local_v1_lv1_003_o4_producer.py"
  ],
  "exact_implementation_review_required": true,
  "exact_implementation_review_complete": true,
  "separate_live_evidence_authorization_required": true
}
<!-- mission-command-runner-bridge-authorization:end -->
