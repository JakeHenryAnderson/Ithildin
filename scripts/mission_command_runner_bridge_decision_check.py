"""Validate the review-pending MCC-007 fixed runner-bridge capability decision."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TARGET = "mission-command-runner-bridge-decision-check"
DECISION = "docs/codex/mission-command-runner-bridge-capability-decision.md"
EVALUATION = "docs/codex/mission-command-runner-bridge-candidate-evaluation.md"
EVALUATION_REVIEW = (
    "docs/codex/mission-command-runner-bridge-candidate-evaluation-internal-source-review.md"
)
START = "<!-- mission-command-runner-bridge-decision:start -->"
END = "<!-- mission-command-runner-bridge-decision:end -->"
HERMES_DIGEST = "sha256:6705aac1f41c5faca559858611ce696b760d858b73fa3b51be11599c73ba1ffc"
GOVERNED_TOOLS = ["project.structure.summary", "project.test.summary"]
BRIDGE_AFFORDANCES = ["mission.step.1", "mission.step.2", "mission.complete"]
IMPLEMENTATION_PATHS = [
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
]
FALSE_FIELDS = (
    "implementation_authorized",
    "runtime_adapter_authorized",
    "runner_bridge_authorized",
    "runner_lifecycle_authority",
    "model_provider_authority",
    "prompt_output_evidence_custody_authorized",
    "arbitrary_host_control_authorized",
    "generic_process_control_authorized",
    "shell_execution_authorized",
    "docker_socket_authorized",
    "network_non_bypass_claimed",
    "filesystem_non_bypass_claimed",
    "node_private_key_shared",
    "api_admin_token_shared",
    "provider_credential_shared",
    "gateway_api_change_authorized",
    "gateway_schema_change_authorized",
    "policy_change_authorized",
    "manifest_change_authorized",
    "new_governed_tool",
    "node_tcp_listener_authorized",
    "automatic_ambiguity_retry_authorized",
    "production_identity_authorized",
    "release_allowed",
    "production_promotion_allowed",
    "uat_complete",
    "sol_ultra_authorized",
)
EXPECTED_KEYS = {
    "document_type",
    "schema_version",
    "ticket_id",
    "decision",
    "tool_count",
    "capability_selected",
    *FALSE_FIELDS,
    "candidate_evaluation_sha256",
    "candidate_evaluation_review_sha256",
    "hermes_oci_index_digest",
    "hermes_version",
    "hermes_upstream_commit",
    "hermes_platform_digests",
    "bridge_source_identity",
    "bridge_entrypoint",
    "bridge_arguments",
    "model_provider",
    "model_base_url",
    "model_name",
    "allowed_environment_names",
    "working_directory",
    "governed_tools",
    "bridge_affordances",
    "local_protocol",
    "socket_path",
    "peer_identity",
    "state_mode",
    "state_fields",
    "max_frame_bytes",
    "operation_timeout_seconds",
    "mission_wall_time_seconds",
    "concurrency",
    "cpu_limit",
    "memory_mib",
    "pids_limit",
    "tmpfs_mib",
    "per_file_mib",
    "writable_disk_mib",
    "runner_root_filesystem_read_only",
    "runner_writable_tmpfs",
    "runner_persistent_session_volume",
    "runner_logging_driver",
    "runner_raw_logging_allowed",
    "runner_memory_enabled",
    "runner_verbose_enabled",
    "plaintext_lifetime_seconds",
    "cleanup_owner",
    "cleanup_evidence_fields",
    "failed_cleanup_blocks_retry",
    "build_identity_fields",
    "same_candidate_equality_fields",
    "o4_harness_identity_binding_required",
    "profile_input_source",
    "prompt_custody",
    "ambiguity_policy",
    "cancellation_facts",
    "evidence_fields",
    "implementation_paths",
    "exact_candidate_review_required",
    "post_review_authorization_required",
}


class DecisionContractError(ValueError):
    """Raised when the decision contract is ambiguous."""


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    decision_path = repo_root / DECISION
    evaluation_path = repo_root / EVALUATION
    review_path = repo_root / EVALUATION_REVIEW
    decision_text = _read(decision_path, failures)
    evaluation_text = _read(evaluation_path, failures)
    review_text = _read(review_path, failures)
    hermes_dockerfile = _read(repo_root / "deploy/hermes-poc/Dockerfile", failures)
    pyproject = _read(repo_root / "pyproject.toml", failures)
    try:
        decision = _contract(decision_text)
    except DecisionContractError as exc:
        failures.append(str(exc))
        decision = {}

    tool_count = _tool_count(repo_root / "tool-manifests.lock.json", failures)
    expected: dict[str, object] = {
        "document_type": "runner_bridge_capability_decision",
        "schema_version": "1",
        "ticket_id": "MCC-007",
        "decision": "fixed_hermes_node_bridge_selected_pending_exact_review",
        "tool_count": tool_count,
        "capability_selected": True,
        "candidate_evaluation_sha256": _digest(evaluation_text),
        "candidate_evaluation_review_sha256": _digest(review_text),
        "hermes_oci_index_digest": HERMES_DIGEST,
        "hermes_version": "0.18.2 (2026.7.7.2)",
        "hermes_upstream_commit": "0512f06a",
        "bridge_source_identity": (
            "repo_owned_ithildin_mcp_server_node_bridge_same_candidate"
        ),
        "bridge_entrypoint": [
            "/opt/ithildin/.venv/bin/python",
            "-m",
            "ithildin_mcp_server.node_bridge",
        ],
        "bridge_arguments": [],
        "model_provider": "custom",
        "model_base_url": "http://host.docker.internal:11434/v1",
        "model_name": "gemma4:e4b",
        "allowed_environment_names": [],
        "working_directory": "/opt/data/scratch",
        "governed_tools": GOVERNED_TOOLS,
        "bridge_affordances": BRIDGE_AFFORDANCES,
        "local_protocol": "unix_domain_socket_canonical_json_v1",
        "socket_path": "/run/ithildin-node/mission.sock",
        "peer_identity": "linux_so_peercred_uid_10000_plus_profile_digest",
        "state_mode": "0600",
        "state_fields": [
            "mission_id",
            "claim_id",
            "envelope_digest",
            "next_operation_index",
            "handoff_nonce_digest",
            "last_closed_status",
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
        "writable_disk_mib": 256,
        "runner_root_filesystem_read_only": True,
        "runner_writable_tmpfs": {
            "/opt/data/scratch": {"mib": 128, "mode": "0700"},
            "/tmp": {"mib": 128, "mode": "0700"},
        },
        "runner_persistent_session_volume": False,
        "runner_logging_driver": "none",
        "runner_raw_logging_allowed": False,
        "runner_memory_enabled": False,
        "runner_verbose_enabled": False,
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
            "persistent_profile_volume_absent",
        ],
        "failed_cleanup_blocks_retry": True,
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
            "license_receipt_digest",
        ],
        "same_candidate_equality_fields": ["candidate_commit", "candidate_tree"],
        "o4_harness_identity_binding_required": True,
        "profile_input_source": "operator_fixed_immutable_image_profile",
        "prompt_custody": "operator_fixed_profile_only_not_gateway_evidence",
        "ambiguity_policy": "no_automatic_retry_reassignment_or_finalization",
        "cancellation_facts": [
            "gateway_cancel_requested",
            "node_cancel_observed",
            "bridge_receipt",
            "runner_acknowledgment",
            "process_exit",
            "runner_reported_canceled",
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
            "observed_at",
        ],
        "implementation_paths": IMPLEMENTATION_PATHS,
        "exact_candidate_review_required": True,
        "post_review_authorization_required": True,
    }
    if set(decision) != EXPECTED_KEYS:
        failures.append("runner-bridge decision contract fields are not closed")
    for key, value in expected.items():
        if decision.get(key) != value:
            failures.append(f"runner-bridge decision {key} must equal {value!r}")
    for key in FALSE_FIELDS:
        if decision.get(key) is not False:
            failures.append(f"runner-bridge decision {key} must remain false")

    platform_digests = decision.get("hermes_platform_digests")
    if platform_digests != {
        "linux/amd64": "sha256:48420b0abcf18f9f33cfa1da4c4e8bbd4ad107a0ddc52e5fb3ebb34a9fd20149",
        "linux/arm64": "sha256:bca5bafd0292bdf0d4b4b975780e96c0ec9e428e08941a87aacddb116663ce13",
    }:
        failures.append("runner-bridge decision Hermes platform digests drifted")

    _validate_text(decision_text, evaluation_text, review_text, failures)
    if f"FROM nousresearch/hermes-agent@{HERMES_DIGEST}" not in hermes_dockerfile:
        failures.append("reviewed Hermes Dockerfile does not bind the selected OCI index")
    package_mapping = (
        'ithildin_mcp_server = "apps/mcp-server/src/ithildin_mcp_server"'
    )
    if package_mapping not in pyproject:
        failures.append("existing MCP server package mapping is unavailable for the bridge")
    _validate_wiring(repo_root, failures)
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_count": tool_count,
        "capability_selected": decision.get("capability_selected"),
        "implementation_authorized": decision.get("implementation_authorized"),
        "runner_bridge_authorized": decision.get("runner_bridge_authorized"),
        "new_governed_tool": decision.get("new_governed_tool"),
        "arbitrary_host_control_authorized": decision.get(
            "arbitrary_host_control_authorized"
        ),
        "exact_candidate_review_required": decision.get(
            "exact_candidate_review_required"
        ),
        "post_review_authorization_required": decision.get(
            "post_review_authorization_required"
        ),
    }


def _contract(text: str) -> dict[str, Any]:
    if text.count(START) != 1 or text.count(END) != 1:
        raise DecisionContractError("runner-bridge contract markers must occur exactly once")
    payload = text.split(START, 1)[1].split(END, 1)[0].strip()
    try:
        value = json.loads(payload, object_pairs_hook=_reject_duplicates)
    except (json.JSONDecodeError, DecisionContractError) as exc:
        raise DecisionContractError("runner-bridge contract must be unambiguous JSON") from exc
    if not isinstance(value, dict):
        raise DecisionContractError("runner-bridge contract must be an object")
    return value


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise DecisionContractError(f"duplicate runner-bridge contract key: {key}")
        value[key] = item
    return value


def _tool_count(path: Path, failures: list[str]) -> int:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        failures.append("tool manifest lock is unavailable")
        return -1
    manifests = value.get("manifests") if isinstance(value, dict) else None
    if not isinstance(manifests, list):
        failures.append("tool manifest lock is invalid")
        return -1
    if len(manifests) != 24:
        failures.append(f"actual governed tool count changed: {len(manifests)}")
    return len(manifests)


def _validate_text(
    decision: str,
    evaluation: str,
    review: str,
    failures: list[str],
) -> None:
    required = (
        "Implementation, runtime-adapter, runner-lifecycle, release, "
        "and UAT authority remain false",
        "three no-argument local affordances",
        "model correctness, output quality",
        "malicious process already running",
        "There is no automatic claim, handoff, operation",
        "clean-source observations before",
        "same candidate commit and tree",
        "read-only root filesystem",
        "Docker logging driver `none`",
        "no persistent session or data volume",
        "operator owns teardown and deletion",
        "failed removal blocks retry",
        "Ithildin does not enforce or claim provider-network non-bypass",
        "post-review authorization record",
    )
    for token in required:
        if token not in decision:
            failures.append(f"runner-bridge decision is missing required token: {token}")
    if "design-only candidate evaluation ready for exact-candidate review" not in evaluation:
        failures.append("runner-bridge antecedent evaluation is not the reviewed design candidate")
    review_disposition = (
        "Review disposition: "
        "`approved_for_separate_capability_decision_preparation_only`"
    )
    if review_disposition not in review:
        failures.append(
            "runner-bridge antecedent source review does not permit decision preparation"
        )


def _validate_wiring(repo_root: Path, failures: list[str]) -> None:
    makefile = _read(repo_root / "Makefile", failures)
    readme = _read(repo_root / "README.md", failures)
    docs_site = _read(repo_root / "scripts/build_docs_site.py", failures)
    review_docs = _read(repo_root / "scripts/review_docs.py", failures)
    review_index = _read(repo_root / "docs/codex/review-docs-index.md", failures)
    if not any(line.startswith(f"{TARGET}:") for line in makefile.splitlines()):
        failures.append(f"Make target is missing: {TARGET}")
    milestone_invocation = f"\t$(MAKE) {TARGET}"
    milestone_body = _target_body(makefile, "local-v1-milestone-check")
    if milestone_body.count(milestone_invocation) != 1:
        failures.append(
            "runner-bridge decision check must occur exactly once in "
            "local-v1-milestone-check"
        )
    release_dependencies = [
        dependency
        for line in makefile.splitlines()
        if line.startswith("release-check:")
        for dependency in line.split(":", 1)[1].split()
    ]
    if release_dependencies.count(TARGET) != 1:
        failures.append(
            "runner-bridge decision check must occur exactly once as a "
            "release-check dependency"
        )
    for label, text in (
        ("README", readme),
        ("docs site", docs_site),
        ("review docs", review_docs),
        ("review index", review_index),
    ):
        if DECISION not in text and Path(DECISION).name not in text:
            failures.append(f"{label} is missing the runner-bridge capability decision")


def _target_body(makefile: str, target: str) -> str:
    lines = makefile.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith(f"{target}:"):
            continue
        body: list[str] = []
        for candidate in lines[index + 1 :]:
            if candidate.startswith("\t"):
                body.append(candidate)
                continue
            if not candidate.strip():
                break
            break
        return "\n".join(body)
    return ""


def _read(path: Path, failures: list[str]) -> str:
    if not path.is_file():
        failures.append(f"missing runner-bridge input: {path}")
        return ""
    return path.read_text(encoding="utf-8")


def _digest(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "MCC-007 fixed runner-bridge capability decision check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"capability_selected: {str(report['capability_selected']).lower()}",
        f"implementation_authorized: {str(report['implementation_authorized']).lower()}",
        f"runner_bridge_authorized: {str(report['runner_bridge_authorized']).lower()}",
        f"new_governed_tool: {str(report['new_governed_tool']).lower()}",
        "arbitrary_host_control_authorized: "
        f"{str(report['arbitrary_host_control_authorized']).lower()}",
        "exact_candidate_review_required: "
        f"{str(report['exact_candidate_review_required']).lower()}",
        "post_review_authorization_required: "
        f"{str(report['post_review_authorization_required']).lower()}",
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
