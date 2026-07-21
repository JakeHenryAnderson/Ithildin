"""Generate a display-only enterprise status export for operator dashboards."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_current_checkpoint,
    enterprise_operator_next_action,
    enterprise_progress_model,
    enterprise_response_status_board,
    enterprise_review_send_readiness,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-status-export.md"
DOC_TITLE = "Enterprise Status Export"
DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/enterprise-status-export")
MARKDOWN_NAME = "ENTERPRISE_STATUS_EXPORT.md"
JSON_NAME = "enterprise-status-export.json"
HASH_NAME = "enterprise-status-export-artifact-hashes.json"
ARCHIVED_ERG004_DESCRIPTOR_ONLY_COMMANDS = [
    "make sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run",
    "make sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-response-application-record-check",
]
PIS_003_DISPLAY_ACTION_COMMANDS = [
    "make production-identity-storage-pis-002-continuation-decision-check",
    "make production-identity-storage-pis-002-sandbox-descriptor-repository-"
    "internal-review-check",
    "make no-new-powers-guardrail",
    "make tool-surface-invariant-gate",
]

REQUIRED_DOC_PHRASES = [
    "Status: display-only enterprise status export contract.",
    "make enterprise-status-export",
    "make enterprise-status-export-check",
    "safe action commands",
    "send package",
    "send-session record",
    "does not approve Mission Control runtime behavior",
    "does not approve live VM/container inspection",
    "does not approve sandbox orchestration",
    "does not approve trusted-host promotion",
    "does not approve SIEM adapter behavior",
    "does not approve compliance automation",
    "does not approve public/security-product positioning",
    "does not approve new governed tool powers",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    report = build_report(ROOT)
    if args.write:
        output_dir = write_export(report, args.output_dir)
        print(f"Built enterprise status export at {output_dir}")
        return 0 if report["valid"] else 1
    if args.check:
        generated = _build_artifacts(report)
        failures = list(report["failures"])
        failures.extend(_validate_generated_artifacts(generated))
        failures.extend(_validate_persisted_export(args.output_dir, report))
        if failures:
            for failure in failures:
                print(f"enterprise status export failed: {failure}", file=sys.stderr)
            return 1
        print("Enterprise status export check passed.")
        return 0
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path) -> dict[str, Any]:
    current = enterprise_current_checkpoint.build_report(repo_root)
    next_action = enterprise_operator_next_action.build_report(repo_root)
    progress = enterprise_progress_model.build_report(repo_root)
    send = enterprise_review_send_readiness.build_report(repo_root)
    responses = enterprise_response_status_board.build_report(repo_root)
    git = _git_state(repo_root)

    failures: list[str] = []
    failures.extend(f"enterprise-current-checkpoint: {failure}" for failure in current["failures"])
    failures.extend(
        f"enterprise-operator-next-action: {failure}" for failure in next_action["failures"]
    )
    failures.extend(f"enterprise-progress-model: {failure}" for failure in progress["failures"])
    if next_action.get("next_action") != "prepare_pis_003_entry_decision_record":
        failures.extend(
            f"enterprise-review-send-readiness: {failure}"
            for failure in send["failures"]
        )
    failures.extend(
        f"enterprise-response-status-board: {failure}" for failure in responses["failures"]
    )

    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    if current.get("tool_count") != 24:
        failures.append("current checkpoint tool count is not 24")
    if progress.get("tool_count") != 24:
        failures.append("progress model tool count is not 24")
    if send.get("recommended_now") != ["ERG-003", "ERG-002"]:
        failures.append("send readiness recommended set is not ERG-003 then ERG-002")
    if responses.get("response_present_count") != 0:
        failures.append("enterprise responses are present; run response intake before exporting")
    if responses.get("closure_ready_count") != 0:
        failures.append("enterprise closures are ready; run lane-specific closure before exporting")

    boundary_flags = {
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
    for source_name, source in [
        ("current checkpoint", current),
        ("operator next action", next_action),
        ("progress model", progress),
        ("send readiness", send),
        ("response status", responses),
    ]:
        for key, expected in boundary_flags.items():
            if key in source and source[key] is not expected:
                failures.append(f"{source_name} boundary flag drifted: {key}")

    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in doc:
            failures.append(f"enterprise status export doc is missing phrase: {phrase}")
    if "enterprise-status-export:" not in makefile:
        failures.append("Make target is missing: enterprise-status-export")
    if "enterprise-status-export-check:" not in makefile:
        failures.append("Make target is missing: enterprise-status-export-check")
    if "enterprise-status-export-check" not in release_check_body:
        failures.append("enterprise-status-export-check is missing from release-check")
    if "$(MAKE) enterprise-status-export" not in review_candidate_body:
        failures.append("enterprise-status-export is missing from review-candidate")
    if "make enterprise-status-export" not in readme:
        failures.append("README is missing enterprise-status-export command")
    if DOC_REL not in readme:
        failures.append("README is missing enterprise status export doc")
    if DOC_REL not in docs_site:
        failures.append("enterprise status export is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise status export is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing enterprise status export")
    if "enterprise-status-export-check" not in release_guardrails:
        failures.append("release guardrails do not require enterprise status export check")

    active_send_set = set(current.get("recommended_send_set") or [])
    pis_planning_mode = (
        next_action.get("next_action") == "prepare_pis_003_entry_decision_record"
    )
    display_action_commands = (
        PIS_003_DISPLAY_ACTION_COMMANDS
        if pis_planning_mode
        else next_action.get("action_commands")
    )
    display_next_after_send_commands = (
        PIS_003_DISPLAY_ACTION_COMMANDS
        if pis_planning_mode
        else next_action.get("next_after_send_commands")
    )
    rows = [
        {
            "gap": row["gap"],
            "status": row["status"],
            "packet_path": row["packet_path"],
            "packet_handoff_ready": (
                True
                if pis_planning_mode and row["gap"] == "ERG-006/ERG-007"
                else row["packet_handoff_ready"]
            ),
            "recommended_to_send_now": _gap_selected(row["gap"], active_send_set),
            "closure_ready": row["closure_ready"],
            "normalized_response_present": row["normalized_response_present"],
            "implementation_allowed": row["implementation_allowed"],
            "runtime_changes_allowed": row["runtime_changes_allowed"],
            "note": row["note"],
        }
        for row in send["rows"]
    ]

    return {
        "schema_version": "1",
        "artifact_type": "ithildin.enterprise_status_export",
        "status": "display_only",
        "valid": not failures,
        "failures": failures,
        "summary_doc": DOC_REL,
        "git": git,
        "tool_count": 24,
        "selected_capability": current.get("selected_capability"),
        "recommended_send_set": current.get("recommended_send_set"),
        "recommended_next_enterprise_review": current.get("recommended_next_enterprise_review"),
        "next_action": next_action.get("next_action"),
        "action_commands": display_action_commands,
        "next_after_send_commands": display_next_after_send_commands,
        "archived_erg004_descriptor_only_commands": ARCHIVED_ERG004_DESCRIPTOR_ONLY_COMMANDS,
        "handoff_artifacts": next_action.get("handoff_artifacts"),
        "operator_next_action_doc": next_action.get("next_action_doc"),
        "response_present_count": responses.get("response_present_count"),
        "closure_ready_count": responses.get("closure_ready_count"),
        "enterprise_gap_count": progress.get("enterprise_gap_count"),
        "progress_bands": progress.get("progress_bands"),
        "lane_count": send.get("lane_count"),
        "packet_handoff_ready_count": sum(
            1 for row in rows if row["packet_handoff_ready"] is True
        ),
        "review_lanes": rows,
        "packet_paths": {
            "enterprise_status_export": DEFAULT_OUTPUT_DIR.as_posix(),
            "v1_rc_packet": "var/review-packets/v1.0/rc",
            "enterprise_dual_review_outbox": "var/review-packets/v3/enterprise-dual-review-outbox",
            "enterprise_review_send_quickstart": (
                "var/review-packets/v3/enterprise-review-send-quickstart"
            ),
            "enterprise_review_send_package": (
                "var/review-packets/v3/enterprise-review-send-package"
            ),
            "enterprise_review_send_session_record": (
                "var/review-runs/enterprise-review-send-session-record"
            ),
            "enterprise_response_status_board": "var/review-runs/enterprise-response-status-board",
        },
        **boundary_flags,
    }


def write_export(report: dict[str, Any], output_dir: Path) -> Path:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = _build_artifacts(report)
    for name, content in artifacts.items():
        (output_dir / name).write_text(content, encoding="utf-8")
    hashes = _artifact_hashes(output_dir)
    (output_dir / HASH_NAME).write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise status export",
        f"valid: {str(report['valid']).lower()}",
        f"status: {report['status']}",
        f"summary_doc: {report['summary_doc']}",
        f"commit: {report['git']['commit']}",
        f"dirty: {str(report['git']['dirty']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report['selected_capability']}",
        "recommended_send_set: " + ", ".join(report["recommended_send_set"]),
        f"recommended_next_enterprise_review: {report['recommended_next_enterprise_review']}",
        f"next_action: {report['next_action']}",
        "action_commands:",
        *[f"- {command}" for command in report.get("action_commands") or []],
        "next_after_send_commands:",
        *[f"- {command}" for command in report.get("next_after_send_commands") or []],
        "handoff_artifacts:",
        *[
            f"- {artifact['label']}: {artifact['path']}"
            for artifact in report.get("handoff_artifacts") or []
        ],
        f"response_present_count: {report['response_present_count']}",
        f"closure_ready_count: {report['closure_ready_count']}",
        f"enterprise_gap_count: {report['enterprise_gap_count']}",
        "progress_bands:",
    ]
    lines.extend(f"- {name}: {band}" for name, band in report["progress_bands"].items())
    lines.extend(
        [
            f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
            "mission_control_runtime_allowed: "
            f"{str(report['mission_control_runtime_allowed']).lower()}",
            f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
            "sandbox_orchestration_allowed: "
            f"{str(report['sandbox_orchestration_allowed']).lower()}",
            "trusted_host_promotion_allowed: "
            f"{str(report['trusted_host_promotion_allowed']).lower()}",
            f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
            "compliance_automation_allowed: "
            f"{str(report['compliance_automation_allowed']).lower()}",
            "public_security_product_positioning_allowed: "
            f"{str(report['public_security_product_positioning_allowed']).lower()}",
            f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        ]
    )
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def render_markdown(report: dict[str, Any]) -> str:
    lane_rows = "\n".join(
        "| {gap} | `{status}` | `{ready}` | `{recommended}` | `{closure}` | `{response}` |".format(
            gap=row["gap"],
            status=row["status"],
            ready=str(row["packet_handoff_ready"]).lower(),
            recommended=str(row["recommended_to_send_now"]).lower(),
            closure=str(row["closure_ready"]).lower(),
            response=str(row["normalized_response_present"]).lower(),
        )
        for row in report["review_lanes"]
    )
    progress_rows = "\n".join(
        f"| {name} | `{band}` |" for name, band in report["progress_bands"].items()
    )
    public_positioning = str(report["public_security_product_positioning_allowed"]).lower()
    action_command_lines = "\n".join(
        f"  - `{command}`" for command in report.get("action_commands") or []
    )
    next_after_send_command_lines = "\n".join(
        f"  - `{command}`" for command in report.get("next_after_send_commands") or []
    )
    handoff_artifact_lines = "\n".join(
        f"  - `{artifact['label']}`: `{artifact['path']}`"
        for artifact in report.get("handoff_artifacts") or []
    )
    packet_path_lines = "\n".join(
        f"- `{label}`: `{path}`" for label, path in report["packet_paths"].items()
    )
    return f"""# Enterprise Status Export

Status: generated display-only enterprise status export.

This ignored export is for operator dashboards and Mission Control display/import experiments. It
is not a policy source, not an approval source, not audit custody, not a source of truth over
runtime behavior, and not an enterprise lane closure record.

## Snapshot

- schema_version: `{report["schema_version"]}`
- artifact_type: `{report["artifact_type"]}`
- status: `{report["status"]}`
- commit: `{report["git"]["commit"]}`
- dirty: `{str(report["git"]["dirty"]).lower()}`
- tool_count: `{report["tool_count"]}`
- selected_capability: `{report["selected_capability"]}`
- recommended_send_set: `{", ".join(report["recommended_send_set"])}`
- recommended_next_enterprise_review: `{report["recommended_next_enterprise_review"]}`
- next_action: `{report["next_action"]}`
- action_commands:
{action_command_lines}
- next_after_send_commands:
{next_after_send_command_lines}
- handoff_artifacts:
{handoff_artifact_lines}
- response_present_count: `{report["response_present_count"]}`
- closure_ready_count: `{report["closure_ready_count"]}`
- enterprise_gap_count: `{report["enterprise_gap_count"]}`

## Progress Bands

| Area | Band |
| --- | --- |
{progress_rows}

## Review Lanes

| Gap | Status | packet_handoff_ready | recommended_now | closure_ready | response_present |
| --- | --- | --- | --- | --- | --- |
{lane_rows}

## Packet Paths

{packet_path_lines}

## Blocked Authority

- runtime_changes_allowed: `{str(report["runtime_changes_allowed"]).lower()}`
- mission_control_runtime_allowed: `{str(report["mission_control_runtime_allowed"]).lower()}`
- live_vm_inspection_allowed: `{str(report["live_vm_inspection_allowed"]).lower()}`
- sandbox_orchestration_allowed: `{str(report["sandbox_orchestration_allowed"]).lower()}`
- trusted_host_promotion_allowed: `{str(report["trusted_host_promotion_allowed"]).lower()}`
- siem_adapter_allowed: `{str(report["siem_adapter_allowed"]).lower()}`
- compliance_automation_allowed: `{str(report["compliance_automation_allowed"]).lower()}`
- public_security_product_positioning_allowed: `{public_positioning}`
- new_power_classes_allowed: `{str(report["new_power_classes_allowed"]).lower()}`

## What This Export Does Not Approve

This export does not approve Mission Control runtime behavior. It does not approve live
VM/container inspection. It does not approve sandbox orchestration. It does not approve trusted-host
promotion. It does not approve SIEM adapter behavior. It does not approve compliance automation. It
does not approve public/security-product positioning. It does not approve new governed tool powers.
"""


def _build_artifacts(report: dict[str, Any]) -> dict[str, str]:
    return {
        MARKDOWN_NAME: render_markdown(report),
        JSON_NAME: json.dumps(report, indent=2, sort_keys=True) + "\n",
    }


def _gap_selected(gap: str, active_send_set: set[str]) -> bool:
    if gap in active_send_set:
        return True
    combined_gaps = set(gap.split("/"))
    return len(combined_gaps) > 1 and combined_gaps.issubset(active_send_set)


def _validate_generated_artifacts(artifacts: dict[str, str]) -> list[str]:
    failures: list[str] = []
    required = {MARKDOWN_NAME, JSON_NAME}
    if set(artifacts) != required:
        failures.append("generated artifact set drifted")
    markdown = artifacts.get(MARKDOWN_NAME, "")
    json_text = artifacts.get(JSON_NAME, "")
    for phrase in [
        "display-only enterprise status export",
        "recommended_send_set: `ERG-006, ERG-007`",
        "next_action: `prepare_pis_003_entry_decision_record`",
        "`make production-identity-storage-pis-002-continuation-decision-check`",
        "`make production-identity-storage-pis-002-sandbox-descriptor-repository-"
        "internal-review-check`",
        "`make no-new-powers-guardrail`",
        "`make tool-surface-invariant-gate`",
        "handoff_artifacts:",
        "production-identity-storage-pis-002-continuation-decision-record.md",
        "production-identity-storage-pis-002-continuation-decision.json",
        "production-identity-storage-pis-002-sandbox-descriptor-repository-internal-source-review.md",
        "runtime_changes_allowed: `false`",
        "does not approve Mission Control runtime behavior",
        "does not approve new governed tool powers",
    ]:
        if phrase not in markdown:
            failures.append(f"generated markdown is missing phrase: {phrase}")
    for phrase in [
        '"artifact_type": "ithildin.enterprise_status_export"',
        '"status": "display_only"',
        '"tool_count": 24',
        '"next_action": "prepare_pis_003_entry_decision_record"',
        '"handoff_artifacts": [',
        "production-identity-storage-pis-002-continuation-decision-record.md",
        "production-identity-storage-pis-002-continuation-decision.json",
        "production-identity-storage-pis-002-sandbox-descriptor-repository-internal-source-review.md",
        '"make production-identity-storage-pis-002-continuation-decision-check"',
        '"make production-identity-storage-pis-002-sandbox-descriptor-repository-'
        'internal-review-check"',
        '"make no-new-powers-guardrail"',
        '"make tool-surface-invariant-gate"',
        '"runtime_changes_allowed": false',
        '"new_power_classes_allowed": false',
    ]:
        if phrase not in json_text:
            failures.append(f"generated JSON is missing phrase: {phrase}")
    return failures


def _validate_persisted_export(output_dir: Path, report: dict[str, Any]) -> list[str]:
    if not output_dir.exists():
        return []
    failures: list[str] = []
    markdown_path = output_dir / MARKDOWN_NAME
    json_path = output_dir / JSON_NAME
    hash_path = output_dir / HASH_NAME
    for path in [markdown_path, json_path, hash_path]:
        if not path.exists():
            failures.append(f"persisted enterprise status export missing: {path.name}")
    if failures:
        return failures

    markdown = markdown_path.read_text(encoding="utf-8")
    try:
        persisted_json = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"persisted enterprise status JSON is invalid: {exc}")
        persisted_json = {}
    try:
        persisted_hashes = json.loads(hash_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"persisted enterprise status hash manifest is invalid: {exc}")
        persisted_hashes = {}

    current_commit = report["git"]["commit"]
    current_action = report["next_action"]
    if f"commit: `{current_commit}`" not in markdown:
        failures.append("persisted enterprise status markdown commit is stale")
    if f"next_action: `{current_action}`" not in markdown:
        failures.append("persisted enterprise status markdown next_action is stale")
    if persisted_json.get("git", {}).get("commit") != current_commit:
        failures.append("persisted enterprise status JSON commit is stale")
    if persisted_json.get("next_action") != current_action:
        failures.append("persisted enterprise status JSON next_action is stale")
    if not _artifact_hashes_match_files(output_dir, persisted_hashes):
        failures.append("persisted enterprise status artifact hashes do not match files")
    return failures


def _artifact_hashes(output_dir: Path) -> dict[str, Any]:
    artifacts = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name == HASH_NAME:
            continue
        data = path.read_bytes()
        artifacts.append(
            {
                "path": path.relative_to(output_dir).as_posix(),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return {
        "schema_version": "1",
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "hash_manifest_self_hashed": False,
    }


def _artifact_hashes_match_files(output_dir: Path, manifest: dict[str, Any]) -> bool:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return False
    expected = {
        str(item.get("path")): item
        for item in artifacts
        if isinstance(item, dict) and item.get("path")
    }
    actual = _artifact_hashes(output_dir).get("artifacts", [])
    actual_by_path = {str(item["path"]): item for item in actual}
    if set(expected) != set(actual_by_path):
        return False
    for path, expected_item in expected.items():
        actual_item = actual_by_path[path]
        if expected_item.get("sha256") != actual_item.get("sha256"):
            return False
        if expected_item.get("bytes") != actual_item.get("bytes"):
            return False
    return manifest.get("hash_manifest_self_hashed") is False


def _git_state(repo_root: Path) -> dict[str, Any]:
    commit = _git(repo_root, "rev-parse", "HEAD")
    status = _git(repo_root, "status", "--short")
    return {
        "commit": commit,
        "dirty": bool(status.strip()),
    }


def _git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())
