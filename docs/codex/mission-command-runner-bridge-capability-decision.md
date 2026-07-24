# MCC-007 Fixed Hermes Runner-Bridge Capability Decision

Status: `combined_implementation_candidate_pending_exact_review`

Current governed tool count: `24`.

Implementation, runtime-adapter, runner-lifecycle, release, and UAT authority remain false. The
prior exact decision review does not cover this combined candidate. The revised decision, code,
deployment overlay, tests, and evidence checker require one new exact-candidate review and a
post-review authorization record before any live execution may be prepared.

## Closed Product Decision

Select one operator-installed and operator-started Hermes profile for Local-v1 `O4`. It uses the
reviewed Hermes Agent v0.18.2 OCI index, the repo-owned packaged
`ithildin_mcp_server.node_bridge`, and exactly three no-argument local affordances:
`mission.step.1`, `mission.step.2`, and `mission.complete`. The Node resolves the two server-owned
governed reads from the signed Gateway delivery envelope and polls signed mission control before
each read and completion. Runner completion remains runner-reported only; it does not establish
model correctness, output quality, provider completion, or process exit.

The runner cannot choose a tool, workspace, path, argument, mission, endpoint, image, command,
environment, provider, model, or prompt. There is no automatic claim, handoff, operation,
reassignment, finalization, or ambiguity retry. The current governed surface remains 24 tools.

## Established Compose And Identity Topology

`deploy/hermes-node-bridge/compose.yaml` is only an overlay for
`deploy/docker-compose.yml`. It reuses that project's Gateway, default network, Node service, and
`ithildin-node-state` volume; it is not an independent project.

- The enrolled Node remains UID:GID `10002:10002` with supplemental group `20000`.
- The runner remains UID:GID `10000:10000` with supplemental group `20000`.
- The Node creates `mission-socket/` within its existing state volume as `10002:20000` mode
  `0770`, and binds a mode-`0660` socket there.
- The runner mounts only volume subpath `mission-socket`, read-only, at `/run/ithildin-node`.
  It never mounts the state-volume root or receives the Node private key.
- The Node binds through an open parent-directory descriptor and verifies the socket owner, group,
  type, and mode. Linux `SO_PEERCRED` UID `10000` plus the profile digest admits the peer.
- No TCP or public listener exists. A malicious process already running as the admitted UID is not
  excluded: the same-UID host/container process remains inside the local host TCB.
- The operator's base-plus-overlay start uses Compose `--wait` against the fixed Node socket
  healthcheck before creating the runner container, so the isolated volume subpath exists first.

## Resource, Custody, And Lifecycle Ceiling

The runner has a read-only root filesystem, Docker logging driver `none`, no persistent session or
data volume, no configured environment values, no Docker socket, no host process namespace, no
privileged mode, and two UID-bound `128 MiB` tmpfs mounts. Kernel `RLIMIT_FSIZE` enforces the
`16 MiB` per-file ceiling. It has no persistent session or data volume. The pinned image build
requires its existing `/usr/bin/timeout`; the
fixed container-init entrypoint runs exactly Hermes for 900 seconds, then sends `TERM` and, after
ten seconds, `KILL`. If that binary is absent, the build fails closed. This fixed operator-selected
init wrapper is not an Ithildin runner lifecycle API.

The Node profile requires `--max-cycles 1`. Before any Gateway claim, it descriptor-opens and
owner/mode-checks the receipt parent and refuses if any receipt leaf already exists, including a
terminal receipt. Its receipt create, read, update, and replace operations remain parent-descriptor
relative, no-follow, owner-bound, mode `0600`, and fsync-backed. Restart ambiguity therefore causes
zero new claim requests. A same-UID host actor remains part of the stated TCB; no kernel-grade host
isolation or filesystem non-bypass claim is made.

The operator owns teardown and deletion. The exact profile container and tmpfs must be absent before
another separately authorized run. A crash or failed removal blocks retry. Ithildin never updates,
starts, stops, kills, or inspects Hermes.
Ithildin does not enforce or claim provider-network non-bypass.

## Evidence Truth

The evidence assembler consumes owner-bound, mode-`0600`, descriptor-relative receipts only. `O4`
requires exactly one Gateway-correlated Agent Run with:

- `authority=gateway_agent_run_evidence`;
- `correlation_basis=gateway_validated_claim_session`;
- `rejected_correlation_count=0`; and
- two closed operation bindings for `project.structure.summary` and `project.test.summary`, each
  bound to the same mission ID, claim ID, envelope digest, mission session, and Agent Run.

The Node receipt and Gateway run evidence do not prove raw runner behavior, model output, reasoning,
provider state, or non-bypass. Evidence retains closed IDs, digests, indexes, codes, timestamps, and
the Gateway correlation fields only. It does not retain prompts, tool-result bodies, model output,
credentials, or crash content.

Build evidence records clean-source observations before and after both builds, candidate commit and
tree, source and lock digests, OCI index and platform digest, profile digest, image digests,
platform, SBOM digest, and license receipt digest. Node and runner must bind the same candidate
commit and tree; this is the same candidate commit and tree invariant. Upgrade and rollback remain
operator actions.

## Review And Stop Lines

This combined candidate is implementation-pending-review, not authorized runtime. Exact review must
cover the decision, authorization disposition, Node client/service/bridge, MCP bridge, Compose
overlay, fixed profile, evidence assembler/checker, tests, and honest Local-v1 status wording.

Stop if the implementation needs a twenty-fifth tool, policy/manifest/API/schema/dependency/package
change, dynamic tool selection, arbitrary input, public listener, Node/admin/provider credentials in
the runner, broad host mount, automatic ambiguity retry, generic process control, or runner/provider
state represented as Gateway truth. Live Hermes, Docker lifecycle, provider access, `O4` evidence,
release, promotion, production, and UAT authority remain false. Sol Ultra remains prohibited
without prior user approval.

<!-- mission-command-runner-bridge-decision:start -->
{
  "document_type": "runner_bridge_capability_decision",
  "schema_version": "1",
  "ticket_id": "MCC-007",
  "decision": "fixed_hermes_node_bridge_combined_candidate_pending_exact_review",
  "tool_count": 24,
  "capability_selected": true,
  "implementation_authorized": false,
  "runtime_adapter_authorized": false,
  "runner_bridge_authorized": false,
  "runner_lifecycle_authority": false,
  "model_provider_authority": false,
  "prompt_output_evidence_custody_authorized": false,
  "arbitrary_host_control_authorized": false,
  "generic_process_control_authorized": false,
  "shell_execution_authorized": false,
  "docker_socket_authorized": false,
  "network_non_bypass_claimed": false,
  "filesystem_non_bypass_claimed": false,
  "node_private_key_shared": false,
  "api_admin_token_shared": false,
  "provider_credential_shared": false,
  "gateway_api_change_authorized": false,
  "gateway_schema_change_authorized": false,
  "policy_change_authorized": false,
  "manifest_change_authorized": false,
  "new_governed_tool": false,
  "node_tcp_listener_authorized": false,
  "automatic_ambiguity_retry_authorized": false,
  "production_identity_authorized": false,
  "release_allowed": false,
  "production_promotion_allowed": false,
  "uat_complete": false,
  "sol_ultra_authorized": false,
  "candidate_evaluation_sha256": "sha256:9aa24b794d23a072409ee99b9bbe282ae3a89b4c34775fc3c08dea5dcf8f00c1",
  "candidate_evaluation_review_sha256": "sha256:81d0ac9c1a93cee414097b27ca6e6f6f97b341b4057b4e14258bacceee6fb24e",
  "hermes_oci_index_digest": "sha256:6705aac1f41c5faca559858611ce696b760d858b73fa3b51be11599c73ba1ffc",
  "hermes_version": "0.18.2 (2026.7.7.2)",
  "hermes_upstream_commit": "0512f06a",
  "hermes_platform_digests": {
    "linux/amd64": "sha256:48420b0abcf18f9f33cfa1da4c4e8bbd4ad107a0ddc52e5fb3ebb34a9fd20149",
    "linux/arm64": "sha256:bca5bafd0292bdf0d4b4b975780e96c0ec9e428e08941a87aacddb116663ce13"
  },
  "bridge_source_identity": "repo_owned_ithildin_mcp_server_node_bridge_same_candidate",
  "bridge_entrypoint": [
    "/opt/ithildin/.venv/bin/python",
    "-m",
    "ithildin_mcp_server.node_bridge"
  ],
  "bridge_arguments": [],
  "model_provider": "custom",
  "model_base_url": "http://host.docker.internal:11434/v1",
  "model_name": "gemma4:e4b",
  "allowed_environment_names": [],
  "working_directory": "/opt/data/scratch",
  "governed_tools": [
    "project.structure.summary",
    "project.test.summary"
  ],
  "bridge_affordances": [
    "mission.step.1",
    "mission.step.2",
    "mission.complete"
  ],
  "local_protocol": "unix_domain_socket_canonical_json_v1",
  "compose_base": "deploy/docker-compose.yml",
  "compose_overlay": "deploy/hermes-node-bridge/compose.yaml",
  "gateway_network": "established_compose_default_network",
  "node_state_volume": "ithildin-node-state",
  "node_state_volume_subpath": "mission-socket",
  "runner_start_gate": "node_unix_socket_healthcheck_then_operator_compose_wait",
  "node_uid": 10002,
  "node_gid": 10002,
  "runner_uid": 10000,
  "runner_gid": 10000,
  "shared_socket_gid": 20000,
  "node_socket_path": "/var/lib/ithildin-node/mission-socket/mission.sock",
  "runner_socket_path": "/run/ithildin-node/mission.sock",
  "socket_parent_mode": "0770",
  "socket_mode": "0660",
  "peer_identity": "linux_so_peercred_uid_10000_plus_profile_digest",
  "state_mode": "0600",
  "state_fields": [
    "mission_id",
    "claim_id",
    "envelope_digest",
    "next_operation_index",
    "handoff_nonce_digest",
    "last_closed_status"
  ],
  "max_frame_bytes": 16384,
  "operation_timeout_seconds": 120,
  "mission_wall_time_seconds": 900,
  "concurrency": 1,
  "cpu_limit": 2,
  "memory_mib": 4096,
  "pids_limit": 256,
  "tmpfs_mib": 256,
  "per_file_mib": 16,
  "per_file_enforcement": "kernel_rlimit_fsize",
  "wall_time_enforcement": "fixed_container_init_timeout",
  "node_max_cycles": 1,
  "writable_disk_mib": 256,
  "runner_root_filesystem_read_only": true,
  "runner_writable_tmpfs": {
    "/opt/data/scratch": {
      "mib": 128,
      "mode": "0700"
    },
    "/tmp": {
      "mib": 128,
      "mode": "0700"
    }
  },
  "runner_persistent_session_volume": false,
  "runner_logging_driver": "none",
  "runner_raw_logging_allowed": false,
  "runner_memory_enabled": false,
  "runner_verbose_enabled": false,
  "plaintext_lifetime_seconds": 900,
  "cleanup_owner": "operator_profile_teardown",
  "cleanup_evidence_fields": [
    "profile_digest",
    "runner_image_digest",
    "node_image_digest",
    "read_only_root",
    "logging_driver",
    "tmpfs_limits",
    "container_absent",
    "persistent_profile_volume_absent"
  ],
  "failed_cleanup_blocks_retry": true,
  "build_identity_fields": [
    "candidate_commit",
    "candidate_tree",
    "clean_before_bridge_build",
    "clean_after_bridge_build",
    "clean_before_node_build",
    "clean_after_node_build",
    "bridge_source_digest",
    "node_source_digest",
    "dependency_lock_digest",
    "hermes_oci_index_digest",
    "hermes_platform_digest",
    "profile_digest",
    "bridge_image_digest",
    "node_image_digest",
    "platform",
    "sbom_digest",
    "license_receipt_digest"
  ],
  "same_candidate_equality_fields": [
    "candidate_commit",
    "candidate_tree"
  ],
  "o4_harness_identity_binding_required": true,
  "profile_input_source": "operator_fixed_immutable_image_profile",
  "prompt_custody": "operator_fixed_profile_only_not_gateway_evidence",
  "ambiguity_policy": "no_automatic_retry_reassignment_or_finalization",
  "cancellation_facts": [
    "gateway_cancel_requested",
    "node_cancel_observed",
    "bridge_receipt",
    "runner_acknowledgment",
    "process_exit",
    "runner_reported_canceled"
  ],
  "evidence_fields": [
    "mission_id",
    "claim_id",
    "envelope_digest",
    "profile_digest",
    "operation_index",
    "handoff_nonce_digest",
    "closed_receipt_code",
    "closed_reason_code",
    "observed_at"
  ],
  "implementation_paths": [
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
  "exact_candidate_review_required": true,
  "post_review_authorization_required": true
}
<!-- mission-command-runner-bridge-decision:end -->
