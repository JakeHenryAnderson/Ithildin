"""Validate the fail-closed LV1-003 O4 one-attempt execution disposition."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from ithildin_schemas import JsonObject, JsonValue, sha256_digest

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import mission_command_runner_bridge_authorization_check as code_authorization

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = Path("docs/codex/local-v1-lv1-003-o4-execution-authorization.json")
DOCUMENT = Path("docs/codex/local-v1-lv1-003-o4-execution-authorization.md")
PRODUCER_CONTRACT = Path("docs/codex/local-v1-lv1-003-o4-producer-contract.md")
PRODUCER_EXACT_REVIEW = Path(
    "docs/codex/local-v1-lv1-003-o4-producer-exact-review.md"
)
DISPOSITION_JSON = Path(
    "docs/codex/local-v1-lv1-003-o4-post-review-disposition.json"
)
DISPOSITION_DOCUMENT = Path(
    "docs/codex/local-v1-lv1-003-o4-post-review-disposition.md"
)
ATTEMPT_DISPOSITION_JSON = Path(
    "docs/codex/local-v1-lv1-003-o4-attempt-001-disposition.json"
)
ATTEMPT_DISPOSITION_DOCUMENT = Path(
    "docs/codex/local-v1-lv1-003-o4-attempt-001-disposition.md"
)
AUTHORIZATION_TARGET = "local-v1-lv1-003-o4-execution-authorization-check"
PRODUCER_STATIC_TARGET = "local-v1-lv1-003-o4-producer-static-check"
PRODUCER_RUN_TARGET = "local-v1-lv1-003-o4-producer-run"
PRODUCER_MODULE_INVOCATION = (
    "uv run python -m scripts.local_v1_lv1_003_o4_producer"
)
FAILED_FILE_PATH_INVOCATION = (
    "uv run python scripts/local_v1_lv1_003_o4_producer.py"
)
ENTRYPOINT_REPAIR_BASE_COMMIT = "148effd50c69b40a005f86f6217fc3db8b665a06"
REVIEWED_IMPLEMENTATION_COMMIT = "5dab3654391c14fe214a9dfe302c099d0fe5fbf8"
REVIEWED_IMPLEMENTATION_TREE = "f9a0cb66ac12e6e0ecca7fc23a0071be0dbe3075"
CANDIDATE_PARENT_COMMIT = "86e75f0cf7f92ceb33218f2a66a00668f4da9e12"
CANDIDATE_PARENT_TREE = "11d9a752b8e08b483e1d8b9a347a06b5d8bf9af7"
CODE_AUTHORIZATION_COMMIT = CANDIDATE_PARENT_COMMIT
CODE_AUTHORIZATION_TREE = CANDIDATE_PARENT_TREE
CODE_AUTHORIZATION_ORIGIN_COMMIT = "da17fbc86369ed5a6e7f9de7c1098322bcda4ac9"
CODE_AUTHORIZATION_ORIGIN_TREE = "7e3c14074a568dc47f7363eaab4e8ec4b996982f"
CODE_AUTHORIZATION_RECORD_DIGEST = (
    "sha256:2420d1c22faaec94d15834734b5b2f700579446c9e5fb9ea742855ff78a7b83d"
)
CODE_AUTHORIZATION_ORIGIN_RECORD_DIGEST = (
    "sha256:f241034bc56219c29ecaa215cdbed1404516130b8093567611a8c56960b1a051"
)
HISTORICAL_PRODUCER_CONTRACT_DIGEST = (
    "sha256:3c742762465380387153f5ee17686ed540354926c5364c9e73f15100d9bb30e1"
)
PRODUCER_CONTRACT_DIGEST = (
    "sha256:ef13427da1991dc4f176fe91ca90da29ca8605bfa2435a15d1a7868fc76370b6"
)
PRODUCER_EXACT_REVIEW_DIGEST = (
    "sha256:5d023bb589636fc991a86768fb97f737cae2cdd58da369c94f99a99d20245c76"
)
DISPOSITION_JSON_DIGEST = (
    "sha256:98671458e5c4053e3a892781dfb53bf8be0d397f578995e80a20483166095593"
)
DISPOSITION_DOCUMENT_DIGEST = (
    "sha256:9ddd3fc6a78c6556233888a6828e1540b4f85c68660618a424d228bc3b79eea8"
)
ATTEMPT_DISPOSITION_JSON_DIGEST = (
    "sha256:16545c118efc7fc93d57534215d1b2defeb920fb9cde388cedd14e646db00671"
)
ATTEMPT_DISPOSITION_DOCUMENT_DIGEST = (
    "sha256:3b3e12c7e6f1993c2c256eb0140e15dedf7dc42914cbf67a29de11ed20c7a245"
)
ATTEMPT_ID = "LV1-003-O4-ATTEMPT-001"
ATTEMPTED_CANDIDATE_COMMIT = "9a9e10a083ee9019b58d49d5099040e18bfbb7f2"
ATTEMPTED_CANDIDATE_TREE = "aa3eecea481dd5c92925ceec3421c051c63cb3cf"
ATTEMPTED_AUTHORIZATION_CONTRACT_DIGEST = (
    "sha256:2dfd27d564a8359ae66c87bd0ed7308cf74cd2cf5561aa60a80ba04b83bd6863"
)
ATTEMPT_COMMAND = "uv run python scripts/local_v1_lv1_003_o4_producer.py"
CONTROL_PATH_ALLOWLIST = [
    CONTRACT.as_posix(),
    DOCUMENT.as_posix(),
    DISPOSITION_JSON.as_posix(),
    DISPOSITION_DOCUMENT.as_posix(),
    "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
    "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
]
PRIOR_ATTEMPT_ROOTS = [
    "var/local-v1-lv1-003-o4-receipts",
    "var/local-v1-lv1-003-o4-runtime",
    "var/local-v1-constrained-mission-journey",
]
PROFILE_DIGEST = "sha256:90b94d725640768f1a7d665e979bbe11f263a4ff264591a5348d0b5820db3e92"
SOURCE_DIGESTS = {
    "profile_file_sha256": (
        Path("deploy/hermes-node-bridge/profile.json"),
        "sha256:d39fcb373377ff97d18eb7a81f00157e17baabf134b65231a4c3b20a7370d47e",
    ),
    "base_compose_sha256": (
        Path("deploy/docker-compose.yml"),
        "sha256:55d5978f47a29273ff25e086486b9e0d85643b1a271993b3b14a00bc8bfcda49",
    ),
    "overlay_compose_sha256": (
        Path("deploy/hermes-node-bridge/compose.yaml"),
        "sha256:a7930d3a01c1ed45e9f97bac5ccc9b05c33bcbfaceaa918dd525725afab77774",
    ),
    "bridge_dockerfile_sha256": (
        Path("deploy/hermes-node-bridge/Dockerfile"),
        "sha256:511c195334d336222bc396d471e8cccdd71aa2b0bb36a24e7628b24e4df893da",
    ),
    "dependency_lock_sha256": (
        Path("uv.lock"),
        "sha256:a0ea98764d069193226a9debe837f37655ee707cb17dcdf6731b922883a4dafb",
    ),
}
FIXED_ACTIONS = [
    "docker_daemon_version",
    "docker_compose_version",
    "merged_compose_config_quiet",
    "build_base_api_ui_node",
    "build_fixed_hermes_bridge",
    "inspect_owned_image_ids_platform_config_and_layers",
    "start_base_api_ui",
    "enroll_node_once_via_stdin",
    "start_ordinary_node",
    "stop_ordinary_node",
    "start_reviewed_fixed_node_wait",
    "run_hermes_once_no_arguments_devnull_output",
    "copy_closed_node_mission_receipt",
    "stop_fixed_node",
    "compose_down_remove_orphans_volumes",
    "list_project_containers_volumes_networks",
    "remove_exact_owned_images",
    "prove_exact_owned_images_absent",
]
EXTERNAL_PREFLIGHT = [
    "clean_exact_candidate_matching_post_review_disposition",
    "local_docker_socket_uniquely_proven",
    "ambient_docker_host_context_config_credentials_and_proxies_absent",
    "docker_daemon_and_compose_available",
    "ports_8000_and_5173_available",
    "host_local_ollama_reachable_at_127_0_0_1_11434",
    "host_local_ollama_model_inventory_contains_exact_gemma4_e4b",
    "reviewed_hermes_platform_digest_available",
    "isolated_0700_runtime_and_0600_secret_files",
    "source_profile_and_compose_digests_exact",
]
AUTHORITY_FIELDS = {
    "producer_code_authorized",
    "docker_lifecycle_authorized",
    "live_hermes_execution_authorized",
    "model_provider_access_authorized",
    "o4_evidence_execution_authorized",
    "credential_custody_authorized",
    "runner_lifecycle_authority",
    "arbitrary_host_control_authorized",
    "generic_process_control_authorized",
    "shell_execution_authorized",
    "docker_socket_authorized",
    "network_non_bypass_claimed",
    "filesystem_non_bypass_claimed",
    "new_governed_power_authorized",
    "new_governed_tool",
    "release_allowed",
    "promotion_allowed",
    "production_authorized",
    "uat_complete",
}
TOP_LEVEL_FIELDS = {
    "schema_version",
    "record_type",
    "record_status",
    "ticket_id",
    "outcome_id",
    "producer_contract_path",
    "producer_contract_sha256",
    "candidate_parent_commit",
    "candidate_parent_tree",
    "reviewed_implementation_commit",
    "reviewed_implementation_tree",
    "producer_exact_review_record",
    "producer_exact_review_sha256",
    "code_authorization_origin_commit",
    "code_authorization_origin_tree",
    "code_authorization_commit",
    "code_authorization_tree",
    "code_authorization_origin_record_sha256",
    "code_authorization_record_sha256",
    "post_review_disposition_json",
    "post_review_disposition_json_sha256",
    "post_review_disposition_document",
    "post_review_disposition_document_sha256",
    "attempt_disposition_json",
    "attempt_disposition_json_sha256",
    "attempt_disposition_document",
    "attempt_disposition_document_sha256",
    "attempt_id",
    "attempted_candidate_commit",
    "attempted_candidate_tree",
    "attempted_authorization_contract_sha256",
    "attempt_invocation",
    "attempt_root_absence",
    "producer_entrypoint_repair",
    "execution_candidate_binding_mode",
    "execution_attempt_budget",
    "attempt_consumed",
    "retry_authorized",
    "attempt_custody",
    "persistent_cross_process_budget_consumption_claimed",
    "immediate_post_attempt_disposition_recorded",
    "prior_attempt_detection_roots",
    "profile",
    "command_contract",
    "external_preflight_requirements",
    "evidence_contract",
    "cleanup_contract",
    "authority",
}
EXPECTED_PROFILE: JsonObject = {
    "profile_id": "ithildin-fixed-hermes-node-bridge-v1",
    "canonical_profile_sha256": PROFILE_DIGEST,
    **{key: digest for key, (_, digest) in SOURCE_DIGESTS.items()},
    "hermes_oci_index_digest": (
        "sha256:6705aac1f41c5faca559858611ce696b760d858b73fa3b51be11599c73ba1ffc"
    ),
    "hermes_platform_digests": {
        "linux/amd64": (
            "sha256:48420b0abcf18f9f33cfa1da4c4e8bbd4ad107a0ddc52e5fb3ebb34a9fd20149"
        ),
        "linux/arm64": (
            "sha256:bca5bafd0292bdf0d4b4b975780e96c0ec9e428e08941a87aacddb116663ce13"
        ),
    },
    "provider_type": "custom",
    "provider_base_url": "http://host.docker.internal:11434/v1",
    "host_preflight_base_url": "http://127.0.0.1:11434",
    "provider_model": "gemma4:e4b",
    "container_provider_routing_runtime_unknown": True,
    "cloud_credentials_allowed": False,
}
EXPECTED_COMMAND_CONTRACT: JsonObject = {
    "dynamic_values": [
        "run_id",
        "unique_compose_project",
        "anchored_runtime_paths",
        "anchored_exact_candidate_snapshot_paths",
        "run_specific_image_references",
        "exact_inspected_image_ids",
    ],
    "fixed_actions": cast(list[JsonValue], FIXED_ACTIONS),
    "arbitrary_command_allowed": False,
    "arbitrary_argument_allowed": False,
    "arbitrary_path_allowed": False,
    "arbitrary_provider_allowed": False,
    "arbitrary_model_allowed": False,
    "arbitrary_tool_allowed": False,
}
EXPECTED_EVIDENCE_CONTRACT: JsonObject = {
    "mission_template_id": "synthetic_read_review_v1",
    "mission_count": 1,
    "hermes_execution_attempts_maximum": 1,
    "automatic_retry_allowed": False,
    "gateway_operation_bindings_source": "mission_detail_plus_agent_run_detail_timeline",
    "gateway_mission_lifecycle_state": "runner_reported_succeeded",
    "gateway_agent_run_record_status": "active",
    "gateway_completed_timeline_event_type": "tool.execution.completed",
    "gateway_completed_timeline_event_count": 2,
    "runner_authored_operation_counts_trusted": False,
    "synthesized_agent_run_completion_allowed": False,
    "hermes_stdout_destination": "DEVNULL_AT_SUBPROCESS_CREATION",
    "hermes_stderr_destination": "DEVNULL_AT_SUBPROCESS_CREATION",
    "hermes_output_materialized": False,
    "hermes_retained_classifications": ["exit", "timeout", "interruption"],
    "container_provider_route_failure_consumes_attempt": True,
    "future_fake_tests_require_devnull_streams": True,
    "build_receipt_mode": "0600",
    "journey_receipt_mode": "0600",
    "image_artifact_inventory_field": "image_artifact_inventory_digest",
    "license_source_inventory_field": "license_source_inventory_digest",
    "future_assembler_schema_reconciliation_required": False,
    "current_assembler_usable_for_live_producer": True,
    "future_reconciled_assembler_and_checker_required": False,
    "bounded_image_artifact_inventory_required": True,
    "bounded_image_metadata_fields": [
        "reference",
        "image_id",
        "platform",
        "config_digest",
        "ordered_layer_digests",
    ],
    "bounded_license_source_inventory_required": True,
    "license_inventory_source": "private_exact_candidate_snapshot_no_follow_size_limited",
    "license_source_file_max_bytes": 1048576,
    "current_tracked_license_inventory_inputs": ["pyproject.toml", "uv.lock"],
    "current_tracked_license_family_files": [],
    "license_family_patterns": ["LICENSE*", "NOTICE*", "COPYING*"],
    "static_snapshot_enumeration_and_path_replacement_rejection_proven": True,
    "transient_malicious_same_uid_mutation_during_docker_context_read_proven_absent": (
        False
    ),
    "operating_system_snapshot_immutability_claimed": False,
    "complete_sbom_claimed": False,
    "license_completeness_claimed": False,
    "compliance_claimed": False,
    "artifact_custody_claimed": False,
}
EXPECTED_CLEANUP_CONTRACT: JsonObject = {
    "node_revocation_required": True,
    "containers_absent_required": True,
    "volumes_absent_required": True,
    "network_absent_required": True,
    "persistent_profile_volume_absent_required": True,
    "run_specific_images_absent_required": True,
    "runtime_plaintext_absent_required": True,
    "cleanup_failure_requires_recovery": True,
    "cleanup_ambiguity_requires_stop": True,
    "early_failure_plaintext_cleanup_required": True,
    "monotonic_best_effort_cleanup_required": True,
    "enrollment_attempt_recorded_before_subprocess": True,
    "ambiguous_enrollment_retains_runtime_and_node_volume": True,
    "ambiguous_enrollment_revocation_claim_allowed": False,
    "confirmed_node_revocation_required_before_destructive_cleanup": True,
    "unconfirmed_revocation_retains_runtime_and_node_volume": True,
    "unconfirmed_revocation_safe_action": "stop_exact_fixed_node_only",
    "private_secret_free_recovery_identity_receipt_required": True,
    "recovery_identity_receipt_max_bytes": 4096,
    "recovery_identity_receipt_fields": [
        "schema_version",
        "receipt_kind",
        "run_id",
        "candidate_commit",
        "candidate_tree",
        "workspace_id",
        "node_id",
        "compose_project",
        "node_volume_name",
        "revocation_confirmed",
        "node_volume_retained",
        "anchored_runtime_retained",
        "reconciliation_required",
        "next_action",
        "release_allowed",
        "uat_complete",
    ],
    "recovery_identity_receipt_contains_credentials": False,
    "recovery_identity_receipt_published_as_success_evidence": False,
    "atomic_success_publication_required": True,
    "failed_receipt_quarantine_required": True,
    "publication_rollback_requires_name_removal_or_hidden_quarantine": True,
    "publication_rollback_base_directory_fsync_required": True,
    "chmod_only_publication_rollback_success_allowed": False,
    "retry_after_failure_automatic": False,
}
HISTORICAL_TRUE_AUTHORITY_FIELDS = {
    "producer_code_authorized",
    "docker_lifecycle_authorized",
    "live_hermes_execution_authorized",
    "model_provider_access_authorized",
    "o4_evidence_execution_authorized",
}
HISTORICAL_AUTHORITY: JsonObject = {
    key: key in HISTORICAL_TRUE_AUTHORITY_FIELDS for key in AUTHORITY_FIELDS
}
TRUE_AUTHORITY_FIELDS: set[str] = set()
EXPECTED_AUTHORITY: JsonObject = {key: False for key in AUTHORITY_FIELDS}


class O4ExecutionAuthorizationError(RuntimeError):
    """Raised when a live producer asks for unavailable authority."""


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    contract = _read_contract(repo_root / CONTRACT, failures)
    document = _read_text(repo_root / DOCUMENT, failures)
    producer_contract = _read_text(repo_root / PRODUCER_CONTRACT, failures)
    disposition = _read_contract(repo_root / DISPOSITION_JSON, failures)
    disposition_document = _read_text(repo_root / DISPOSITION_DOCUMENT, failures)
    attempt_disposition = _read_contract(
        repo_root / ATTEMPT_DISPOSITION_JSON,
        failures,
    )
    attempt_disposition_document = _read_text(
        repo_root / ATTEMPT_DISPOSITION_DOCUMENT,
        failures,
    )
    _validate_contract(contract, failures)
    _validate_document(document, failures)
    _validate_producer_contract(producer_contract, contract, failures)
    _validate_disposition(disposition, disposition_document, failures)
    _validate_attempt_disposition(
        attempt_disposition,
        attempt_disposition_document,
        failures,
    )
    _validate_bound_documents(repo_root, failures)
    _validate_git_bindings(repo_root, failures)
    _validate_attempted_candidate_binding(repo_root, failures)
    _validate_source_bindings(repo_root, contract, failures)
    _validate_current_license_discovery(repo_root, failures)
    code_report = code_authorization.build_report(repo_root)
    if not code_report["valid"]:
        failures.append("reviewed runner-bridge code authorization is invalid")
    if (
        code_report.get("reviewed_candidate_commit") != REVIEWED_IMPLEMENTATION_COMMIT
        or code_report.get("code_implementation_authorized") is not True
        or code_report.get("authorized_runtime_matches_reviewed_candidate") is not True
    ):
        failures.append("reviewed runner-bridge code authority is not exact")
    _validate_wiring(repo_root, failures)
    _validate_recorded_root_absence(repo_root, failures)
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "record_status": contract.get("record_status"),
        "reviewed_implementation_commit": contract.get("reviewed_implementation_commit"),
        "code_authorization_commit": contract.get("code_authorization_commit"),
        "attempt_id": contract.get("attempt_id"),
        "attempted_candidate_commit": contract.get("attempted_candidate_commit"),
        "attempted_candidate_tree": contract.get("attempted_candidate_tree"),
        "attempt_consumed": contract.get("attempt_consumed"),
        "retry_authorized": False,
        "execution_checkout_commit": None,
        "execution_checkout_tree": None,
        "execution_attempt_budget": 0,
        "live_execution_authorized": False,
        "docker_lifecycle_authorized": False,
        "provider_access_authorized": False,
        "o4_evidence_execution_authorized": False,
        "new_governed_tool": False,
        "release_allowed": False,
        "uat_complete": False,
    }


def assert_live_execution_authorized(
    repo_root: Path,
    *,
    candidate_commit: str,
    candidate_tree: str,
) -> None:
    report = build_report(repo_root)
    if (
        not report["valid"]
        or report["live_execution_authorized"] is not True
        or report["execution_attempt_budget"] != 1
        or report["execution_checkout_commit"] != candidate_commit
        or report["execution_checkout_tree"] != candidate_tree
    ):
        raise O4ExecutionAuthorizationError("o4_live_execution_not_authorized")


def _validate_contract(contract: JsonObject, failures: list[str]) -> None:
    if set(contract) != TOP_LEVEL_FIELDS:
        failures.append("O4 execution authorization fields are not closed")
    expected = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_execution_authorization",
        "record_status": "ATTEMPT_CONSUMED_PRE_GATE_IMPORT_FAILURE",
        "ticket_id": "LV1-003",
        "outcome_id": "O4",
        "producer_contract_path": PRODUCER_CONTRACT.as_posix(),
        "producer_contract_sha256": PRODUCER_CONTRACT_DIGEST,
        "candidate_parent_commit": CANDIDATE_PARENT_COMMIT,
        "candidate_parent_tree": CANDIDATE_PARENT_TREE,
        "reviewed_implementation_commit": REVIEWED_IMPLEMENTATION_COMMIT,
        "reviewed_implementation_tree": REVIEWED_IMPLEMENTATION_TREE,
        "producer_exact_review_record": PRODUCER_EXACT_REVIEW.as_posix(),
        "producer_exact_review_sha256": PRODUCER_EXACT_REVIEW_DIGEST,
        "code_authorization_origin_commit": CODE_AUTHORIZATION_ORIGIN_COMMIT,
        "code_authorization_origin_tree": CODE_AUTHORIZATION_ORIGIN_TREE,
        "code_authorization_commit": CODE_AUTHORIZATION_COMMIT,
        "code_authorization_tree": CODE_AUTHORIZATION_TREE,
        "code_authorization_origin_record_sha256": (
            CODE_AUTHORIZATION_ORIGIN_RECORD_DIGEST
        ),
        "code_authorization_record_sha256": CODE_AUTHORIZATION_RECORD_DIGEST,
        "post_review_disposition_json": DISPOSITION_JSON.as_posix(),
        "post_review_disposition_json_sha256": DISPOSITION_JSON_DIGEST,
        "post_review_disposition_document": DISPOSITION_DOCUMENT.as_posix(),
        "post_review_disposition_document_sha256": DISPOSITION_DOCUMENT_DIGEST,
        "attempt_disposition_json": ATTEMPT_DISPOSITION_JSON.as_posix(),
        "attempt_disposition_json_sha256": ATTEMPT_DISPOSITION_JSON_DIGEST,
        "attempt_disposition_document": ATTEMPT_DISPOSITION_DOCUMENT.as_posix(),
        "attempt_disposition_document_sha256": ATTEMPT_DISPOSITION_DOCUMENT_DIGEST,
        "attempt_id": ATTEMPT_ID,
        "attempted_candidate_commit": ATTEMPTED_CANDIDATE_COMMIT,
        "attempted_candidate_tree": ATTEMPTED_CANDIDATE_TREE,
        "attempted_authorization_contract_sha256": (
            ATTEMPTED_AUTHORIZATION_CONTRACT_DIGEST
        ),
        "attempt_invocation": {
            "command": ATTEMPT_COMMAND,
            "exit_code": 1,
            "classification": "PRE_GATE_MODULE_IMPORT_FAILURE",
            "exception_type": "ModuleNotFoundError",
            "exception_message": "No module named 'scripts'",
            "failure_location": "scripts/local_v1_lv1_003_o4_producer.py:36",
            "gate_authorization_entered": False,
            "producer_runtime_entered": False,
        },
        "attempt_root_absence": {
            "observation_method": "read_only_path_absence_check_after_failed_invocation",
            "absent_roots": cast(list[JsonValue], PRIOR_ATTEMPT_ROOTS),
        },
        "producer_entrypoint_repair": {
            "status": "IMPLEMENTED_PENDING_EXACT_REVIEW_NO_RETRY_AUTHORITY",
            "base_closure_commit": ENTRYPOINT_REPAIR_BASE_COMMIT,
            "live_make_target": PRODUCER_RUN_TARGET,
            "module_invocation": PRODUCER_MODULE_INVOCATION,
            "failed_file_path_invocation": FAILED_FILE_PATH_INVOCATION,
            "failed_file_path_invocation_authorized": False,
            "module_import_executes_main": False,
            "independent_exact_review_required": True,
            "separate_new_attempt_disposition_required": True,
        },
        "execution_candidate_binding_mode": (
            "attempt_consumed_no_execution_candidate_authorized"
        ),
        "execution_attempt_budget": 0,
        "attempt_consumed": True,
        "retry_authorized": False,
        "attempt_custody": "central_manager_supervised_local_invocation",
        "persistent_cross_process_budget_consumption_claimed": False,
        "immediate_post_attempt_disposition_recorded": True,
        "prior_attempt_detection_roots": PRIOR_ATTEMPT_ROOTS,
        "external_preflight_requirements": EXTERNAL_PREFLIGHT,
    }
    for key, value in expected.items():
        if not _exact_json_equal(contract.get(key), value):
            failures.append(f"O4 execution authorization {key} is not exact")
    if not _exact_json_equal(contract.get("profile"), EXPECTED_PROFILE):
        failures.append("O4 execution profile binding is not exact")
    if not _exact_json_equal(
        contract.get("command_contract"),
        EXPECTED_COMMAND_CONTRACT,
    ):
        failures.append("O4 execution command contract is invalid")
    if not _exact_json_equal(
        contract.get("evidence_contract"),
        EXPECTED_EVIDENCE_CONTRACT,
    ):
        failures.append("O4 execution evidence contract is invalid")
    if not _exact_json_equal(
        contract.get("cleanup_contract"),
        EXPECTED_CLEANUP_CONTRACT,
    ):
        failures.append("O4 execution cleanup contract is invalid")
    if not _exact_json_equal(contract.get("authority"), EXPECTED_AUTHORITY):
        failures.append("O4 execution authority must be all false after Attempt 001")


def _validate_document(document: str, failures: list[str]) -> None:
    normalized = " ".join(document.split())
    for phrase in (
        "Status: `ATTEMPT_CONSUMED_PRE_GATE_IMPORT_FAILURE`",
        REVIEWED_IMPLEMENTATION_COMMIT,
        CANDIDATE_PARENT_COMMIT,
        CODE_AUTHORIZATION_COMMIT,
        ATTEMPTED_CANDIDATE_COMMIT,
        ATTEMPTED_CANDIDATE_TREE,
        ATTEMPT_COMMAND,
        "exited `1` before gate authorization or producer runtime entry",
        "`ModuleNotFoundError: No module named 'scripts'`",
        "receipt, runtime, and constrained-journey report roots absent",
        "performed no runtime creation, Docker, Ollama or provider, API, Node, Hermes, "
        "credential, network journey, or evidence action",
        "make local-v1-lv1-003-o4-producer-run",
        "`uv run python -m scripts.local_v1_lv1_003_o4_producer`",
        "failed command `uv run python scripts/local_v1_lv1_003_o4_producer.py` is not "
        "an authorized future invocation",
        "Importing that module does not execute its `main` function",
        "requires independent exact review and a separate new-attempt disposition",
        "not a dependency of release, milestone, or static checks",
        "one server-owned",
        "`synthetic_read_review_v1`",
        "`max_cycles=1`",
        "Hermes may be invoked exactly once with no supplied",
        "Gateway mission detail and Gateway Agent Run detail/timeline",
        "actual Gateway truth is mission lifecycle `runner_reported_succeeded`, "
        "Agent Run record status `active`, and exactly two "
        "`tool.execution.completed` timeline events",
        "connected directly to `DEVNULL` when its subprocess is created",
        "was usable only for the now-consumed supervised attempt when the dynamic immediate-child "
        "gate passed",
        code_authorization.REVIEW_DOCUMENT,
        "does not prove absence of transient malicious same-UID mutation while Docker reads "
        "the build context",
        "host-local only at `http://127.0.0.1:11434`",
        "permission removal alone is insufficient",
        "If a validated Node ID exists but revocation is unavailable, invalid, or interrupted",
        "private recovery receipt is quarantined staged material, not successful published "
        "evidence",
        "There is no automatic retry",
        "Every other authority field is also false",
        "attempt budget is zero",
        "governed tool count remains exactly 24",
        "No retry is authorized",
        "requires a repaired candidate, independent exact review of that candidate, and a "
        "separate post-review execution disposition",
        "does not bind or derive its own closure commit or tree",
    ):
        if phrase not in normalized:
            failures.append(f"O4 execution authorization doc is missing phrase: {phrase}")


def _validate_producer_contract(
    document: str,
    contract: JsonObject,
    failures: list[str],
) -> None:
    normalized = " ".join(document.split())
    for phrase in (
        "Status: `entrypoint_repair_candidate_pending_exact_review_and_separate_attempt_"
        "disposition`",
        "candidate producer and reconciled assembler now implement this contract",
        "Attempt 001 is consumed after the failed file-path invocation",
        "make local-v1-lv1-003-o4-producer-run",
        "`uv run python -m scripts.local_v1_lv1_003_o4_producer`",
        "`uv run python scripts/local_v1_lv1_003_o4_producer.py` is not an authorized "
        "future entrypoint",
        "Importing the module does not execute `main`",
        "current consumed Attempt 001 disposition refuses this repaired entrypoint",
        "remains unusable for live producer evidence until this producer-and-assembler "
        "candidate receives independent exact review",
        "before it creates a runtime directory or performs Docker, API, provider, network",
        "One invocation has these exact ordered stages",
        "Create a unique `ithildin-local-v1-o4-<8 lowercase hex>`",
        "ordinary Node eligibility",
        "Admit exactly one server-owned `synthetic_read_review_v1`",
        "`max_cycles=1`",
        "route stdout and stderr directly to `DEVNULL`",
        "There is no automatic retry",
        "GET /missions/{mission_id}",
        "GET /runs/{run_id}",
        "Agent Run record status `active`",
        "exactly two distinct `tool.execution.completed` timeline events",
        "never trust runner-authored operation counts",
        "`image_artifact_inventory_digest`, never as an SBOM",
        "exact private snapshot with no-follow reads and a fixed size ceiling",
        "do not prove absence of transient malicious same-UID mutation while Docker reads "
        "the build context",
        "current discovery is exactly `pyproject.toml` and `uv.lock`, with zero tracked",
        "reconciled constrained-mission assembler and checker",
        "Container routing through `host.docker.internal` remains a runtime-only fact",
        "leaves `enrollment_outcome_ambiguous=true`, makes no revocation or absence claim",
        "writes and verifies `node-revocation-recovery.json`",
        "attempts the exact fixed-Node stop but skips project down",
        "Permission removal alone is never rollback success",
        "recovery_required",
        "Runtime-Only Facts Still Unproven",
    ):
        if phrase not in normalized:
            failures.append(f"O4 producer contract is missing phrase: {phrase}")
    stages = re.findall(r"(?m)^(\d+)\. ", document)
    if stages != [str(number) for number in range(1, 18)]:
        failures.append("O4 producer contract must contain exactly 17 ordered stages")
    document_digest = _digest(document)
    if document_digest != PRODUCER_CONTRACT_DIGEST:
        failures.append("O4 producer contract digest is invalid")
    if not _exact_json_equal(
        contract.get("producer_contract_sha256"),
        document_digest,
    ):
        failures.append("O4 producer contract digest binding is invalid")


def _validate_disposition(
    disposition: JsonObject,
    document: str,
    failures: list[str],
) -> None:
    expected: JsonObject = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_post_review_disposition",
        "record_status": "AUTHORIZE_SUPERVISED_ONE_ATTEMPT_IMMEDIATE_CHILD",
        "ticket_id": "LV1-003",
        "outcome_id": "O4",
        "candidate_parent_commit": CANDIDATE_PARENT_COMMIT,
        "candidate_parent_tree": CANDIDATE_PARENT_TREE,
        "reviewed_implementation_commit": REVIEWED_IMPLEMENTATION_COMMIT,
        "reviewed_implementation_tree": REVIEWED_IMPLEMENTATION_TREE,
        "producer_exact_review_path": PRODUCER_EXACT_REVIEW.as_posix(),
        "producer_exact_review_sha256": PRODUCER_EXACT_REVIEW_DIGEST,
        "code_authorization_path": code_authorization.AUTHORIZATION,
        "code_authorization_commit": CODE_AUTHORIZATION_COMMIT,
        "code_authorization_tree": CODE_AUTHORIZATION_TREE,
        "code_authorization_record_sha256": CODE_AUTHORIZATION_RECORD_DIGEST,
        "producer_contract_sha256": HISTORICAL_PRODUCER_CONTRACT_DIGEST,
        "execution_candidate_binding": {
            "mode": "dynamic_current_head_after_all_checks",
            "required_parent_relation": "single_immediate_child_of_candidate_parent",
            "clean_checkout_required": True,
            "static_child_commit_claimed": False,
            "static_child_tree_claimed": False,
            "runtime_byte_parity_commit": REVIEWED_IMPLEMENTATION_COMMIT,
            "changed_paths_must_equal_control_allowlist": True,
        },
        "control_path_allowlist": cast(list[JsonValue], CONTROL_PATH_ALLOWLIST),
        "attempt_contract": {
            "maximum_supervised_invocations": 1,
            "custody": "central_manager_supervised_local_invocation",
            "concurrent_invocations_authorized": False,
            "automatic_retry_authorized": False,
            "post_attempt_rerun_authorized": False,
            "immediate_post_attempt_disposition_required": True,
            "persistent_cross_process_budget_consumption_claimed": False,
            "prior_attempt_detection": (
                "retained_exact_local_evidence_only_not_tamper_proof_or_atomic_consumption"
            ),
            "prior_attempt_roots": cast(list[JsonValue], PRIOR_ATTEMPT_ROOTS),
        },
        "authority": HISTORICAL_AUTHORITY,
    }
    if not _exact_json_equal(disposition, expected):
        failures.append("O4 post-review disposition is not closed and exact")
    normalized = " ".join(document.split())
    for phrase in (
        "AUTHORIZE_SUPERVISED_ONE_ATTEMPT_IMMEDIATE_CHILD",
        CANDIDATE_PARENT_COMMIT,
        REVIEWED_IMPLEMENTATION_COMMIT,
        "six-path control allowlist",
        "No future child commit or tree is stated here",
        "one central-manager-supervised local producer invocation",
        "does not implement or claim atomic, tamper-proof, persistent cross-process budget "
        "consumption",
        "No concurrent invocation, automatic retry, or post-attempt rerun is authorized",
        "requires an immediate new post-attempt disposition",
        "Only these five authority bits are true",
        "governed tool count remains exactly 24",
    ):
        if phrase not in normalized:
            failures.append(f"O4 post-review disposition doc is missing phrase: {phrase}")


def _validate_attempt_disposition(
    disposition: JsonObject,
    document: str,
    failures: list[str],
) -> None:
    expected: JsonObject = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_attempt_disposition",
        "record_status": "ATTEMPT_CONSUMED_PRE_GATE_IMPORT_FAILURE",
        "ticket_id": "LV1-003",
        "outcome_id": "O4",
        "attempt_id": ATTEMPT_ID,
        "attempt_number": 1,
        "attempted_candidate_commit": ATTEMPTED_CANDIDATE_COMMIT,
        "attempted_candidate_tree": ATTEMPTED_CANDIDATE_TREE,
        "attempted_candidate_clean": True,
        "attempted_authorization_contract_sha256": (
            ATTEMPTED_AUTHORIZATION_CONTRACT_DIGEST
        ),
        "invocation": {
            "command": ATTEMPT_COMMAND,
            "exit_code": 1,
            "classification": "PRE_GATE_MODULE_IMPORT_FAILURE",
            "exception_type": "ModuleNotFoundError",
            "exception_message": "No module named 'scripts'",
            "failure_location": "scripts/local_v1_lv1_003_o4_producer.py:36",
            "module_import_started": True,
            "gate_authorization_entered": False,
            "producer_runtime_entered": False,
        },
        "observed_root_absence": {
            "observation_method": "read_only_path_absence_check_after_failed_invocation",
            "roots": [
                {"path": path, "exists": False} for path in PRIOR_ATTEMPT_ROOTS
            ],
        },
        "external_action_observation": {
            "runtime_created": False,
            "docker_action_performed": False,
            "ollama_or_provider_action_performed": False,
            "api_action_performed": False,
            "node_action_performed": False,
            "hermes_action_performed": False,
            "credential_action_performed": False,
            "network_journey_action_performed": False,
            "evidence_action_performed": False,
        },
        "attempt_contract": {
            "attempt_consumed": True,
            "retry_authorized": False,
            "automatic_retry_authorized": False,
            "post_failure_execution_authorized": False,
            "separately_reviewed_repair_candidate_required": True,
            "separate_post_review_execution_disposition_required": True,
        },
        "closure_candidate_binding": {
            "closure_commit_claimed": False,
            "closure_tree_claimed": False,
            "descendant_closure_commit_allowed": True,
        },
        "authority": EXPECTED_AUTHORITY,
    }
    if not _exact_json_equal(disposition, expected):
        failures.append("O4 Attempt 001 disposition is not closed and exact")
    normalized = " ".join(document.split())
    for phrase in (
        "Status: `ATTEMPT_CONSUMED_PRE_GATE_IMPORT_FAILURE`",
        ATTEMPT_ID,
        ATTEMPTED_CANDIDATE_COMMIT,
        ATTEMPTED_CANDIDATE_TREE,
        ATTEMPT_COMMAND,
        "exited `1` during module import",
        "`ModuleNotFoundError: No module named 'scripts'`",
        "authorization gate was not entered and producer runtime was not entered",
        "all three exact roots absent",
        "no runtime creation, Docker action, Ollama or model provider action, API action, "
        "Node action, Hermes action, credential action, network journey action, or evidence "
        "action",
        "attempt budget is now zero and all 19 authority fields are false",
        "A retry requires a repaired candidate, independent exact review of that candidate, "
        "and a separate post-review execution disposition",
        "does not state or derive its own future closure commit or tree",
    ):
        if phrase not in normalized:
            failures.append(f"O4 Attempt 001 disposition doc is missing phrase: {phrase}")


def _validate_bound_documents(repo_root: Path, failures: list[str]) -> None:
    for path, expected, label in (
        (PRODUCER_EXACT_REVIEW, PRODUCER_EXACT_REVIEW_DIGEST, "producer exact review"),
        (DISPOSITION_JSON, DISPOSITION_JSON_DIGEST, "post-review disposition JSON"),
        (
            DISPOSITION_DOCUMENT,
            DISPOSITION_DOCUMENT_DIGEST,
            "post-review disposition document",
        ),
        (
            ATTEMPT_DISPOSITION_JSON,
            ATTEMPT_DISPOSITION_JSON_DIGEST,
            "Attempt 001 disposition JSON",
        ),
        (
            ATTEMPT_DISPOSITION_DOCUMENT,
            ATTEMPT_DISPOSITION_DOCUMENT_DIGEST,
            "Attempt 001 disposition document",
        ),
    ):
        if _file_digest(repo_root / path, failures) != expected:
            failures.append(f"O4 {label} digest is invalid")


def _validate_execution_checkout(
    repo_root: Path,
    failures: list[str],
    *,
    candidate_parent_commit: str = CANDIDATE_PARENT_COMMIT,
    candidate_parent_tree: str = CANDIDATE_PARENT_TREE,
    reviewed_commit: str = REVIEWED_IMPLEMENTATION_COMMIT,
    runtime_paths: list[str] | None = None,
    control_paths: list[str] | None = None,
) -> tuple[str, str] | None:
    runtime_paths = (
        list(code_authorization.ALLOWED_RUNTIME_PATHS)
        if runtime_paths is None
        else runtime_paths
    )
    control_paths = CONTROL_PATH_ALLOWLIST if control_paths is None else control_paths
    head = _git(repo_root, ["rev-parse", "HEAD"], failures)
    tree = _git(repo_root, ["show", "-s", "--format=%T", "HEAD"], failures)
    parents = _git(repo_root, ["show", "-s", "--format=%P", "HEAD"], failures).split()
    if parents != [candidate_parent_commit]:
        failures.append(
            "O4 execution checkout is not a single immediate child of the authorized parent"
        )
    parent_tree = _git(
        repo_root,
        ["show", "-s", "--format=%T", candidate_parent_commit],
        failures,
    )
    if parent_tree != candidate_parent_tree:
        failures.append("O4 execution candidate parent tree is not exact")
    status = _git(
        repo_root,
        ["status", "--porcelain=v1", "--untracked-files=all"],
        failures,
    )
    if status:
        failures.append("O4 execution checkout is not clean")
    changed = _git(
        repo_root,
        ["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
        failures,
    ).splitlines()
    if changed != control_paths:
        failures.append("O4 execution candidate changed paths are not the exact control allowlist")
    parity = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "diff",
            "--quiet",
            reviewed_commit,
            "HEAD",
            "--",
            *runtime_paths,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if parity.returncode != 0:
        failures.append("O4 execution runtime differs from the exact reviewed candidate")
    if failures:
        return None
    return head, tree


def _validate_prior_attempt_posture(repo_root: Path, failures: list[str]) -> None:
    for relative in PRIOR_ATTEMPT_ROOTS:
        path = repo_root / relative
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            continue
        except OSError:
            failures.append(f"O4 prior-attempt root is unreadable: {relative}")
            continue
        if path.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
            failures.append(f"O4 prior-attempt root is not a no-follow directory: {relative}")
            continue
        if metadata.st_uid != os.getuid() or metadata.st_gid != os.getgid():
            failures.append(f"O4 prior-attempt root ownership is unsafe: {relative}")
        if stat.S_IMODE(metadata.st_mode) != 0o700:
            failures.append(f"O4 prior-attempt root mode is not 0700: {relative}")
        try:
            retained = next(path.iterdir(), None)
        except OSError:
            failures.append(f"O4 prior-attempt root cannot be enumerated: {relative}")
            continue
        if retained is not None:
            failures.append(f"O4 prior attempt or success evidence exists: {relative}")


def _validate_wiring(repo_root: Path, failures: list[str]) -> None:
    makefile = _read_text(repo_root / "Makefile", failures)
    readme = _read_text(repo_root / "README.md", failures)
    expected_bodies = {
        AUTHORIZATION_TARGET: (
            "\tuv run python "
            "scripts/local_v1_lv1_003_o4_execution_authorization_check.py"
        ),
        PRODUCER_STATIC_TARGET: (
            "\tuv run pytest \\\n"
            "\t\ttests/test_local_v1_lv1_003_o4_execution_authorization_check.py \\\n"
            "\t\ttests/test_local_v1_lv1_003_o4_producer.py \\\n"
            "\t\ttests/test_local_v1_constrained_mission_journey.py \\\n"
            "\t\t-q"
        ),
    }
    for target, expected_body in expected_bodies.items():
        definitions = sum(
            line.startswith(f"{target}:") for line in makefile.splitlines()
        )
        if definitions != 1:
            failures.append(f"O4 execution Make target is not unique: {target}")
            continue
        body = _target_body(makefile, target)
        if body.strip() != expected_body.strip():
            failures.append(f"O4 execution Make target body is not exact: {target}")
        milestone = _target_body(makefile, "local-v1-milestone-check")
        if milestone.count(f"\t$(MAKE) {target}") != 1:
            failures.append(f"O4 execution target is not in Local-v1 milestone once: {target}")
        release_header = next(
            (line for line in makefile.splitlines() if line.startswith("release-check:")),
            "",
        )
        if target in release_header:
            failures.append(f"O4 execution target must not be wired into release-check: {target}")
    run_occurrences = [
        (line_number, line)
        for line_number, line in enumerate(makefile.splitlines(), start=1)
        if PRODUCER_RUN_TARGET in line
    ]
    allowed_occurrences = 0
    for line_number, line in run_occurrences:
        if line == f"{PRODUCER_RUN_TARGET}:":
            allowed_occurrences += 1
            continue
        if line.startswith(".PHONY:"):
            tokens = line.split()
            if (
                tokens.count(PRODUCER_RUN_TARGET) == 1
                and line.count(PRODUCER_RUN_TARGET) == 1
            ):
                allowed_occurrences += 1
                continue
        failures.append(
            "O4 live producer Make target token occurs outside its exact PHONY token "
            f"or target header: line {line_number}"
        )
    if len(run_occurrences) != 2 or allowed_occurrences != 2:
        failures.append("O4 live producer Make target occurrence allowlist is not exact")
    run_definitions = sum(
        line == f"{PRODUCER_RUN_TARGET}:" for line in makefile.splitlines()
    )
    if run_definitions != 1:
        failures.append("O4 live producer Make target header is not unique and exact")
    if _target_body(makefile, PRODUCER_RUN_TARGET).strip() != (
        PRODUCER_MODULE_INVOCATION
    ):
        failures.append("O4 live producer Make target body is not exact")
    for parent_target in (
        "release-check",
        "local-v1-milestone-check",
        PRODUCER_STATIC_TARGET,
        AUTHORIZATION_TARGET,
    ):
        if PRODUCER_RUN_TARGET in _target_body(makefile, parent_target):
            failures.append(
                f"O4 live producer target is wired into forbidden target: {parent_target}"
            )
    if "local-v1-lv1-003-o4-execution-authorization.md" not in readme:
        failures.append("README does not navigate to the O4 execution authorization")
    if "local-v1-lv1-003-o4-producer-contract.md" not in readme:
        failures.append("README does not navigate to the O4 producer contract")
    if "local-v1-lv1-003-o4-execution-authorization-check" not in readme:
        failures.append("README does not document the O4 execution authorization check")
    if "local-v1-lv1-003-o4-producer-static-check" not in readme:
        failures.append("README does not document the O4 producer static check")
    if PRODUCER_RUN_TARGET not in readme:
        failures.append("README does not document the O4 live producer entrypoint")
    if PRODUCER_MODULE_INVOCATION not in readme:
        failures.append("README does not bind the O4 module invocation")
    if "currently refuses because Attempt 001 is consumed" not in readme:
        failures.append("README does not preserve the O4 consumed-attempt refusal")


def _target_body(makefile: str, target: str) -> str:
    lines = makefile.splitlines()
    start = next(
        (index for index, line in enumerate(lines) if line.startswith(f"{target}:")),
        None,
    )
    if start is None:
        return ""
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line and not line.startswith(("\t", " ")):
            break
        body.append(line)
    return "\n".join(body).rstrip()


def _validate_git_bindings(repo_root: Path, failures: list[str]) -> None:
    for commit, expected_tree in (
        (REVIEWED_IMPLEMENTATION_COMMIT, REVIEWED_IMPLEMENTATION_TREE),
        (CODE_AUTHORIZATION_ORIGIN_COMMIT, CODE_AUTHORIZATION_ORIGIN_TREE),
        (CODE_AUTHORIZATION_COMMIT, CODE_AUTHORIZATION_TREE),
    ):
        tree = _git(repo_root, ["show", "-s", "--format=%T", commit], failures)
        if tree != expected_tree:
            failures.append(f"O4 execution bound tree is invalid for {commit}")
        ancestry = subprocess.run(
            ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", commit, "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
        if ancestry.returncode != 0:
            failures.append(f"O4 execution bound commit is not an ancestor: {commit}")
    historical = _git(
        repo_root,
        [
            "show",
            f"{CODE_AUTHORIZATION_ORIGIN_COMMIT}:{code_authorization.AUTHORIZATION}",
        ],
        failures,
        strip=False,
    )
    if historical and _digest(historical) != CODE_AUTHORIZATION_ORIGIN_RECORD_DIGEST:
        failures.append("O4 execution code authorization origin record digest is invalid")
    current_historical = _git(
        repo_root,
        [
            "show",
            f"{CODE_AUTHORIZATION_COMMIT}:{code_authorization.AUTHORIZATION}",
        ],
        failures,
        strip=False,
    )
    if current_historical and _digest(current_historical) != CODE_AUTHORIZATION_RECORD_DIGEST:
        failures.append("O4 execution bound code authorization record digest is invalid")
    current_authorization = _file_digest(
        repo_root / code_authorization.AUTHORIZATION,
        failures,
    )
    if current_authorization != CODE_AUTHORIZATION_RECORD_DIGEST:
        failures.append("O4 execution current code authorization record digest is invalid")


def _validate_attempted_candidate_binding(
    repo_root: Path,
    failures: list[str],
) -> None:
    tree = _git(
        repo_root,
        ["show", "-s", "--format=%T", ATTEMPTED_CANDIDATE_COMMIT],
        failures,
    )
    if tree != ATTEMPTED_CANDIDATE_TREE:
        failures.append("O4 Attempt 001 candidate tree is invalid")
    ancestry = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "merge-base",
            "--is-ancestor",
            ATTEMPTED_CANDIDATE_COMMIT,
            "HEAD",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if ancestry.returncode != 0:
        failures.append("O4 Attempt 001 candidate is not an ancestor of the closure")
    historical_contract = _git(
        repo_root,
        ["show", f"{ATTEMPTED_CANDIDATE_COMMIT}:{CONTRACT.as_posix()}"],
        failures,
        strip=False,
    )
    if (
        historical_contract
        and _digest(historical_contract) != ATTEMPTED_AUTHORIZATION_CONTRACT_DIGEST
    ):
        failures.append("O4 Attempt 001 authorization contract digest is invalid")


def _validate_recorded_root_absence(
    repo_root: Path,
    failures: list[str],
) -> None:
    for relative in PRIOR_ATTEMPT_ROOTS:
        try:
            (repo_root / relative).lstat()
        except FileNotFoundError:
            continue
        except OSError:
            failures.append(f"O4 Attempt 001 observed root posture is unreadable: {relative}")
            continue
        failures.append(f"O4 Attempt 001 observed-absent root is now present: {relative}")


def _validate_source_bindings(
    repo_root: Path,
    contract: JsonObject,
    failures: list[str],
) -> None:
    producer_digest = _file_digest(repo_root / PRODUCER_CONTRACT, failures)
    if producer_digest != PRODUCER_CONTRACT_DIGEST:
        failures.append("O4 execution current producer contract digest is invalid")
    if not _exact_json_equal(
        contract.get("producer_contract_sha256"),
        producer_digest,
    ):
        failures.append("O4 execution producer contract source binding is invalid")
    profile = contract.get("profile")
    if not isinstance(profile, dict):
        return
    for key, (path, expected) in SOURCE_DIGESTS.items():
        if _file_digest(repo_root / path, failures) != expected:
            failures.append(f"O4 execution current source differs for {key}")
    try:
        raw_profile = json.loads(
            (repo_root / "deploy/hermes-node-bridge/profile.json").read_text(
                encoding="utf-8"
            ),
            object_pairs_hook=_reject_duplicates,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        failures.append("O4 execution profile cannot be canonicalized")
        return
    if not isinstance(raw_profile, dict) or sha256_digest(cast(JsonObject, raw_profile)) != (
        PROFILE_DIGEST
    ):
        failures.append("O4 execution current canonical profile digest is invalid")


def _validate_current_license_discovery(
    repo_root: Path,
    failures: list[str],
) -> None:
    tracked_output = _git(
        repo_root,
        ["ls-tree", "-r", "--name-only", "HEAD"],
        failures,
    )
    if not tracked_output:
        failures.append("O4 execution tracked Git tree inventory is unavailable")
        return
    tracked_paths = tracked_output.splitlines()
    license_family_files = sorted(
        path
        for path in tracked_paths
        if Path(path).name.startswith(("LICENSE", "NOTICE", "COPYING"))
    )
    inventory_inputs = sorted(
        path for path in tracked_paths if path in {"pyproject.toml", "uv.lock"}
    )
    if inventory_inputs != ["pyproject.toml", "uv.lock"]:
        failures.append("O4 execution current license inventory inputs are not exact")
    if license_family_files:
        failures.append("O4 execution current tracked license-family files are not empty")
    for relative in inventory_inputs:
        path = repo_root / relative
        try:
            metadata = path.lstat()
        except OSError:
            failures.append(f"O4 execution license input is unavailable: {relative}")
            continue
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            failures.append(f"O4 execution license input is not a no-follow file: {relative}")
        if metadata.st_size > 1048576:
            failures.append(f"O4 execution license input exceeds size ceiling: {relative}")


def _read_contract(path: Path, failures: list[str]) -> JsonObject:
    try:
        document = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicates,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        failures.append("O4 execution authorization JSON is unavailable or ambiguous")
        return {}
    if not isinstance(document, dict):
        failures.append("O4 execution authorization JSON is not an object")
        return {}
    return cast(JsonObject, document)


def _exact_json_equal(actual: object, expected: object) -> bool:
    """Compare closed JSON values without Python's bool/int coercion."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or actual.keys() != expected.keys():
            return False
        return all(
            _exact_json_equal(actual[key], expected_value)
            for key, expected_value in expected.items()
        )
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return False
        return all(
            _exact_json_equal(actual_value, expected_value)
            for actual_value, expected_value in zip(actual, expected, strict=True)
        )
    return actual == expected


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"duplicate key: {key}")
        document[key] = value
    return document


def _read_text(path: Path, failures: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        failures.append(f"O4 execution authorization input is unavailable: {path}")
        return ""


def _file_digest(path: Path, failures: list[str]) -> str:
    try:
        return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        failures.append(f"O4 execution source is unavailable: {path}")
        return ""


def _digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def _git(
    repo_root: Path,
    arguments: list[str],
    failures: list[str],
    *,
    strip: bool = True,
) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        failures.append(f"O4 execution git command failed: {' '.join(arguments)}")
        return ""
    return result.stdout.rstrip("\n") if strip else result.stdout


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "LV1-003 O4 execution authorization check",
        f"valid: {str(report['valid']).lower()}",
        f"record_status: {report['record_status']}",
        f"attempt_id: {report['attempt_id']}",
        f"attempt_consumed: {str(report['attempt_consumed']).lower()}",
        f"retry_authorized: {str(report['retry_authorized']).lower()}",
        f"execution_attempt_budget: {report['execution_attempt_budget']}",
        f"live_execution_authorized: {str(report['live_execution_authorized']).lower()}",
        "docker_lifecycle_authorized: "
        f"{str(report['docker_lifecycle_authorized']).lower()}",
        f"provider_access_authorized: {str(report['provider_access_authorized']).lower()}",
        "o4_evidence_execution_authorized: "
        f"{str(report['o4_evidence_execution_authorized']).lower()}",
        f"new_governed_tool: {str(report['new_governed_tool']).lower()}",
        f"release_allowed: {str(report['release_allowed']).lower()}",
        f"uat_complete: {str(report['uat_complete']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def main() -> int:
    report = build_report(ROOT)
    print(render_report(report))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
