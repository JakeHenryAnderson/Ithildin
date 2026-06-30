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

from scripts import artifact_freshness_check  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
UPLOAD_STAGING_JSON = Path(
    "var/review-packets/v3/enterprise-review-upload-staging/"
    "enterprise-review-upload-staging.json"
)
DUAL_RESPONSE_INBOX_JSON = Path(
    "var/review-runs/enterprise-dual-response-inbox/enterprise-dual-response-inbox.json"
)


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
    freshness = artifact_freshness_check.build_report(repo_root)
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
        "recommended_gaps": upload.get("recommended_gaps", []),
        "upload_staging_path": UPLOAD_STAGING_JSON.parent.as_posix(),
        "response_inbox_path": DUAL_RESPONSE_INBOX_JSON.parent.as_posix(),
        "lane_count": len(lanes),
        "batch_count": sum(len(lane["batches"]) for lane in lanes),
        "lanes": lanes,
        "next_after_send": [
            "copy the send receipt template before editing it",
            "fill the copied receipt after the human send step",
            "make enterprise-review-send-receipt-validate RECEIPT=path/to/copied-receipt.json",
            "make enterprise-response-waiting-room",
            "make enterprise-response-paste-preflight after reviewer responses are pasted",
        ],
        "records_external_review": False,
        "normalizes_responses": False,
        "writes_response_files": False,
        "closes_erg_003": False,
        "closes_erg_002": False,
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
    return "\n".join(lines)


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


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


if __name__ == "__main__":
    raise SystemExit(main())
