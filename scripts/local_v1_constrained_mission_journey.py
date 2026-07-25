"""Assemble closed, candidate-bound evidence for a separately authorized O4 journey.

This command never starts, stops, or inspects Docker, Hermes, a provider, or a Node. It consumes
only closed build and journey receipts produced by a separately authorized operator workflow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import stat
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from ithildin_schemas import JsonObject, canonical_json, sha256_digest

ROOT = Path(__file__).resolve().parents[1]
REPORT_BASE = ROOT / "var/local-v1-constrained-mission-journey"
PROFILE_PATH = ROOT / "deploy/hermes-node-bridge/profile.json"
BRIDGE_SOURCE_PATHS = (
    ROOT / "apps/mcp-server/src/ithildin_mcp_server/node_bridge.py",
)
NODE_SOURCE_PATHS = (
    ROOT / "apps/node/src/ithildin_node/client.py",
    ROOT / "apps/node/src/ithildin_node/service.py",
    ROOT / "apps/node/src/ithildin_node/fixed_runner_bridge.py",
)
REPORT_JSON = "report.json"
REPORT_MARKDOWN = "report.md"

_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_TREE = _COMMIT
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_RUN_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
_MISSION_ID = re.compile(r"^mission_[0-9a-f]{32}$")
_CLAIM_ID = re.compile(r"^mclaim_[0-9a-f]{32}$")
_AGENT_RUN_ID = re.compile(r"^run_[0-9a-f]{32}$")
_REQUEST_ID = re.compile(r"^req_[0-9a-f]{32}$")
_EVENT_ID = re.compile(r"^evt_[0-9a-f]{32}$")
_MISSION_SESSION = re.compile(
    r"^mission:mission_[0-9a-f]{32}:mclaim_[0-9a-f]{32}:[0-9a-f]{16}$"
)
_SAFE_PLATFORM = re.compile(r"^linux/(amd64|arm64)$")
_FORBIDDEN_TEXT = re.compile(
    r"(?:authorization|bearer|chain.of.thought|credential|private[_ -]?key|"
    r"prompt(?:_text)?|provider[_ -]?secret|raw[_ -]?(?:output|result)|token)",
    re.IGNORECASE,
)
_BUILD_KEYS = {
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
    "image_artifact_inventory_digest",
    "license_source_inventory_digest",
}
_JOURNEY_KEYS = {
    "candidate_commit",
    "candidate_tree",
    "mission_id",
    "claim_id",
    "envelope_digest",
    "profile_digest",
    "handoff_nonce_digest",
    "authority",
    "correlation_basis",
    "rejected_correlation_count",
    "mission_session_id",
    "gateway_agent_runs",
    "gateway_operation_bindings",
    "gateway_lifecycle_state",
    "runner_state_authority",
    "model_provider_state_known",
    "container_absent",
    "volumes_absent",
    "network_absent",
    "persistent_profile_volume_absent",
    "run_specific_images_absent",
    "runtime_plaintext_absent",
    "read_only_root",
    "logging_driver",
    "tmpfs_limits",
}


class ConstrainedJourneyError(RuntimeError):
    """Safe closed error for the evidence-only journey assembler."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--build-receipt", type=Path, required=True)
    parser.add_argument("--journey-receipt", type=Path, required=True)
    parser.add_argument("--expected-reviewed-candidate", required=True)
    args = parser.parse_args()
    try:
        commit, tree = current_clean_candidate()
        if args.expected_reviewed_candidate != commit:
            raise ConstrainedJourneyError("current candidate is not the reviewed candidate")
        build = read_closed_receipt(args.build_receipt)
        journey = read_closed_receipt(args.journey_receipt)
        report = build_report(
            build,
            journey,
            expected_candidate=commit,
            expected_tree=tree,
        )
        report_root = write_report(report)
    except ConstrainedJourneyError as exc:
        print(f"Constrained mission journey refused: {exc}", file=sys.stderr)
        return 1
    print(f"Constrained mission journey evidence assembled: {report_root}")
    print(
        "Check with: python3 scripts/local_v1_constrained_mission_journey_check.py "
        f"--report-root {report_root.relative_to(ROOT)} "
        f"--expected-candidate {report['candidate_commit']}"
    )
    return 0


def current_clean_candidate() -> tuple[str, str]:
    commit = _git("rev-parse", "HEAD")
    tree = _git("rev-parse", "HEAD^{tree}")
    if not _COMMIT.fullmatch(commit) or not _TREE.fullmatch(tree):
        raise ConstrainedJourneyError("candidate identity is invalid")
    if _git("status", "--porcelain", "--untracked-files=all"):
        raise ConstrainedJourneyError("candidate source is dirty")
    return commit, tree


def read_closed_receipt(path: Path) -> JsonObject:
    selected = path if path.is_absolute() else ROOT / path
    parent_descriptor = _open_private_directory(selected.parent)
    try:
        descriptor = os.open(
            selected.name,
            _file_flags(os.O_RDONLY),
            dir_fd=parent_descriptor,
        )
    except OSError as exc:
        os.close(parent_descriptor)
        raise ConstrainedJourneyError("selected receipt is unavailable") from exc
    try:
        details = os.fstat(descriptor)
        if (
            not stat.S_ISREG(details.st_mode)
            or stat.S_IMODE(details.st_mode) != 0o600
            or details.st_uid != os.geteuid()
            or details.st_gid != os.getegid()
        ):
            raise ConstrainedJourneyError(
                "selected receipt must be an owner-only regular file"
            )
        raw_bytes = os.read(descriptor, 1_048_577)
    finally:
        os.close(descriptor)
        os.close(parent_descriptor)
    if len(raw_bytes) > 1_048_576:
        raise ConstrainedJourneyError("selected receipt is too large")
    try:
        text = raw_bytes.decode("utf-8")
        raw = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ConstrainedJourneyError("selected receipt is invalid") from exc
    if not isinstance(raw, dict):
        raise ConstrainedJourneyError("selected receipt must be an object")
    if _FORBIDDEN_TEXT.search(text):
        raise ConstrainedJourneyError("selected receipt contains forbidden custody fields")
    return cast(JsonObject, raw)


def build_report(
    build: JsonObject,
    journey: JsonObject,
    *,
    expected_candidate: str,
    expected_tree: str,
    observed_at: datetime | None = None,
    run_id: str | None = None,
    source_root: Path = ROOT,
    source_evidence: JsonObject | None = None,
) -> JsonObject:
    if set(build) != _BUILD_KEYS or set(journey) != _JOURNEY_KEYS:
        raise ConstrainedJourneyError("receipt shape is not closed")
    if not _COMMIT.fullmatch(expected_candidate) or not _TREE.fullmatch(expected_tree):
        raise ConstrainedJourneyError("expected candidate identity is invalid")
    if any(build.get(key) is not True for key in {
        "clean_before_bridge_build",
        "clean_after_bridge_build",
        "clean_before_node_build",
        "clean_after_node_build",
    }):
        raise ConstrainedJourneyError("build receipt has a dirty source observation")
    if (
        build.get("candidate_commit") != expected_candidate
        or journey.get("candidate_commit") != expected_candidate
        or build.get("candidate_tree") != expected_tree
        or journey.get("candidate_tree") != expected_tree
    ):
        raise ConstrainedJourneyError("candidate or tree identity differs")
    evidence = source_evidence or candidate_source_evidence(source_root)
    profile = cast(JsonObject, evidence["profile"])
    profile_digest = sha256_digest(profile)
    expected_bridge_source = evidence["bridge_source_digest"]
    expected_node_source = evidence["node_source_digest"]
    expected_lock_digest = evidence["dependency_lock_digest"]
    for field, expected in {
        "profile_digest": profile_digest,
        "bridge_source_digest": expected_bridge_source,
        "node_source_digest": expected_node_source,
        "dependency_lock_digest": expected_lock_digest,
    }.items():
        if build.get(field) != expected:
            raise ConstrainedJourneyError(f"build {field} differs from candidate")
    if journey.get("profile_digest") != profile_digest:
        raise ConstrainedJourneyError("journey profile differs from candidate")
    _validate_build_receipt(
        build,
        profile,
        hermes_config_digest=cast(str, evidence["hermes_config_digest"]),
    )
    _validate_journey_receipt(journey, profile)
    effective_now = (observed_at or datetime.now(UTC)).astimezone(UTC)
    effective_run_id = run_id or (
        effective_now.strftime("%Y%m%dT%H%M%SZ") + f"-{secrets.token_hex(4)}"
    )
    if not _RUN_ID.fullmatch(effective_run_id):
        raise ConstrainedJourneyError("run ID is invalid")
    report: JsonObject = {
        "document_type": "local_v1_constrained_mission_journey_evidence",
        "schema_version": "1",
        "run_id": effective_run_id,
        "observed_at": effective_now.isoformat(),
        "candidate_commit": expected_candidate,
        "candidate_tree": expected_tree,
        "build": build,
        "journey": journey,
        "evidence_limits": {
            "live_execution_authorized_by_report": False,
            "release_allowed": False,
            "production_promotion_allowed": False,
            "uat_complete": False,
            "runner_behavior_proven": False,
            "model_provider_state_known": False,
            "network_non_bypass_claimed": False,
            "filesystem_non_bypass_claimed": False,
        },
    }
    validate_report(
        report,
        expected_candidate=expected_candidate,
        source_root=source_root,
        source_evidence=evidence,
    )
    return report


def validate_report(
    report: JsonObject,
    *,
    expected_candidate: str,
    source_root: Path = ROOT,
    source_evidence: JsonObject | None = None,
) -> None:
    if set(report) != {
        "document_type",
        "schema_version",
        "run_id",
        "observed_at",
        "candidate_commit",
        "candidate_tree",
        "build",
        "journey",
        "evidence_limits",
    }:
        raise ConstrainedJourneyError("report shape is not closed")
    if (
        report.get("document_type") != "local_v1_constrained_mission_journey_evidence"
        or report.get("schema_version") != "1"
        or report.get("candidate_commit") != expected_candidate
        or not isinstance(report.get("candidate_tree"), str)
        or not _TREE.fullmatch(cast(str, report["candidate_tree"]))
        or not isinstance(report.get("run_id"), str)
        or not _RUN_ID.fullmatch(cast(str, report["run_id"]))
    ):
        raise ConstrainedJourneyError("report identity is invalid")
    build = report.get("build")
    journey = report.get("journey")
    limits = report.get("evidence_limits")
    if not isinstance(build, dict) or not isinstance(journey, dict) or not isinstance(limits, dict):
        raise ConstrainedJourneyError("report sections are invalid")
    if set(build) != _BUILD_KEYS or set(journey) != _JOURNEY_KEYS:
        raise ConstrainedJourneyError("report receipt shape is not closed")
    candidate_tree = cast(str, report["candidate_tree"])
    if (
        build.get("candidate_commit") != expected_candidate
        or journey.get("candidate_commit") != expected_candidate
        or build.get("candidate_tree") != candidate_tree
        or journey.get("candidate_tree") != candidate_tree
        or any(
            build.get(key) is not True
            for key in {
                "clean_before_bridge_build",
                "clean_after_bridge_build",
                "clean_before_node_build",
                "clean_after_node_build",
            }
        )
    ):
        raise ConstrainedJourneyError("report candidate build binding is invalid")
    evidence = source_evidence or candidate_source_evidence(source_root)
    profile = cast(JsonObject, evidence["profile"])
    if (
        build.get("profile_digest") != sha256_digest(profile)
        or journey.get("profile_digest") != sha256_digest(profile)
        or build.get("bridge_source_digest") != evidence["bridge_source_digest"]
        or build.get("node_source_digest") != evidence["node_source_digest"]
        or build.get("dependency_lock_digest") != evidence["dependency_lock_digest"]
    ):
        raise ConstrainedJourneyError("report source or profile binding is invalid")
    _validate_build_receipt(
        build,
        profile,
        hermes_config_digest=cast(str, evidence["hermes_config_digest"]),
    )
    _validate_journey_receipt(journey, profile)
    false_limits = {
        "live_execution_authorized_by_report",
        "release_allowed",
        "production_promotion_allowed",
        "uat_complete",
        "runner_behavior_proven",
        "model_provider_state_known",
        "network_non_bypass_claimed",
        "filesystem_non_bypass_claimed",
    }
    if set(limits) != false_limits or any(limits.get(key) is not False for key in false_limits):
        raise ConstrainedJourneyError("report evidence limits are invalid")
    serialized = canonical_json(report)
    if _FORBIDDEN_TEXT.search(serialized):
        raise ConstrainedJourneyError("report contains forbidden custody fields")


def write_report(report: JsonObject) -> Path:
    run_id = cast(str, report["run_id"])
    try:
        REPORT_BASE.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError as exc:
        raise ConstrainedJourneyError("report base is unavailable") from exc
    base_descriptor = _open_private_directory(REPORT_BASE)
    report_root = REPORT_BASE / run_id
    try:
        os.mkdir(run_id, mode=0o700, dir_fd=base_descriptor)
        run_descriptor = os.open(run_id, _directory_flags(), dir_fd=base_descriptor)
    except FileExistsError as exc:
        os.close(base_descriptor)
        raise ConstrainedJourneyError("report run already exists") from exc
    except OSError as exc:
        os.close(base_descriptor)
        raise ConstrainedJourneyError("report run creation failed") from exc
    try:
        details = os.fstat(run_descriptor)
        if (
            not stat.S_ISDIR(details.st_mode)
            or stat.S_IMODE(details.st_mode) != 0o700
            or details.st_uid != os.geteuid()
            or details.st_gid != os.getegid()
        ):
            raise ConstrainedJourneyError("report run directory is unsafe")
        _write_new_private_at(
            run_descriptor,
            REPORT_JSON,
            canonical_json(report),
        )
        _write_new_private_at(
            run_descriptor,
            REPORT_MARKDOWN,
            render_markdown(report),
        )
        os.fsync(run_descriptor)
        os.fsync(base_descriptor)
    finally:
        os.close(run_descriptor)
        os.close(base_descriptor)
    return report_root


def render_markdown(report: JsonObject) -> str:
    build = cast(JsonObject, report["build"])
    journey = cast(JsonObject, report["journey"])
    return "\n".join(
        [
            "# Local-v1 Constrained Mission Journey Evidence",
            "",
            f"- Run: `{report['run_id']}`",
            f"- Candidate: `{report['candidate_commit']}`",
            f"- Tree: `{report['candidate_tree']}`",
            f"- Profile: `{build['profile_digest']}`",
            f"- Mission: `{journey['mission_id']}`",
            f"- Gateway lifecycle: `{journey['gateway_lifecycle_state']}`",
            "- Agent Run authority: `gateway_agent_run_evidence`",
            "- Correlation basis: `gateway_validated_claim_session`",
            "- Rejected correlations: `0`",
            "- Correlated Agent Runs: `1` active record with two Gateway-completed events",
            "- Image artifact inventory is bounded metadata, not an SBOM",
            "- License-source inventory makes no completeness or compliance claim",
            "- Runner behavior proven: `false`",
            "- Model-provider state known: `false`",
            "- Release allowed: `false`",
            "- UAT complete: `false`",
            "",
        ]
    )


def source_digest(paths: tuple[Path, ...], *, source_root: Path = ROOT) -> str:
    material: JsonObject = {
        str(path.relative_to(source_root)): file_digest(path) for path in sorted(paths)
    }
    return sha256_digest(material)


def candidate_source_evidence(source_root: Path = ROOT) -> JsonObject:
    profile = _json_object(source_root / PROFILE_PATH.relative_to(ROOT))
    evidence: JsonObject = {
        "profile": profile,
        "bridge_source_digest": source_digest(
            tuple(source_root / path.relative_to(ROOT) for path in BRIDGE_SOURCE_PATHS),
            source_root=source_root,
        ),
        "node_source_digest": source_digest(
            tuple(source_root / path.relative_to(ROOT) for path in NODE_SOURCE_PATHS),
            source_root=source_root,
        ),
        "dependency_lock_digest": file_digest(source_root / "uv.lock"),
        "hermes_config_digest": file_digest(
            source_root / "deploy/hermes-node-bridge/config.yaml"
        ),
    }
    if set(evidence) != {
        "profile",
        "bridge_source_digest",
        "node_source_digest",
        "dependency_lock_digest",
        "hermes_config_digest",
    }:
        raise ConstrainedJourneyError("candidate source evidence is invalid")
    return evidence


def file_digest(path: Path) -> str:
    try:
        return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ConstrainedJourneyError("candidate source file is unavailable") from exc


def _validate_build_receipt(
    build: JsonObject,
    profile: JsonObject,
    *,
    hermes_config_digest: str,
) -> None:
    digest_fields = _BUILD_KEYS - {
        "candidate_commit",
        "candidate_tree",
        "clean_before_bridge_build",
        "clean_after_bridge_build",
        "clean_before_node_build",
        "clean_after_node_build",
        "platform",
    }
    if any(
        not isinstance(build.get(field), str)
        or not _DIGEST.fullmatch(cast(str, build[field]))
        for field in digest_fields
    ):
        raise ConstrainedJourneyError("build receipt digest is invalid")
    platform = build.get("platform")
    if not isinstance(platform, str) or not _SAFE_PLATFORM.fullmatch(platform):
        raise ConstrainedJourneyError("build platform is invalid")
    if profile.get("hermes_config_digest") != hermes_config_digest:
        raise ConstrainedJourneyError("Hermes configuration differs from profile")
    hermes = cast(JsonObject, profile["hermes"])
    platform_digests = cast(JsonObject, hermes["platform_digests"])
    if (
        build.get("hermes_oci_index_digest") != hermes.get("oci_index_digest")
        or build.get("hermes_platform_digest") != platform_digests.get(platform)
    ):
        raise ConstrainedJourneyError("Hermes provenance differs from profile")


def _validate_journey_receipt(journey: JsonObject, profile: JsonObject) -> None:
    for field, pattern in {
        "mission_id": _MISSION_ID,
        "claim_id": _CLAIM_ID,
        "envelope_digest": _DIGEST,
        "profile_digest": _DIGEST,
        "handoff_nonce_digest": _DIGEST,
    }.items():
        value = journey.get(field)
        if not isinstance(value, str) or not pattern.fullmatch(value):
            raise ConstrainedJourneyError(f"journey {field} is invalid")
    mission_id = cast(str, journey["mission_id"])
    claim_id = cast(str, journey["claim_id"])
    envelope_digest = cast(str, journey["envelope_digest"])
    expected_session = (
        f"mission:{mission_id}:{claim_id}:"
        f"{envelope_digest.removeprefix('sha256:')[:16]}"
    )
    if (
        journey.get("authority") != "gateway_agent_run_evidence"
        or journey.get("correlation_basis") != "gateway_validated_claim_session"
        or type(journey.get("rejected_correlation_count")) is not int
        or journey.get("rejected_correlation_count") != 0
        or journey.get("mission_session_id") != expected_session
        or not _MISSION_SESSION.fullmatch(expected_session)
    ):
        raise ConstrainedJourneyError("Gateway Agent Run authority or correlation is invalid")
    agent_runs = journey.get("gateway_agent_runs")
    if not isinstance(agent_runs, list) or len(agent_runs) != 1:
        raise ConstrainedJourneyError("journey must bind exactly one correlated Agent Run")
    agent_run = agent_runs[0]
    if not isinstance(agent_run, dict):
        raise ConstrainedJourneyError("correlated Agent Run binding is invalid")
    expected_run_keys = {
        "run_id",
        "session_id",
        "mission_id",
        "claim_id",
        "envelope_digest",
        "authority",
        "correlation_basis",
        "tool_call_count",
        "status",
    }
    run_id = agent_run.get("run_id")
    if (
        set(agent_run) != expected_run_keys
        or not isinstance(run_id, str)
        or not _AGENT_RUN_ID.fullmatch(run_id)
        or agent_run.get("session_id") != expected_session
        or agent_run.get("mission_id") != mission_id
        or agent_run.get("claim_id") != claim_id
        or agent_run.get("envelope_digest") != envelope_digest
        or agent_run.get("authority") != "gateway_agent_run_evidence"
        or agent_run.get("correlation_basis") != "gateway_validated_claim_session"
        or type(agent_run.get("tool_call_count")) is not int
        or agent_run.get("tool_call_count") != 2
        or agent_run.get("status") != "active"
    ):
        raise ConstrainedJourneyError("correlated Agent Run binding is invalid")
    operation_bindings = journey.get("gateway_operation_bindings")
    expected_tools = ["project.structure.summary", "project.test.summary"]
    if not isinstance(operation_bindings, list) or len(operation_bindings) != 2:
        raise ConstrainedJourneyError("Gateway operation bindings are incomplete")
    request_ids: set[str] = set()
    event_ids: set[str] = set()
    event_hashes: set[str] = set()
    for index, (binding, tool_name) in enumerate(
        zip(operation_bindings, expected_tools, strict=True),
        start=1,
    ):
        if not isinstance(binding, dict):
            raise ConstrainedJourneyError("Gateway operation binding is invalid")
        request_id = binding.get("request_id")
        event_id = binding.get("event_id")
        event_hash = binding.get("event_hash")
        if (
            set(binding)
            != {
                "operation_index",
                "event_id",
                "event_hash",
                "event_type",
                "tool_name",
                "request_id",
                "run_id",
                "session_id",
                "mission_id",
                "claim_id",
                "envelope_digest",
                "authority",
                "correlation_basis",
                "status",
            }
            or type(binding.get("operation_index")) is not int
            or binding.get("operation_index") != index
            or not isinstance(event_id, str)
            or not _EVENT_ID.fullmatch(event_id)
            or not isinstance(event_hash, str)
            or not _DIGEST.fullmatch(event_hash)
            or binding.get("event_type") != "tool.execution.completed"
            or binding.get("tool_name") != tool_name
            or not isinstance(request_id, str)
            or not _REQUEST_ID.fullmatch(request_id)
            or binding.get("run_id") != run_id
            or binding.get("session_id") != expected_session
            or binding.get("mission_id") != mission_id
            or binding.get("claim_id") != claim_id
            or binding.get("envelope_digest") != envelope_digest
            or binding.get("authority") != "gateway_agent_run_evidence"
            or binding.get("correlation_basis") != "gateway_validated_claim_session"
            or binding.get("status") != "completed"
        ):
            raise ConstrainedJourneyError("Gateway operation binding is invalid")
        request_ids.add(request_id)
        event_ids.add(event_id)
        event_hashes.add(event_hash)
    if len(request_ids) != 2 or len(event_ids) != 2 or len(event_hashes) != 2:
        raise ConstrainedJourneyError("Gateway operation event binding is ambiguous")
    tmpfs = cast(JsonObject, cast(JsonObject, profile["limits"])["tmpfs"])
    if (
        journey.get("gateway_lifecycle_state") != "runner_reported_succeeded"
        or journey.get("runner_state_authority") != "runner_reported_only"
        or journey.get("model_provider_state_known") is not False
        or journey.get("container_absent") is not True
        or journey.get("volumes_absent") is not True
        or journey.get("network_absent") is not True
        or journey.get("persistent_profile_volume_absent") is not True
        or journey.get("run_specific_images_absent") is not True
        or journey.get("runtime_plaintext_absent") is not True
        or journey.get("read_only_root") is not True
        or journey.get("logging_driver") != "none"
        or journey.get("tmpfs_limits") != tmpfs
    ):
        raise ConstrainedJourneyError("journey posture or cleanup is incomplete")


def _json_object(path: Path) -> JsonObject:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConstrainedJourneyError("candidate profile is invalid") from exc
    if not isinstance(raw, dict):
        raise ConstrainedJourneyError("candidate profile is invalid")
    return cast(JsonObject, raw)


def _git(*arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ConstrainedJourneyError("candidate Git identity is unavailable") from exc
    return result.stdout.strip()


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise ConstrainedJourneyError("selected receipt has duplicate keys")
        document[key] = value
    return document


def _write_new_private_at(parent_descriptor: int, name: str, text: str) -> None:
    try:
        descriptor = os.open(
            name,
            _file_flags(os.O_WRONLY | os.O_CREAT | os.O_EXCL),
            0o600,
            dir_fd=parent_descriptor,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise ConstrainedJourneyError("report write failed") from exc


def _open_private_directory(path: Path) -> int:
    if not path.is_absolute():
        raise ConstrainedJourneyError("selected directory path must be absolute")
    try:
        descriptor = os.open(path, _directory_flags())
    except OSError as exc:
        raise ConstrainedJourneyError("selected directory is unavailable") from exc
    details = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(details.st_mode)
        or stat.S_IMODE(details.st_mode) != 0o700
        or details.st_uid != os.geteuid()
        or details.st_gid != os.getegid()
    ):
        os.close(descriptor)
        raise ConstrainedJourneyError("selected directory is unsafe")
    return descriptor


def _directory_flags() -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    return flags


def _file_flags(base: int) -> int:
    flags = base
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    return flags


if __name__ == "__main__":
    raise SystemExit(main())
