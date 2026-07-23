"""Validate the current enterprise-readiness checkpoint summary."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_operator_next_action,
    enterprise_response_status_board,
    enterprise_review_send_readiness,
    mission_command_control_plane_poc_evidence_check,
    next_capability_readiness,
    packet_redaction_scan,
    review_docs,
    v1_progress_assessment,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-current-checkpoint.md"
DOC_TITLE = "Enterprise Current Checkpoint"
PRE_DISPOSITION_ACTION = "send_erg_003_and_erg_002"
POST_DISPOSITION_ACTION = "prepare_erg004_runtime_implementation_gate"
DESCRIPTOR_ONLY_PLANNING_ACTION = "prepare_erg004_descriptor_only_runtime_planning"
ERG005_TRUSTED_HOST_ACTION = "prepare_erg005_trusted_host_promotion_review"
PIS_001_PLANNING_ACTION = "execute_pis_001_threat_model_dependency_decision"
PIS_002_ENTRY_DECISION_ACTION = "prepare_pis_002_entry_decision_record"
PIS_003_ENTRY_DECISION_ACTION = "prepare_pis_003_entry_decision_record"
PIS_003_EXTERNAL_INPUT_ACTION = enterprise_operator_next_action.PIS_003_EXTERNAL_INPUT_ACTION
ALLOWED_NEXT_ACTIONS = {
    PRE_DISPOSITION_ACTION,
    POST_DISPOSITION_ACTION,
    DESCRIPTOR_ONLY_PLANNING_ACTION,
    ERG005_TRUSTED_HOST_ACTION,
    PIS_001_PLANNING_ACTION,
    PIS_002_ENTRY_DECISION_ACTION,
    PIS_003_ENTRY_DECISION_ACTION,
    PIS_003_EXTERNAL_INPUT_ACTION,
}

REQUIRED_PHRASES = [
    "Status: checked operator checkpoint",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "make enterprise-current-checkpoint",
    "Command Center closure-review dispatch and `CC-PILOT-107` UAT remain blocked",
    "Capability expansion remains blocked",
    "Runtime changes remain blocked",
    "Public/security-product positioning remains blocked",
    "Enterprise response evidence is not present yet",
    "`ERG-004`: descriptor-only sandbox/VM live POC runtime source review is locally dispositioned",
    "`ERG-005`: staging-only trusted-host promotion runtime source findings are dispositioned",
    "the `ERG-006`/`ERG-007` architecture review and disposition",
    "cleared PIS-003 environment-evidence authority",
    "external target identity and signed environment receipts are now",
    PIS_003_EXTERNAL_INPUT_ACTION,
    "The historical ERG-003/ERG-002 dual-send commands remain available only for "
    "lineage and fallback.",
    "What This Checkpoint Does Not Approve",
]

MCC_BLOCKED_PHRASES = [
    "`make review-candidate` is blocked at its required MCC-006 live-evidence precondition",
    "No valid immutable current-candidate review packet exists",
]

PACKET_BLOCKED_PHRASES = [
    "The MCC-006 precondition is valid, but the immutable current-candidate review packet is "
    "absent or invalid",
]

PACKET_READY_PHRASES = [
    "The current immutable review packet is valid for the exact source candidate",
]

BLOCKED_PHRASES = [
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "Mission Control runtime behavior",
    "local model invocation",
    "trusted-host promotion",
    "SIEM adapter runtime behavior",
    "production identity or enterprise RBAC",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP hosting",
    "compliance automation",
    "public/security-product positioning",
    "new governed tool powers",
]

FORBIDDEN_PHRASES = [
    "enterprise-ready",
    "production-ready",
    "approved for live VM",
    "Mission Control may execute",
    "sandbox orchestration allowed",
    "public security product approved",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_report(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []

    operator_next_action = enterprise_operator_next_action.build_report(repo_root)
    pis_mode = operator_next_action.get("next_action") in {
        PIS_001_PLANNING_ACTION,
        PIS_002_ENTRY_DECISION_ACTION,
        PIS_003_ENTRY_DECISION_ACTION,
        PIS_003_EXTERNAL_INPUT_ACTION,
    }
    progress = v1_progress_assessment.build_report(repo_root)
    send_readiness: dict[str, Any] = (
        {
            "failures": [],
            "tool_count": 24,
            "recommended_now": ["ERG-003", "ERG-002"],
        }
        if pis_mode
        else enterprise_review_send_readiness.build_report(repo_root)
    )
    response_status = enterprise_response_status_board.build_report(repo_root)
    capability = next_capability_readiness.build_report(repo_root)
    mcc_poc = mission_command_control_plane_poc_evidence_check.build_report(repo_root)
    current_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    immutable_packet_path = (
        repo_root
        / "var/review-packets/v0.2"
        / f"ithildin-v0.2-review-packet-{current_commit[:12]}"
    )
    immutable_packet_present = immutable_packet_path.is_dir()
    immutable_packet_valid = _immutable_packet_valid(
        immutable_packet_path,
        current_commit,
    )
    mcc_poc_valid = mcc_poc.get("valid") is True
    review_candidate_packet_ready = mcc_poc_valid and immutable_packet_valid
    if not mcc_poc_valid:
        review_candidate_blocker: str | None = (
            "missing_or_invalid_exact_candidate_mcc_006_live_evidence"
        )
        required_packet_phrases = MCC_BLOCKED_PHRASES
    elif not immutable_packet_valid:
        review_candidate_blocker = "missing_or_invalid_immutable_review_packet"
        required_packet_phrases = PACKET_BLOCKED_PHRASES
    else:
        review_candidate_blocker = None
        required_packet_phrases = PACKET_READY_PHRASES

    failures.extend(f"v1-progress-assessment: {failure}" for failure in progress["failures"])
    if not pis_mode:
        failures.extend(
            f"enterprise-review-send-readiness: {failure}"
            for failure in send_readiness["failures"]
        )
    failures.extend(
        f"enterprise-response-status-board: {failure}"
        for failure in response_status["failures"]
    )
    failures.extend(f"next-capability-readiness: {failure}" for failure in capability["failures"])
    failures.extend(
        f"enterprise-operator-next-action: {failure}"
        for failure in operator_next_action["failures"]
    )

    doc_path = repo_root / DOC_REL
    doc = _read(doc_path)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if progress.get("tool_count") != 24:
        failures.append("progress assessment tool count is not 24")
    if send_readiness.get("tool_count") != 24:
        failures.append("send-readiness tool count is not 24")
    if response_status.get("tool_count") != 24:
        failures.append("response-status tool count is not 24")
    if capability.get("next_candidate") != "not selected":
        failures.append("next capability candidate is selected")
    if mcc_poc.get("tool_count") != 24:
        failures.append("MCC-006 evidence checker tool count is not 24")
    if immutable_packet_present and not immutable_packet_valid:
        failures.append("current immutable review packet is present but invalid")
    if immutable_packet_valid and not mcc_poc_valid:
        failures.append(
            "current immutable review packet exists without valid exact-candidate MCC-006 evidence"
        )
    next_action = operator_next_action.get("next_action")
    post_disposition_mode = next_action == POST_DISPOSITION_ACTION
    descriptor_only_mode = next_action == DESCRIPTOR_ONLY_PLANNING_ACTION
    erg005_mode = next_action == ERG005_TRUSTED_HOST_ACTION
    if not post_disposition_mode and send_readiness.get("recommended_now") != [
        "ERG-003",
        "ERG-002",
    ]:
        failures.append("recommended enterprise send set must remain ERG-003 then ERG-002")
    if descriptor_only_mode and operator_next_action.get("recommended_send_set") != ["ERG-004"]:
        failures.append("operator next action must recommend ERG-004 in descriptor-only mode")
    if erg005_mode and operator_next_action.get("recommended_send_set") != ["ERG-005"]:
        failures.append(
            "operator next action must recommend ERG-005 after descriptor-only disposition"
        )
    if (
        pis_mode
        and next_action != PIS_003_EXTERNAL_INPUT_ACTION
        and operator_next_action.get("recommended_send_set") != ["ERG-006", "ERG-007"]
    ):
        failures.append(
            "operator next action must recommend ERG-006/ERG-007 after ERG-005 source disposition"
        )
    if (
        next_action == PIS_003_EXTERNAL_INPUT_ACTION
        and operator_next_action.get("recommended_send_set") != []
    ):
        failures.append("external-input wait must not recommend an enterprise send set")
    if next_action not in ALLOWED_NEXT_ACTIONS:
        failures.append("operator next action is not an allowed enterprise flow")
    if response_status.get("response_present_count") != 0:
        failures.append(
            "enterprise responses are present; intake them before using this checkpoint"
        )
    if response_status.get("closure_ready_count") != 0:
        failures.append("enterprise closures are ready; run lane-specific closure flow")

    boundary_flags = {
        "capability_expansion_allowed": False,
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "live_vm_inspection_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "compliance_automation_allowed": False,
        "public_security_product_positioning_allowed": False,
        "new_power_classes_allowed": False,
    }
    if progress.get("capability_expansion_allowed") is not False:
        failures.append("progress assessment allows capability expansion")
    if progress.get("runtime_changes_allowed") is not False:
        failures.append("progress assessment allows runtime changes")
    if progress.get("public_security_product_positioning_allowed") is not False:
        failures.append("progress assessment allows public/security-product positioning")
    for key, expected in boundary_flags.items():
        if key in send_readiness and send_readiness[key] is not expected:
            failures.append(f"send-readiness boundary flag drifted: {key}")
        if key in response_status and response_status[key] is not expected:
            failures.append(f"response-status boundary flag drifted: {key}")

    normalized_doc = " ".join(doc.split())
    for phrase in [*REQUIRED_PHRASES, *required_packet_phrases]:
        if phrase not in normalized_doc:
            failures.append(f"enterprise checkpoint doc is missing phrase: {phrase}")
    for phrase in [
        *MCC_BLOCKED_PHRASES,
        *PACKET_BLOCKED_PHRASES,
        *PACKET_READY_PHRASES,
    ]:
        if phrase not in required_packet_phrases and phrase in normalized_doc:
            failures.append(
                "enterprise checkpoint doc contradicts computed packet state: "
                f"{phrase}"
            )
    for phrase in BLOCKED_PHRASES:
        if phrase not in normalized_doc:
            failures.append(f"enterprise checkpoint doc is missing blocked phrase: {phrase}")
    lowered = doc.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(f"enterprise checkpoint doc contains forbidden phrase: {phrase}")

    if "enterprise-current-checkpoint:" not in makefile:
        failures.append("Make target is missing: enterprise-current-checkpoint")
    if "enterprise-current-checkpoint" not in release_check_body:
        failures.append("enterprise-current-checkpoint is missing from release-check")
    if "make enterprise-current-checkpoint" not in readme:
        failures.append("README is missing enterprise-current-checkpoint command")
    if DOC_REL not in readme:
        failures.append("README is missing enterprise current checkpoint doc")
    if DOC_REL not in docs_site:
        failures.append("enterprise current checkpoint is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise current checkpoint is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing enterprise current checkpoint")
    if "enterprise-current-checkpoint" not in release_guardrails:
        failures.append("release guardrails do not require enterprise current checkpoint")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "checkpoint_doc": DOC_REL,
        "tool_count": 24,
        "selected_capability": capability.get("next_candidate"),
        "recommended_send_set": operator_next_action.get(
            "recommended_send_set",
            send_readiness.get("recommended_now"),
        ),
        "recommended_next_enterprise_review": operator_next_action.get(
            "recommended_next_enterprise_review"
        ),
        "next_action": next_action,
        "action_commands": operator_next_action.get("action_commands", []),
        "next_after_send_commands": operator_next_action.get("next_after_send_commands", []),
        "handoff_artifacts": operator_next_action.get("handoff_artifacts", []),
        "operator_next_action_doc": operator_next_action.get("next_action_doc"),
        "response_present_count": response_status.get("response_present_count"),
        "closure_ready_count": response_status.get("closure_ready_count"),
        "review_candidate_prerequisite_mcc_006_valid": mcc_poc_valid,
        "review_candidate_blocker": review_candidate_blocker,
        "immutable_review_packet_path": immutable_packet_path.relative_to(repo_root).as_posix(),
        "immutable_review_packet_present": immutable_packet_present,
        "immutable_review_packet_valid": immutable_packet_valid,
        "review_candidate_packet_ready": review_candidate_packet_ready,
        "closure_review_dispatch_allowed": False,
        "human_uat_allowed": False,
        **boundary_flags,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise current checkpoint",
        f"valid: {str(report['valid']).lower()}",
        f"checkpoint_doc: {report['checkpoint_doc']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report.get('selected_capability', 'unknown')}",
        "recommended_send_set: " + ", ".join(report.get("recommended_send_set") or []),
        "recommended_next_enterprise_review: "
        f"{report.get('recommended_next_enterprise_review', 'unknown')}",
        f"next_action: {report.get('next_action', 'unknown')}",
        "action_commands:",
        *[f"- {command}" for command in report.get("action_commands", [])],
        "next_after_send_commands:",
        *[f"- {command}" for command in report.get("next_after_send_commands", [])],
        "handoff_artifacts:",
        *[
            f"- {artifact['label']}: {artifact['path']}"
            for artifact in report.get("handoff_artifacts", [])
        ],
        f"response_present_count: {report.get('response_present_count', 'unknown')}",
        f"closure_ready_count: {report.get('closure_ready_count', 'unknown')}",
        "review_candidate_prerequisite_mcc_006_valid: "
        f"{str(report['review_candidate_prerequisite_mcc_006_valid']).lower()}",
        f"review_candidate_blocker: {report.get('review_candidate_blocker') or ''}",
        f"immutable_review_packet_path: {report['immutable_review_packet_path']}",
        "immutable_review_packet_present: "
        f"{str(report['immutable_review_packet_present']).lower()}",
        f"immutable_review_packet_valid: {str(report['immutable_review_packet_valid']).lower()}",
        f"review_candidate_packet_ready: {str(report['review_candidate_packet_ready']).lower()}",
        "closure_review_dispatch_allowed: "
        f"{str(report['closure_review_dispatch_allowed']).lower()}",
        f"human_uat_allowed: {str(report['human_uat_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"compliance_automation_allowed: {str(report['compliance_automation_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _immutable_packet_valid(packet_path: Path, current_commit: str) -> bool:
    required_paths = {
        "artifact-hashes.json",
        "git-summary.txt",
        "packet-redaction-scan.txt",
        "release-check.txt",
    }
    try:
        packet_absolute = packet_path.absolute()
        packet_resolved = packet_path.resolve(strict=True)
    except OSError:
        return False
    if (
        not packet_path.is_dir()
        or packet_path.is_symlink()
        or packet_resolved != packet_absolute
        or packet_path.name != f"ithildin-v0.2-review-packet-{current_commit[:12]}"
        or not all(
            packet_path.joinpath(relative).is_file()
            and not packet_path.joinpath(relative).is_symlink()
            for relative in required_paths
        )
    ):
        return False

    try:
        git_summary = packet_path.joinpath("git-summary.txt").read_text(encoding="utf-8")
        release_check = packet_path.joinpath("release-check.txt").read_text(encoding="utf-8")
        redaction_scan = packet_path.joinpath("packet-redaction-scan.txt").read_text(
            encoding="utf-8"
        )
        artifact_hashes = json.loads(
            packet_path.joinpath("artifact-hashes.json").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False

    git_summary_lines = git_summary.splitlines()
    git_summary_commit_lines = [
        line.strip()
        for line in git_summary_lines
        if line.strip().startswith("commit=")
    ]
    git_summary_dirty_lines = [
        line.strip()
        for line in git_summary_lines
        if line.strip().startswith("dirty=")
    ]
    release_lines = release_check.splitlines()
    release_commit_lines = [
        line.strip()
        for line in release_lines
        if line.strip().startswith("git_commit=")
    ]
    release_dirty_lines = [
        line.strip()
        for line in release_lines
        if line.strip().startswith("git_dirty=")
    ]
    release_returncodes = [
        line.strip()
        for line in release_lines
        if line.strip().startswith("returncode=")
    ]
    if (
        git_summary_commit_lines != [f"commit={current_commit}"]
        or git_summary_dirty_lines != ["dirty=false"]
        or not release_lines
        or release_lines[0] != "$ make release-check"
        or release_commit_lines != [f"git_commit={current_commit}"]
        or release_dirty_lines != ["git_dirty=false"]
        or release_returncodes != ["returncode=0"]
        or release_lines[-1] != "returncode=0"
        or "findings: `0`" not in redaction_scan
        or "Packet redaction scan passed." not in redaction_scan
        or not isinstance(artifact_hashes, list)
    ):
        return False

    manifest_paths: set[str] = set()
    for item in artifact_hashes:
        if not isinstance(item, dict):
            return False
        relative = item.get("path")
        expected_sha256 = item.get("sha256")
        expected_bytes = item.get("bytes")
        if (
            not isinstance(relative, str)
            or not isinstance(expected_sha256, str)
            or type(expected_bytes) is not int
        ):
            return False
        relative_path = Path(relative)
        if (
            relative in manifest_paths
            or not relative_path.parts
            or relative_path.is_absolute()
            or ".." in relative_path.parts
            or relative_path.as_posix() != relative
            or relative == "artifact-hashes.json"
        ):
            return False
        artifact_path = packet_path / relative_path
        try:
            artifact_resolved = artifact_path.resolve(strict=True)
        except OSError:
            return False
        if (
            not artifact_path.is_file()
            or artifact_path.is_symlink()
            or artifact_resolved != artifact_path.absolute()
            or not artifact_resolved.is_relative_to(packet_resolved)
        ):
            return False
        try:
            content = artifact_path.read_bytes()
        except OSError:
            return False
        if len(content) != expected_bytes:
            return False
        if f"sha256:{hashlib.sha256(content).hexdigest()}" != expected_sha256:
            return False
        manifest_paths.add(relative)

    disk_paths: set[str] = set()
    for path in packet_path.rglob("*"):
        if path.is_symlink():
            return False
        if path.is_file():
            disk_paths.add(path.relative_to(packet_path).as_posix())
        elif not path.is_dir():
            return False
    if manifest_paths | {"artifact-hashes.json"} != disk_paths:
        return False
    if not required_paths.difference({"artifact-hashes.json"}).issubset(manifest_paths):
        return False

    roots_match = re.search(r"(?m)^roots: `1`$", redaction_scan) is not None
    scanned_match = re.search(r"(?m)^scanned_files: `(\d+)`$", redaction_scan)
    if (
        not roots_match
        or scanned_match is None
        or int(scanned_match.group(1)) != len(disk_paths) - 2
    ):
        return False
    try:
        current_redaction = packet_redaction_scan.scan_packet_paths([packet_path])
    except packet_redaction_scan.PacketRedactionScanError:
        return False
    return (
        not current_redaction.findings
        and current_redaction.scanned_files == len(disk_paths)
        and current_redaction.roots == [packet_resolved.as_posix()]
    )


if __name__ == "__main__":
    raise SystemExit(main())
