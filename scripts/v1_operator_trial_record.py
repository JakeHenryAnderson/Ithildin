"""Generate and validate a secret-free v1.0 operator trial record."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    demo_evidence_readiness,
    enterprise_operator_next_action,
    enterprise_response_waiting_room,
    live_demo_environment_diagnostics,
    packet_redaction_scan,
    review_docs,
    v1_operator_trial_checklist_check,
    v1_progress_assessment,
    v1_rc_readiness_check,
    v1_rc_status_check,
    validation_decision,
    workbench_readiness,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs/codex/v1.0-operator-trial-record.md"
DEFAULT_OUTPUT_DIR = ROOT / "var/review-packets/v1.0/operator-trial"
REQUIRED_ARTIFACTS = [
    Path("var/review-packets/v1.0/rc"),
    Path("var/review-packets/v3/operator-workbench"),
    Path("var/review-packets/v3/demo-evidence"),
    Path("var/review-packets/v3/live-demo"),
    Path("var/review-packets/v3/review-candidate-release-check.txt"),
]
RECOMMENDED_COMMANDS = [
    "make v1-operator-trial-record-check",
    "make release-check",
    "make review-candidate",
    "git status --short",
]
REQUIRED_DOC_PHRASES = [
    "Status: generated local-preview operator trial evidence record for the v1.0 RC path.",
    "make v1-operator-trial-record",
    "make v1-operator-trial-record-check",
    "var/review-packets/v1.0/operator-trial/",
    "What The Record Does Not Do",
    "packet redaction scan reports `findings: 0`",
    "validation decision summary",
    "enterprise operator next-action result",
    "enterprise response waiting-room result",
    "live demo environment diagnostics result",
    "current enterprise send set, waiting-room counts, and handoff artifact pointers",
    "local-preview handoff evidence only",
]
ALLOWED_ENTERPRISE_NEXT_ACTIONS = {
    "send_erg_003_and_erg_002",
    "prepare_erg004_runtime_implementation_gate",
    "prepare_erg004_descriptor_only_runtime_planning",
    "prepare_erg005_trusted_host_promotion_review",
    "execute_pis_001_threat_model_dependency_decision",
    "prepare_pis_002_entry_decision_record",
    "prepare_pis_003_entry_decision_record",
}
BLOCKED_PHRASES = [
    "production deployment readiness",
    "kernel sandbox claim",
    "compliance automation",
    "SIEM-grade custody",
    "external notarization",
    "public/security-product positioning",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.check:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = build_record(ROOT, Path(temp_dir) / "operator-trial")
    else:
        report = build_record(ROOT, args.output_dir)
    report["failures"].extend(_wiring_failures(ROOT))
    report["valid"] = _record_valid(report)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_record(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    status = v1_rc_status_check.build_report(repo_root)
    progress = v1_progress_assessment.build_report(repo_root)
    checklist = v1_operator_trial_checklist_check.build_report(repo_root)
    readiness = v1_rc_readiness_check.build_report(repo_root)
    workbench = workbench_readiness.build_report(repo_root)
    demo_evidence = demo_evidence_readiness.build_report(repo_root)
    enterprise_next_action = enterprise_operator_next_action.build_report(repo_root)
    enterprise_waiting_room = enterprise_response_waiting_room.build_report(repo_root)
    live_environment = live_demo_environment_diagnostics.build_report(repo_root)
    validation = validation_decision.build_report([])
    artifact_reports = [_artifact_report(repo_root, artifact) for artifact in REQUIRED_ARTIFACTS]
    packet_scan = _packet_scan(repo_root)
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    failures = [
        *_prefixed_failures("v1-rc-status", status),
        *_prefixed_failures("v1-progress-assessment", progress),
        *_prefixed_failures("operator-trial-checklist", checklist),
        *_prefixed_failures("v1-rc-readiness", readiness),
        *_prefixed_failures("workbench-readiness", workbench),
        *_prefixed_failures("demo-evidence-readiness", demo_evidence),
        *_prefixed_failures("enterprise-operator-next-action", enterprise_next_action),
        *_prefixed_failures("enterprise-response-waiting-room", enterprise_waiting_room),
        *_prefixed_failures("live-demo-environment-diagnostics", live_environment),
        *_prefixed_failures("validation-decision", validation),
    ]
    if packet_scan["findings_count"] != 0:
        failures.append("packet redaction scan has findings")
    if enterprise_next_action.get("next_action") not in ALLOWED_ENTERPRISE_NEXT_ACTIONS:
        failures.append("enterprise next action is not an allowed review flow")
    if enterprise_waiting_room.get("candidate_response_count") != 0:
        failures.append("enterprise waiting room has candidate responses")
    if enterprise_waiting_room.get("recommended_gaps") != ["ERG-004"]:
        failures.append("enterprise waiting room is not on the active ERG-004 lane")
    if enterprise_waiting_room.get("placeholder_count") != 1:
        failures.append("enterprise waiting room does not have one active ERG-004 placeholder")

    report: dict[str, Any] = {
        "schema_version": "1",
        "valid": False,
        "generated_at": datetime.now(UTC).isoformat(),
        "repo_root": str(repo_root),
        "commit": commit,
        "dirty": dirty,
        "tool_count": status.get("tool_count"),
        "latest_implemented_tool": status.get("latest_implemented_tool"),
        "selected_capability": status.get("selected_capability"),
        "checks": {
            "v1_rc_status": _summary(status),
            "v1_progress_assessment": _summary(progress),
            "operator_trial_checklist": _summary(checklist),
            "v1_rc_readiness": _summary(readiness),
            "workbench_readiness": _summary(workbench),
            "demo_evidence_readiness": _summary(demo_evidence),
            "enterprise_next_action": _summary(enterprise_next_action),
            "enterprise_waiting_room": _summary(enterprise_waiting_room),
            "live_demo_environment": _summary(live_environment),
            "validation_decision": _summary(validation),
            "packet_redaction_scan": packet_scan,
        },
        "live_demo_environment": {
            "compose_demo_ready": live_environment.get("compose_demo_ready"),
            "docker_cli_available": live_environment.get("docker", {}).get("cli_available"),
            "docker_compose_status": live_environment.get("docker", {})
            .get("compose_version", {})
            .get("status"),
            "docker_daemon_status": live_environment.get("docker", {})
            .get("daemon_info", {})
            .get("status"),
            "rosetta_check_status": live_environment.get("rosetta", {}).get("status"),
            "safe_next_actions": live_environment.get("safe_next_actions", []),
        },
        "enterprise_review_state": {
            "next_action": enterprise_next_action.get("next_action"),
            "recommended_send_set": enterprise_next_action.get("recommended_send_set"),
            "recommended_next_enterprise_review": enterprise_next_action.get(
                "recommended_next_enterprise_review"
            ),
            "handoff_artifacts": enterprise_next_action.get("handoff_artifacts", []),
            "candidate_response_count": enterprise_waiting_room.get("candidate_response_count"),
            "placeholder_count": enterprise_waiting_room.get("placeholder_count"),
            "missing_count": enterprise_waiting_room.get("missing_count"),
            "invalid_count": enterprise_waiting_room.get("invalid_count"),
            "waiting_room_next_action": enterprise_waiting_room.get("next_action"),
        },
        "validation_decision": {
            "recommended_mode": validation["recommended_mode"],
            "next_development_commands": validation["next_development_commands"],
            "deferred_handoff_commands": validation["deferred_handoff_commands"],
            "release_or_handoff_required": validation["release_or_handoff_required"],
        },
        "artifacts": artifact_reports,
        "recommended_next_commands": RECOMMENDED_COMMANDS,
        "runtime_changes_allowed": False,
        "new_power_classes_allowed": False,
        "sandbox_orchestration_allowed": False,
        "siem_adapter_behavior_allowed": False,
        "production_identity_allowed": False,
        "public_security_product_positioning_allowed": False,
        "failures": failures,
    }
    report["valid"] = _record_valid(report)

    (output_dir / "V1_OPERATOR_TRIAL_RECORD.md").write_text(
        render_record_markdown(report), encoding="utf-8"
    )
    (output_dir / "v1-operator-trial-record.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v1.0 operator trial record",
        f"valid: {str(report['valid']).lower()}",
        f"commit: {report['commit']}",
        f"dirty: {str(report['dirty']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"latest_implemented_tool: {report['latest_implemented_tool']}",
        f"selected_capability: {report['selected_capability']}",
        "runtime_changes_allowed: false",
        "new_power_classes_allowed: false",
        "sandbox_orchestration_allowed: false",
        "siem_adapter_behavior_allowed: false",
        "public_security_product_positioning_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def render_record_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Ithildin v1.0 Operator Trial Record",
        "",
        "Status: generated local-preview operator trial evidence record.",
        "",
        "This generated artifact is secret-free. It does not start services, call governed tools,",
        "approve actions, mutate workspaces, manage sandbox lifecycle, invoke local models, create",
        "SIEM custody, or approve public/security-product positioning.",
        "",
        "## Current State",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- commit: `{report['commit']}`",
        f"- dirty: `{str(report['dirty']).lower()}`",
        f"- tool_count: `{report['tool_count']}`",
        f"- latest_implemented_tool: `{report['latest_implemented_tool']}`",
        f"- selected_capability: `{report['selected_capability']}`",
        f"- valid: `{str(report['valid']).lower()}`",
        "",
        "## Checks",
        "",
        "| Check | Valid | Failure count |",
        "| --- | --- | ---: |",
    ]
    for name, check in report["checks"].items():
        lines.append(f"| `{name}` | `{str(check['valid']).lower()}` | `{check['failure_count']}` |")
    lines.extend(["", "## Artifacts", "", "| Artifact | Exists | Bytes | SHA-256 |"])
    lines.append("| --- | --- | ---: | --- |")
    for artifact in report["artifacts"]:
        lines.append("| `{path}` | `{exists}` | `{bytes}` | `{sha256}` |".format(**artifact))
    validation = report["validation_decision"]
    lines.extend(
        [
            "",
            "## Validation Decision",
            "",
            "This section records the validation decision summary for the current handoff state.",
            "",
            f"- recommended_mode: `{validation['recommended_mode']}`",
            "- release_or_handoff_required: "
            f"`{str(validation['release_or_handoff_required']).lower()}`",
            "- next_development_commands:",
        ]
    )
    lines.extend(f"  - `{command}`" for command in validation["next_development_commands"])
    if validation["deferred_handoff_commands"]:
        lines.append("- deferred_handoff_commands:")
        lines.extend(f"  - `{command}`" for command in validation["deferred_handoff_commands"])
    enterprise = report["enterprise_review_state"]
    lines.extend(
        [
            "",
            "## Enterprise Review State",
            "",
            f"- next_action: `{enterprise['next_action']}`",
            "- recommended_send_set: "
            + ", ".join(f"`{gap}`" for gap in enterprise["recommended_send_set"] or []),
            "- recommended_next_enterprise_review: "
            f"`{enterprise['recommended_next_enterprise_review']}`",
            f"- candidate_response_count: `{enterprise['candidate_response_count']}`",
            f"- placeholder_count: `{enterprise['placeholder_count']}`",
            f"- missing_count: `{enterprise['missing_count']}`",
            f"- invalid_count: `{enterprise['invalid_count']}`",
            f"- waiting_room_next_action: `{enterprise['waiting_room_next_action']}`",
            "",
            "| Handoff artifact | Path |",
            "| --- | --- |",
        ]
    )
    for artifact in enterprise["handoff_artifacts"]:
        lines.append(f"| `{artifact['label']}` | `{artifact['path']}` |")
    live_environment = report["live_demo_environment"]
    lines.extend(
        [
            "",
            "## Live Demo Environment",
            "",
            "This section records the live demo environment diagnostics result for the optional",
            "local API/UI Compose path. It is operator-environment evidence only and is not a",
            "release requirement.",
            "",
            f"- compose_demo_ready: `{str(live_environment['compose_demo_ready']).lower()}`",
            f"- docker_cli_available: `{str(live_environment['docker_cli_available']).lower()}`",
            f"- docker_compose_status: `{live_environment['docker_compose_status']}`",
            f"- docker_daemon_status: `{live_environment['docker_daemon_status']}`",
            f"- rosetta_check_status: `{live_environment['rosetta_check_status']}`",
            "- safe_next_actions:",
        ]
    )
    lines.extend(f"  - `{action}`" for action in live_environment["safe_next_actions"])
    lines.extend(["", "## Recommended Next Commands", ""])
    lines.extend(f"{idx}. `{command}`" for idx, command in enumerate(RECOMMENDED_COMMANDS, 1))
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This record is local-preview handoff evidence only. It does not prove production",
            "deployment readiness, kernel sandbox isolation, host compromise resistance,",
            "SIEM-grade custody, external notarization, compliance automation, Mission Control",
            "execution authority, trusted-host promotion, or activity outside Ithildin-mediated",
            "actions.",
            "",
            "## What The Record Does Not Do",
            "",
            "This record does not start services, call governed tools, approve actions, mutate",
            "workspaces, manage sandbox lifecycle, invoke local models, create SIEM custody,",
            "normalize enterprise review responses, close lanes, or approve",
            "public/security-product positioning.",
            "",
        ]
    )
    if report["failures"]:
        lines.extend(["## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
        lines.append("")
    return "\n".join(lines)


def _record_valid(report: dict[str, Any]) -> bool:
    return (
        not report["failures"]
        and report.get("tool_count") == 24
        and report.get("latest_implemented_tool") == "sandbox.artifact.write_text"
        and report.get("selected_capability") == "not selected"
        and report["checks"]["packet_redaction_scan"]["findings_count"] == 0
    )


def _summary(report: dict[str, Any]) -> dict[str, Any]:
    failures = report.get("failures", [])
    return {
        "valid": bool(report.get("valid")),
        "failure_count": len(failures),
    }


def _prefixed_failures(label: str, report: dict[str, Any]) -> list[str]:
    return [f"{label}: {failure}" for failure in report.get("failures", [])]


def _artifact_report(repo_root: Path, relative_path: Path) -> dict[str, Any]:
    path = repo_root / relative_path
    if not path.exists():
        return {
            "path": relative_path.as_posix(),
            "exists": "false",
            "bytes": 0,
            "sha256": "missing",
        }
    if path.is_file():
        content = path.read_bytes()
    else:
        digest_input = []
        for child in sorted(child for child in path.rglob("*") if child.is_file()):
            rel = child.relative_to(path).as_posix()
            digest_input.append(rel.encode("utf-8") + b"\0" + child.read_bytes())
        content = b"".join(digest_input)
    return {
        "path": relative_path.as_posix(),
        "exists": "true",
        "bytes": len(content),
        "sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
    }


def _packet_scan(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "var/review-packets/v1.0/rc"
    if not path.exists():
        return {
            "valid": True,
            "failure_count": 0,
            "findings_count": 0,
            "scanned_files": 0,
            "roots": [],
            "note": "v1.0 RC packet not generated yet",
        }
    result = packet_redaction_scan.scan_packet_paths([path])
    return {
        "valid": not result.findings,
        "failure_count": len(result.findings),
        "findings_count": len(result.findings),
        "scanned_files": result.scanned_files,
        "roots": result.roots,
    }


def _wiring_failures(repo_root: Path) -> list[str]:
    failures: list[str] = []
    doc_rel = DOC_PATH.relative_to(ROOT).as_posix()
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    packet_script = (repo_root / "scripts/v1_rc_packet.py").read_text(encoding="utf-8")
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]
    text = DOC_PATH.read_text(encoding="utf-8") if DOC_PATH.exists() else ""

    if not DOC_PATH.exists():
        failures.append("v1.0 operator trial record doc is missing")
    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in text:
            failures.append(f"v1.0 operator trial record doc missing phrase: {phrase}")
    for phrase in BLOCKED_PHRASES:
        if phrase not in text:
            failures.append(f"v1.0 operator trial record doc missing blocked phrase: {phrase}")
    if "v1-operator-trial-record:" not in makefile:
        failures.append("Make target is missing: v1-operator-trial-record")
    if "v1-operator-trial-record-check:" not in makefile:
        failures.append("Make target is missing: v1-operator-trial-record-check")
    if "v1-operator-trial-record-check" not in release_check_body:
        failures.append("v1-operator-trial-record-check is missing from release-check")
    if "$(MAKE) v1-operator-trial-record" not in review_candidate_body:
        failures.append("v1-operator-trial-record is missing from review-candidate")
    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("v1.0 operator trial record is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("v1.0 operator trial record is missing from docs-site inputs")
    if doc_rel not in packet_script:
        failures.append("v1.0 RC packet is missing the operator trial record doc")
    if "var/review-packets/v1.0/operator-trial" not in packet_script:
        failures.append("v1.0 RC packet artifact map is missing operator trial record path")
    if "make v1-operator-trial-record" not in readme:
        failures.append("README is missing operator trial record command")
    if doc_rel not in readme:
        failures.append("README is missing operator trial record doc")
    if "Ithildin v1.0 Operator Trial Record" not in review_index:
        failures.append("review docs index is missing v1.0 operator trial record")
    return failures


def _git(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
