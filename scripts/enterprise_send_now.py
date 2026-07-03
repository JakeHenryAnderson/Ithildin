"""Print the current enterprise external-review send instructions."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (  # noqa: E402
    artifact_freshness_check,
    enterprise_operator_next_action,
)

ROOT = Path(__file__).resolve().parents[1]
UPLOAD_STAGING_JSON = Path(
    "var/review-packets/v3/enterprise-review-upload-staging/"
    "enterprise-review-upload-staging.json"
)
DUAL_RESPONSE_INBOX_JSON = Path(
    "var/review-runs/enterprise-dual-response-inbox/enterprise-dual-response-inbox.json"
)
ERG004_SOURCE_REVIEW_DIR = Path(
    "var/review-packets/v3/sandbox-vm-live-poc-runtime-descriptor-only-source-review"
)
ERG004_SOURCE_REVIEW_HASHES = (
    "sandbox-vm-live-poc-runtime-descriptor-only-source-artifact-hashes.json"
)
ERG004_RESPONSE_INBOX_JSON = Path(
    "var/review-runs/sandbox-vm-live-poc-runtime-descriptor-only-response-inbox/"
    "erg004-runtime-descriptor-only-response-inbox.json"
)
DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/enterprise-send-now")
JSON_NAME = "enterprise-send-now.json"
MD_NAME = "ENTERPRISE_SEND_NOW.md"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true", help="write ignored JSON/Markdown output")
    parser.add_argument("--check", action="store_true", help="validate generated artifact wiring")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    if args.check:
        report = build_check_report(ROOT, args.output_dir)
    elif args.write:
        report = build_artifact(ROOT, args.output_dir)
    else:
        report = build_report(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path) -> dict[str, Any]:
    freshness = artifact_freshness_check.build_report(repo_root)
    next_action = enterprise_operator_next_action.build_report(repo_root)
    if next_action.get("recommended_send_set") == ["ERG-004"]:
        return _build_erg004_report(repo_root, freshness, next_action)

    upload = _read_json(repo_root / UPLOAD_STAGING_JSON)
    inbox = _read_json(repo_root / DUAL_RESPONSE_INBOX_JSON)
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    lanes = _lane_reports(upload, inbox)
    failures = _failures(freshness, upload, inbox, commit, lanes)
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "commit": commit,
        "dirty": bool(_git(repo_root, ["status", "--short"])),
        "tool_count": upload.get("tool_count"),
        "selected_capability": upload.get("selected_capability"),
        "current_send_set": upload.get("recommended_gaps", []),
        "recommended_gaps": upload.get("recommended_gaps", []),
        "upload_staging_path": UPLOAD_STAGING_JSON.parent.as_posix(),
        "response_inbox_path": DUAL_RESPONSE_INBOX_JSON.parent.as_posix(),
        "send_now_artifact_path": DEFAULT_OUTPUT_DIR.as_posix(),
        "lane_count": len(lanes),
        "batch_count": sum(len(lane["batches"]) for lane in lanes),
        "lanes": lanes,
        "next_after_send": [
            "make enterprise-review-send-receipt-copy after the human send step",
            "fill the copied receipt after the human send step",
            "make enterprise-review-send-receipt-validate RECEIPT=path/to/copied-receipt.json",
            "make enterprise-response-waiting-room",
            "make enterprise-response-now",
            "make enterprise-response-paste-preflight after reviewer responses are pasted",
        ],
        "records_external_review": False,
        "normalizes_responses": False,
        "writes_response_files": False,
        "closes_erg_003": False,
        "closes_erg_002": False,
        "closes_erg_004": False,
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "live_vm_inspection_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "compliance_automation_allowed": False,
        "public_security_product_positioning_allowed": False,
        "new_power_classes_allowed": False,
    }


def build_artifact(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    report = build_report(repo_root)
    output_path = output_dir if output_dir.is_absolute() else repo_root / output_dir
    output_path.mkdir(parents=True, exist_ok=True)
    json_path = output_path / JSON_NAME
    md_path = output_path / MD_NAME
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_report(report) + "\n", encoding="utf-8")
    return {
        **report,
        "artifact_output_dir": _repo_rel_path(repo_root, output_path).as_posix(),
        "artifact_json": _repo_rel_path(repo_root, json_path).as_posix(),
        "artifact_markdown": _repo_rel_path(repo_root, md_path).as_posix(),
        "artifact_written": True,
    }


def build_check_report(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    output_path = output_dir if output_dir.is_absolute() else repo_root / output_dir
    report = build_report(repo_root)
    json_path = output_path / JSON_NAME
    md_path = output_path / MD_NAME
    failures = list(report["failures"])

    if not json_path.exists():
        failures.append(
            "send-now JSON artifact is missing: "
            f"{_repo_rel_path(repo_root, json_path)}"
        )
    if not md_path.exists():
        failures.append(
            "send-now Markdown artifact is missing: "
            f"{_repo_rel_path(repo_root, md_path)}"
        )
    if json_path.exists():
        try:
            artifact = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            artifact = {}
            failures.append("send-now JSON artifact is not valid JSON")
        if artifact.get("commit") != report["commit"]:
            failures.append("send-now JSON artifact commit does not match current HEAD")
        if artifact.get("recommended_gaps") != report["recommended_gaps"]:
            failures.append("send-now JSON artifact recommended gaps drifted")
        for key in [
            "records_external_review",
            "normalizes_responses",
            "writes_response_files",
            "closes_erg_003",
            "closes_erg_002",
            "closes_erg_004",
            "runtime_changes_allowed",
            "mission_control_runtime_allowed",
            "live_vm_inspection_allowed",
            "sandbox_orchestration_allowed",
            "new_power_classes_allowed",
        ]:
            if artifact.get(key) is not False:
                failures.append(f"send-now JSON artifact boundary flag drifted: {key}")
    if md_path.exists():
        markdown = md_path.read_text(encoding="utf-8")
        for needle in [
            "Ithildin enterprise send now",
            *report["recommended_gaps"],
            "next_after_send:",
            "runtime_changes_allowed: false",
            "new_power_classes_allowed: false",
        ]:
            if needle not in markdown:
                failures.append(f"send-now Markdown artifact is missing {needle}")

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    required = {
        "Make artifact target": ("enterprise-send-now-artifact:", makefile),
        "Make artifact check target": ("enterprise-send-now-artifact-check:", makefile),
        "README command": ("make enterprise-send-now-artifact", readme),
    }
    for label, (needle, haystack) in required.items():
        if needle not in haystack:
            failures.append(f"{label} is missing {needle}")

    return {
        **report,
        "valid": not failures,
        "failures": failures,
        "artifact_output_dir": _repo_rel_path(repo_root, output_path).as_posix(),
        "artifact_json": _repo_rel_path(repo_root, json_path).as_posix(),
        "artifact_markdown": _repo_rel_path(repo_root, md_path).as_posix(),
        "artifact_json_exists": json_path.exists(),
        "artifact_markdown_exists": md_path.exists(),
        "artifact_written": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise send now",
        f"valid: {str(report['valid']).lower()}",
        f"commit: {report['commit']}",
        f"dirty: {str(report['dirty']).lower()}",
        f"tool_count: {report['tool_count']}",
        "recommended_gaps: " + ", ".join(report["recommended_gaps"]),
        f"upload_staging_path: {report['upload_staging_path']}",
        f"response_inbox_path: {report['response_inbox_path']}",
        f"send_now_artifact_path: {report['send_now_artifact_path']}",
        f"lane_count: {report['lane_count']}",
        f"batch_count: {report['batch_count']}",
        "lanes:",
    ]
    for lane in report["lanes"]:
        lines.extend(
            [
                f"- {lane['gap']}: {lane['name']}",
                f"  prompt: {lane['prompt']}",
                f"  finding_namespace: {lane['finding_namespace']}",
                f"  raw_response_path: {lane['raw_response_path']}",
                "  batches:",
            ]
        )
        for batch in lane["batches"]:
            lines.append(
                f"  - {batch['batch_id']}: {batch['path']} "
                f"({batch['attachment_count']} attachment(s))"
            )
        lines.extend(
            [
                f"  dry_run_after_response: {lane['dry_run']}",
                f"  closure_gate_after_response: {lane['closure_gate']}",
            ]
        )
    lines.append("next_after_send:")
    lines.extend(f"- {step}" for step in report["next_after_send"])
    lines.append("boundaries:")
    for key in [
        "records_external_review",
        "normalizes_responses",
        "writes_response_files",
        "closes_erg_003",
        "closes_erg_002",
        "closes_erg_004",
        "runtime_changes_allowed",
        "mission_control_runtime_allowed",
        "live_vm_inspection_allowed",
        "sandbox_orchestration_allowed",
        "new_power_classes_allowed",
    ]:
        lines.append(f"- {key}: {str(report[key]).lower()}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    if "artifact_json" in report:
        lines.extend(
            [
                "artifacts:",
                f"- json: {report['artifact_json']}",
                f"- markdown: {report['artifact_markdown']}",
            ]
        )
    return "\n".join(lines)


def _build_erg004_report(
    repo_root: Path,
    freshness: dict[str, Any],
    next_action: dict[str, Any],
) -> dict[str, Any]:
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    inbox = _read_json(repo_root / ERG004_RESPONSE_INBOX_JSON)
    source_dir = repo_root / ERG004_SOURCE_REVIEW_DIR
    hashes_path = source_dir / ERG004_SOURCE_REVIEW_HASHES
    hashes = _read_json(hashes_path)
    lanes = [_erg004_lane_report(repo_root, inbox, hashes)]
    failures = _erg004_failures(freshness, inbox, hashes, commit, lanes)
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "commit": commit,
        "dirty": bool(_git(repo_root, ["status", "--short"])),
        "tool_count": inbox.get("tool_count", 24),
        "selected_capability": inbox.get("selected_capability", "not selected"),
        "current_send_set": ["ERG-004"],
        "recommended_gaps": ["ERG-004"],
        "upload_staging_path": ERG004_SOURCE_REVIEW_DIR.as_posix(),
        "response_inbox_path": ERG004_RESPONSE_INBOX_JSON.parent.as_posix(),
        "send_now_artifact_path": DEFAULT_OUTPUT_DIR.as_posix(),
        "lane_count": len(lanes),
        "batch_count": sum(len(lane["batches"]) for lane in lanes),
        "lanes": lanes,
        "next_after_send": [
            "paste reviewer response into "
            "var/review-runs/sandbox-vm-live-poc-runtime-descriptor-only-response-inbox/"
            "RAW_RESPONSE_ERG-004-DESCRIPTOR-ONLY.md",
            "make sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run",
            "make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check",
        ],
        "records_external_review": False,
        "normalizes_responses": False,
        "writes_response_files": False,
        "closes_erg_003": False,
        "closes_erg_002": False,
        "closes_erg_004": False,
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "live_vm_inspection_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "compliance_automation_allowed": False,
        "public_security_product_positioning_allowed": False,
        "new_power_classes_allowed": False,
        "enterprise_next_action": next_action.get("next_action"),
    }


def _erg004_lane_report(
    repo_root: Path,
    inbox: dict[str, Any],
    hashes: dict[str, Any],
) -> dict[str, Any]:
    attachments = [
        artifact
        for artifact in hashes.get("artifacts", [])
        if isinstance(artifact, dict) and isinstance(artifact.get("path"), str)
    ]
    return {
        "gap": "ERG-004",
        "name": "Sandbox/VM live POC descriptor-only runtime source review",
        "prompt": (
            ERG004_SOURCE_REVIEW_DIR
            / "01_SANDBOX_VM_LIVE_POC_DESCRIPTOR_ONLY_SOURCE_REVIEW_PROMPT.md"
        ).as_posix(),
        "finding_namespace": "EXT-LIVE-DESC-###",
        "raw_response_path": inbox.get("raw_response_path"),
        "dry_run": inbox.get("dry_run"),
        "closure_gate": inbox.get("response_application_preflight"),
        "batches": [
            {
                "batch_id": "source-review-packet",
                "path": ERG004_SOURCE_REVIEW_DIR.as_posix(),
                "attachment_count": len(attachments) + 1,
            }
        ],
        "reviewed_packet_path": inbox.get(
            "reviewed_packet_path", ERG004_SOURCE_REVIEW_DIR.as_posix()
        ),
        "reviewed_packet_hash": inbox.get("reviewed_packet_hash"),
    }


def _erg004_failures(
    freshness: dict[str, Any],
    inbox: dict[str, Any],
    hashes: dict[str, Any],
    commit: str,
    lanes: list[dict[str, Any]],
) -> list[str]:
    failures: list[str] = []
    if freshness.get("valid") is not True:
        failures.append("handoff artifacts are stale; run make review-candidate")
    if inbox.get("commit") != commit:
        failures.append("ERG-004 descriptor-only response inbox commit does not match current HEAD")
    if inbox.get("gap") != "ERG-004":
        failures.append("ERG-004 descriptor-only response inbox gap drifted")
    if inbox.get("finding_namespace") != "EXT-LIVE-DESC-###":
        failures.append("ERG-004 descriptor-only response inbox namespace drifted")
    if inbox.get("runtime_changes_allowed") is not False:
        failures.append("ERG-004 descriptor-only response inbox allows runtime changes")
    if inbox.get("closes_erg_004") is not False:
        failures.append("ERG-004 descriptor-only response inbox closes ERG-004")
    hashed_paths = {
        artifact.get("path")
        for artifact in hashes.get("artifacts", [])
        if isinstance(artifact, dict)
    }
    required = {
        "00_SANDBOX_VM_LIVE_POC_DESCRIPTOR_ONLY_SOURCE_REVIEW_INDEX.md",
        "01_SANDBOX_VM_LIVE_POC_DESCRIPTOR_ONLY_SOURCE_REVIEW_PROMPT.md",
        "02_ERG004_DESCRIPTOR_ONLY_RUNTIME_SOURCE.md",
        "03_ERG004_DESCRIPTOR_ONLY_TESTS_AND_GATES.md",
        "04_ERG004_DESCRIPTOR_ONLY_CONTRACT_AND_BOUNDARY.md",
        "05_ERG004_DESCRIPTOR_ONLY_COMMAND_EVIDENCE.md",
    }
    if required - hashed_paths:
        failures.append("ERG-004 descriptor-only source review hash manifest is incomplete")
    if len(lanes) != 1:
        failures.append("expected exactly one ERG-004 send lane")
    for lane in lanes:
        if lane.get("gap") != "ERG-004":
            failures.append("send-now lane is not ERG-004")
        if not lane.get("raw_response_path"):
            failures.append("ERG-004 is missing a raw response path")
        if not lane.get("dry_run") or not lane.get("closure_gate"):
            failures.append("ERG-004 is missing response commands")
        if not lane.get("batches"):
            failures.append("ERG-004 has no source-review packet batch")
    return failures


def _lane_reports(upload: dict[str, Any], inbox: dict[str, Any]) -> list[dict[str, Any]]:
    inbox_lanes = {
        lane.get("gap"): lane
        for lane in inbox.get("lanes", [])
        if isinstance(lane, dict) and isinstance(lane.get("gap"), str)
    }
    lanes: list[dict[str, Any]] = []
    for lane in upload.get("lanes", []):
        if not isinstance(lane, dict):
            continue
        gap = lane.get("gap")
        inbox_lane = inbox_lanes.get(gap, {})
        raw_response_file = inbox_lane.get("raw_response_file")
        raw_response_path = (
            f"{DUAL_RESPONSE_INBOX_JSON.parent.as_posix()}/{raw_response_file}"
            if isinstance(raw_response_file, str)
            else lane.get("raw_response_path")
        )
        lanes.append(
            {
                "gap": gap,
                "name": lane.get("name"),
                "prompt": lane.get("prompt"),
                "finding_namespace": lane.get("finding_namespace"),
                "raw_response_path": raw_response_path,
                "dry_run": inbox_lane.get("dry_run"),
                "closure_gate": inbox_lane.get("closure_gate"),
                "batches": [
                    {
                        "batch_id": batch.get("batch_id"),
                        "path": batch.get("path"),
                        "attachment_count": batch.get("attachment_count"),
                    }
                    for batch in lane.get("batches", [])
                    if isinstance(batch, dict)
                ],
            }
        )
    return lanes


def _failures(
    freshness: dict[str, Any],
    upload: dict[str, Any],
    inbox: dict[str, Any],
    commit: str,
    lanes: list[dict[str, Any]],
) -> list[str]:
    failures: list[str] = []
    if freshness.get("valid") is not True:
        failures.append("handoff artifacts are stale; run make review-candidate")
    if upload.get("commit") != commit:
        failures.append("upload staging commit does not match current HEAD")
    if upload.get("dirty") is not False:
        failures.append("upload staging was not generated from a clean tree")
    if inbox.get("commit") != commit:
        failures.append("response inbox commit does not match current HEAD")
    if upload.get("recommended_gaps") != ["ERG-003", "ERG-002"]:
        failures.append("recommended send set is not ERG-003, ERG-002")
    if len(lanes) != 2:
        failures.append("expected exactly two send lanes")
    for lane in lanes:
        if not lane["batches"]:
            failures.append(f"{lane['gap']} has no upload batches")
        if not lane.get("raw_response_path"):
            failures.append(f"{lane['gap']} is missing a raw response path")
        if not lane.get("dry_run") or not lane.get("closure_gate"):
            failures.append(f"{lane['gap']} is missing response commands")
    return failures


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _repo_rel_path(repo_root: Path, path: Path) -> Path:
    resolved = path.resolve()
    try:
        return resolved.relative_to(repo_root.resolve())
    except ValueError:
        return resolved


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


if __name__ == "__main__":
    raise SystemExit(main())
