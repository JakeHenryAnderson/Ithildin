# MCC-007 Fixed Hermes Runner-Bridge Capability Decision

Status: `selected_pending_exact_review`

Current governed tool count: `24`.

Implementation, runtime-adapter, runner-lifecycle, release, and UAT authority remain false. This
candidate selects a closed Local-v1 shape for exact review; it does not authorize code or a live
Hermes run.

## Product Decision

Select one operator-installed and operator-started Hermes profile for the Local-v1 `O4` mission.
The profile uses the already-reviewed Hermes Agent v0.18.2 OCI index and a repo-owned MCP bridge
built from the same exact Ithildin source candidate as the Node. The bridge is a fixed adapter, not
a generic runner SDK or a twenty-fifth governed tool.

The Gateway already owns mission admission, claim, cancellation decisions, accepted reports,
governed Agent Runs, and audit evidence. The authenticated Node claims one assigned
`synthetic_read_review_v1` mission and offers the runner three no-argument local affordances:

1. request the mission's first server-owned governed read;
2. request the mission's second server-owned governed read; and
3. report that the runner considers its fixed mission complete.

The runner cannot choose a Gateway tool, workspace, path, arguments, mission, Node, endpoint, image,
command, environment, provider, model, or prompt through this adapter. The Node resolves each
operation index from the signed Gateway delivery envelope, polls the signed control decision before
each operation, and makes the existing governed call under its Gateway-derived principal and
workspace. The completion affordance creates only a runner-reported observation; it does not prove
model correctness, output quality, process exit, or provider completion.

## Bound Artifacts And Profile

- Hermes OCI index:
  `nousresearch/hermes-agent@sha256:6705aac1f41c5faca559858611ce696b760d858b73fa3b51be11599c73ba1ffc`
- Hermes version: `0.18.2 (2026.7.7.2)`, upstream `0512f06a`
- `linux/amd64` manifest:
  `sha256:48420b0abcf18f9f33cfa1da4c4e8bbd4ad107a0ddc52e5fb3ebb34a9fd20149`
- `linux/arm64` manifest:
  `sha256:bca5bafd0292bdf0d4b4b975780e96c0ec9e428e08941a87aacddb116663ce13`
- Bridge source identity: repo-owned `ithildin_mcp_server.node_bridge` inside the already-packaged
  MCP server package and from the same exact reviewed implementation candidate as the Node.
- Bridge entrypoint:
  `/opt/ithildin/.venv/bin/python -m ithildin_mcp_server.node_bridge`
- Bridge arguments: none.
- Bridge configuration: one immutable profile document copied into the derived image. No mission
  field, environment value, command argument, or caller input may replace the profile.
- Build evidence must record the candidate commit and Git tree, clean-source observations before
  and after both builds, exact bridge-package and Node-source digests, dependency-lock digest, base
  OCI index and platform manifest, closed-profile SHA-256, Node and derived Hermes/bridge image
  IDs/digests, platform, and SBOM/license receipt before a live journey. The Node and bridge receipts
  must bind the same candidate commit and tree. The `O4` harness must reject a dirty source
  observation, unequal candidate/tree identity, or an image/profile identity that differs from the
  reviewed implementation candidate.
- Upgrade and rollback remain operator actions. A profile or protocol mismatch refuses startup.
  The prior reviewed image/profile remains the rollback artifact; Ithildin never updates, starts,
  stops, kills, or inspects Hermes.

## Local Protocol And Identity

The Node owns one non-listening, local-only Unix-domain socket at the fixed path
`/run/ithildin-node/mission.sock`. The socket and its parent are created with owner-only access and
shared only with the fixed operator profile. No TCP/HTTP listener or remote transport is added.

Protocol v1 uses length-bounded canonical JSON frames. The peer must present the selected profile
digest and match Linux `SO_PEERCRED` UID `10000`. This is local profile admission, not protection
against a malicious process already running as the same host or container UID.

Each request binds the mission ID, claim ID, delivery-envelope digest, Node-issued handoff nonce,
monotonic operation index, and selected profile digest. The Node persists only those identifiers,
digests, the next operation index, and a closed last-status code in one exclusive-owner mode-`0600`
receipt. Unknown fields, duplicate keys, oversized frames, reordered or repeated operations,
wrong-claim or wrong-envelope input, stale control posture, profile drift, restart ambiguity, and
conflicting receipts fail closed. There is no automatic claim, handoff, operation, reassignment, or
completion retry after ambiguity.

## Prompt, Output, And Credential Custody

The operator profile contains a fixed instruction that names only the three bridge affordances and
fixes the local provider as `custom`, base URL `http://host.docker.internal:11434/v1`, and model
`gemma4:e4b`. Gateway mission content never supplies a free-form prompt. The bridge may relay a
bounded governed tool result to the active runner process, but it does not persist the prompt, tool
result, model output, reasoning, Node private key, API admin token, provider credential, or local
handoff nonce.

The Hermes/bridge image has a read-only root filesystem, no persistent session or data volume, no
configured environment values, Docker logging driver `none`, Hermes verbose/reasoning display and
memory disabled, and exactly two writable locations: `/opt/data/scratch` and `/tmp`, both bounded
tmpfs. Fixed instruction, governed results, and model output may exist only in process memory or
those tmpfs locations for the shorter of the active process lifetime or the 15-minute profile wall
time. The bridge and evidence harness emit only closed status/reason codes and digests; they never
capture raw Hermes stdout/stderr, prompt, result, model output, or crash material.

The operator owns teardown and deletion: after normal exit or crash, the exact profile container
must be removed before another claim or run. Removal destroys both tmpfs locations. Evidence records
the selected profile/image identity, logging mode, read-only root, bounded tmpfs configuration,
container absence, and no persistent profile volume. A crash or failed removal blocks retry and
requires explicit cleanup. If the pinned Hermes artifact cannot run under this exact profile, the
lane stops and returns to capability review rather than relaxing custody.

Gateway inventory, audit, mission reports, telemetry, and evidence export may retain only the
existing mission/claim/Agent Run records plus closed bridge receipt fields and digests. They must
not retain prompt text, governed tool result bodies, model output, chain of thought, or credentials.
The configured model provider remains authoritative for inference facts and any provider-side
retention, which this local profile does not inspect or control.

## Static Resource And Network Posture

The operator-managed profile fixes:

- CPU: `2`;
- memory: `4096 MiB`;
- PIDs: `256`;
- writable tmpfs: `256 MiB`;
- per-file ceiling: `16 MiB`;
- total writable-disk ceiling: `256 MiB`;
- one active mission and one outstanding operation;
- operation deadline: `120 seconds`; and
- overall profile wall time: `15 minutes`.

The profile has no Docker socket, host process namespace, Linux capability, privileged mode, broad
host mount, Node state/private-key mount, Gateway admin token, SSH, Kubernetes, browser automation,
or generic process API. It retains only the operator-fixed local model-provider route needed by the
selected Hermes profile. Ithildin does not enforce or claim provider-network non-bypass; a stronger
network or filesystem claim requires a separately reviewed sandbox/host boundary.

## Cancellation And Evidence Truth

Gateway `cancel_requested`, Node `cancel_observed`, bridge receipt, runner acknowledgement, process
exit, and `runner_reported_canceled` remain separate facts. The Node polls the existing signed
mission-control endpoint before every operation and before accepting completion. It never turns a
cancel decision or local signal into proof that Hermes stopped.

Allowed bridge evidence is limited to mission/claim/envelope/profile digests, operation index,
Node-issued handoff-nonce digest, closed receipt/reason code, and timestamps. The Node signs the
existing Gateway report. Replayed, cross-mission, late, stale-posture, revoked, or profile-mismatched
receipts are denied or quarantined under the existing Mission Command rules and cannot advance
Gateway lifecycle truth.

## Implementation Gate

After this exact decision candidate receives independent Sol xhigh `GO` with no unresolved
Critical or High finding, a separate authorization record may permit only:

- closed signed Node client methods for existing mission claim/control/report endpoints;
- one mission-cycle branch after current signed configuration and heartbeat posture;
- the fixed Unix-socket protocol and repo-owned MCP bridge described here;
- exclusive-owner local receipt state containing only closed IDs, digests, indexes, and statuses;
- a derived operator-managed Hermes profile using the pinned OCI index;
- focused negative tests and one candidate-bound synthetic `O4` evidence harness/checker; and
- documentation required to operate, validate, roll back, and review that slice.

The implementation gate does not authorize a new Gateway route, database migration, policy power,
manifest change, dependency, public API, Node TCP listener, dynamic tool selection, free-form
mission, runner lifecycle control, model-provider authority, prompt/output evidence custody, or
arbitrary host control.

## Validation And Stop Lines

Before implementation authority can rise:

- this closed contract and its antecedent hashes must validate;
- the fixed 24-tool, policy-parity, and no-new-powers gates must remain green;
- exact candidate inventory and negative tests must be named;
- independent Sol xhigh review must return `GO`; and
- a post-review authorization record must bind the reviewed candidate and findings.

Stop and return to product review if implementation needs a twenty-fifth tool, manifest/policy
expansion, a different Hermes artifact/profile, arbitrary command/path/environment/provider input,
Node/admin/provider credentials in the runner, a public listener, Gateway API/schema migration,
automatic ambiguity retry, or any representation of runner/provider state as Gateway truth. Sol
Ultra remains opt-in by prior user approval and is not authorized.

<!-- mission-command-runner-bridge-decision:start -->
{"document_type":"runner_bridge_capability_decision","schema_version":"1","ticket_id":"MCC-007","decision":"fixed_hermes_node_bridge_selected_pending_exact_review","tool_count":24,"capability_selected":true,"implementation_authorized":false,"runtime_adapter_authorized":false,"runner_bridge_authorized":false,"runner_lifecycle_authority":false,"model_provider_authority":false,"prompt_output_evidence_custody_authorized":false,"arbitrary_host_control_authorized":false,"generic_process_control_authorized":false,"shell_execution_authorized":false,"docker_socket_authorized":false,"network_non_bypass_claimed":false,"filesystem_non_bypass_claimed":false,"node_private_key_shared":false,"api_admin_token_shared":false,"provider_credential_shared":false,"gateway_api_change_authorized":false,"gateway_schema_change_authorized":false,"policy_change_authorized":false,"manifest_change_authorized":false,"new_governed_tool":false,"node_tcp_listener_authorized":false,"automatic_ambiguity_retry_authorized":false,"production_identity_authorized":false,"release_allowed":false,"production_promotion_allowed":false,"uat_complete":false,"sol_ultra_authorized":false,"candidate_evaluation_sha256":"sha256:9aa24b794d23a072409ee99b9bbe282ae3a89b4c34775fc3c08dea5dcf8f00c1","candidate_evaluation_review_sha256":"sha256:81d0ac9c1a93cee414097b27ca6e6f6f97b341b4057b4e14258bacceee6fb24e","hermes_oci_index_digest":"sha256:6705aac1f41c5faca559858611ce696b760d858b73fa3b51be11599c73ba1ffc","hermes_version":"0.18.2 (2026.7.7.2)","hermes_upstream_commit":"0512f06a","hermes_platform_digests":{"linux/amd64":"sha256:48420b0abcf18f9f33cfa1da4c4e8bbd4ad107a0ddc52e5fb3ebb34a9fd20149","linux/arm64":"sha256:bca5bafd0292bdf0d4b4b975780e96c0ec9e428e08941a87aacddb116663ce13"},"bridge_source_identity":"repo_owned_ithildin_mcp_server_node_bridge_same_candidate","bridge_entrypoint":["/opt/ithildin/.venv/bin/python","-m","ithildin_mcp_server.node_bridge"],"bridge_arguments":[],"model_provider":"custom","model_base_url":"http://host.docker.internal:11434/v1","model_name":"gemma4:e4b","allowed_environment_names":[],"working_directory":"/opt/data/scratch","governed_tools":["project.structure.summary","project.test.summary"],"bridge_affordances":["mission.step.1","mission.step.2","mission.complete"],"local_protocol":"unix_domain_socket_canonical_json_v1","socket_path":"/run/ithildin-node/mission.sock","peer_identity":"linux_so_peercred_uid_10000_plus_profile_digest","state_mode":"0600","state_fields":["mission_id","claim_id","envelope_digest","next_operation_index","handoff_nonce_digest","last_closed_status"],"max_frame_bytes":16384,"operation_timeout_seconds":120,"mission_wall_time_seconds":900,"concurrency":1,"cpu_limit":2,"memory_mib":4096,"pids_limit":256,"tmpfs_mib":256,"per_file_mib":16,"writable_disk_mib":256,"runner_root_filesystem_read_only":true,"runner_writable_tmpfs":{"/opt/data/scratch":{"mib":128,"mode":"0700"},"/tmp":{"mib":128,"mode":"0700"}},"runner_persistent_session_volume":false,"runner_logging_driver":"none","runner_raw_logging_allowed":false,"runner_memory_enabled":false,"runner_verbose_enabled":false,"plaintext_lifetime_seconds":900,"cleanup_owner":"operator_profile_teardown","cleanup_evidence_fields":["profile_digest","runner_image_digest","node_image_digest","read_only_root","logging_driver","tmpfs_limits","container_absent","persistent_profile_volume_absent"],"failed_cleanup_blocks_retry":true,"build_identity_fields":["candidate_commit","candidate_tree","clean_before_bridge_build","clean_after_bridge_build","clean_before_node_build","clean_after_node_build","bridge_source_digest","node_source_digest","dependency_lock_digest","hermes_oci_index_digest","hermes_platform_digest","profile_digest","bridge_image_digest","node_image_digest","platform","sbom_digest","license_receipt_digest"],"same_candidate_equality_fields":["candidate_commit","candidate_tree"],"o4_harness_identity_binding_required":true,"profile_input_source":"operator_fixed_immutable_image_profile","prompt_custody":"operator_fixed_profile_only_not_gateway_evidence","ambiguity_policy":"no_automatic_retry_reassignment_or_finalization","cancellation_facts":["gateway_cancel_requested","node_cancel_observed","bridge_receipt","runner_acknowledgment","process_exit","runner_reported_canceled"],"evidence_fields":["mission_id","claim_id","envelope_digest","profile_digest","operation_index","handoff_nonce_digest","closed_receipt_code","closed_reason_code","observed_at"],"implementation_paths":["apps/node/src/ithildin_node/client.py","apps/node/src/ithildin_node/service.py","apps/node/src/ithildin_node/fixed_runner_bridge.py","apps/mcp-server/src/ithildin_mcp_server/node_bridge.py","deploy/hermes-node-bridge","tests/test_node_client.py","tests/test_node_service.py","tests/test_node_fixed_runner_bridge.py","tests/test_node_mcp_bridge.py","tests/test_api_service.py","scripts/local_v1_constrained_mission_journey.py","scripts/local_v1_constrained_mission_journey_check.py","tests/test_local_v1_constrained_mission_journey.py"],"exact_candidate_review_required":true,"post_review_authorization_required":true}
<!-- mission-command-runner-bridge-decision:end -->
