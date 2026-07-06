"""Summarize the current development-speed and handoff posture."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_current_checkpoint,
    enterprise_review_send_preflight,
    release_check_profile,
    review_docs,
    technical_mvp_operator_trial_readiness,
    validation_decision,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/development-efficiency-status.md"
DOC_TITLE = "Development Efficiency Status"

REQUIRED_DOC_PHRASES = [
    "Status: checked development-efficiency view.",
    "make development-efficiency-status",
    "make status-now",
    "make validation-decision",
    "make validation-recommendation",
    "make artifact-freshness-check",
    "make release-check-profile",
    "make technical-mvp-operator-trial-readiness",
    "make enterprise-current-checkpoint",
    "make enterprise-review-send-preflight",
    "current ERG-005 trusted-host review artifact",
    "freshness",
    "current ERG-005 trusted-host review action",
    "historical ERG-003/ERG-002 handoff artifacts only as lineage",
    "make progress-check",
    "make progress-check ARGS=--refresh-stale",
    "make handoff-dry-run",
    "make enterprise-send-quick-check",
    "make dev-check",
    "make release-check",
    "make review-candidate",
    "make enterprise-review-send-refresh",
    "review-candidate artifact freshness",
    "diagnostic shortcut, not release proof",
    "does not start services",
    "does not call governed tools",
    "does not approve runtime changes",
    "does not replace release-check",
]

V1_RC_PACKET_INDEX = Path("var/review-packets/v1.0/rc/00_V1_RC_PACKET_INDEX.md")
REVIEW_CANDIDATE_RELEASE_TRANSCRIPT = Path(
    "var/review-packets/v3/review-candidate-release-check.txt"
)
MAX_RENDERED_READINESS_WARNINGS = 12

FORBIDDEN_PHRASES = [
    "release proof replacement",
    "skip release-check",
    "production-ready",
    "enterprise-ready",
    "approved runtime changes",
    "approved capability expansion",
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
    validation = validation_decision.build_report()
    profile = release_check_profile.build_report(repo_root)
    technical_mvp = technical_mvp_operator_trial_readiness.build_report(repo_root)
    enterprise = enterprise_current_checkpoint.build_report(repo_root)
    enterprise_send_preflight = enterprise_review_send_preflight.build_report(repo_root)

    failures = []
    readiness_warnings = []
    for name, report in [
        ("validation-decision", validation),
        ("release-check-profile", profile),
    ]:
        if report.get("valid") is not True:
            failures.append(f"{name} is not valid")
            failures.extend(f"{name}: {failure}" for failure in report.get("failures", []))
    for name, report in [
        ("technical-mvp-operator-trial-readiness", technical_mvp),
        ("enterprise-current-checkpoint", enterprise),
        ("enterprise-review-send-preflight", enterprise_send_preflight),
    ]:
        if report.get("valid") is not True:
            readiness_warnings.append(f"{name} is not valid")
            readiness_warnings.extend(
                f"{name}: {failure}" for failure in report.get("failures", [])
            )

    failures.extend(_wiring_failures(repo_root))

    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    handoff_status = _handoff_artifact_status(repo_root, current_commit=commit)
    next_development_commands = list(validation.get("next_development_commands", []))
    deferred_handoff_commands = list(validation.get("deferred_handoff_commands", []))
    recommended_now_commands = (
        next_development_commands if dirty else ["make dev-check"]
    )

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "readiness_warnings": readiness_warnings,
        "readiness_warning_count": len(readiness_warnings),
        "status_doc": DOC_REL,
        "commit": commit,
        "dirty": dirty,
        "tool_count": technical_mvp.get("tool_count"),
        "latest_implemented_tool": technical_mvp.get("latest_implemented_tool"),
        "selected_capability": technical_mvp.get("selected_capability"),
        "validation_mode": validation.get("recommended_mode"),
        "release_or_handoff_required": validation.get("release_or_handoff_required"),
        "next_development_commands": next_development_commands,
        "deferred_handoff_commands": deferred_handoff_commands,
        "release_slice_commands": validation.get("release_slice_commands", []),
        "recommended_now_commands": recommended_now_commands,
        "release_check_target_count": profile.get("target_count"),
        "release_check_unique_target_count": profile.get("unique_target_count"),
        "release_check_heaviest_categories": profile.get("heaviest_categories", []),
        "technical_mvp_state": technical_mvp.get("technical_mvp_state"),
        "operator_trial_ready": technical_mvp.get("operator_trial_ready"),
        "operator_trial_observed": technical_mvp.get("operator_trial_observed"),
        "hands_on_trial_required": technical_mvp.get("hands_on_trial_required"),
        "enterprise_next_action": enterprise.get("next_action"),
        "recommended_send_set": enterprise.get("recommended_send_set"),
        "enterprise_send_ready": enterprise_send_preflight.get("valid"),
        "enterprise_send_artifact_commits_match_current": enterprise_send_preflight.get(
            "artifact_commits_match_current"
        ),
        "enterprise_send_artifact_payloads_clean": enterprise_send_preflight.get(
            "artifact_payloads_clean"
        ),
        "enterprise_send_artifact_hashes_match_files": enterprise_send_preflight.get(
            "artifact_hashes_match_files"
        ),
        **handoff_status,
        "response_present_count": enterprise.get("response_present_count"),
        "closure_ready_count": enterprise.get("closure_ready_count"),
        "recommended_handoff_commands": [
            "make release-check",
            "make review-candidate",
            "make progress-check",
            "make handoff-dry-run",
            "make enterprise-review-send-refresh",
        ],
        "handoff_artifacts": {
            "v1_rc_packet": "var/review-packets/v1.0/rc",
            "review_candidate_release_transcript": (
                "var/review-packets/v3/review-candidate-release-check.txt"
            ),
            "enterprise_dual_review_outbox": (
                "var/review-packets/v3/enterprise-dual-review-outbox"
            ),
            "enterprise_review_send_manifest": (
                "var/review-packets/v3/enterprise-review-send-manifest"
            ),
        },
        "runtime_changes_allowed": False,
        "capability_expansion_allowed": False,
        "new_power_classes_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_execution_allowed": False,
        "public_security_product_positioning_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin development efficiency status",
        f"valid: {str(report['valid']).lower()}",
        f"status_doc: {report['status_doc']}",
        f"commit: {report['commit']}",
        f"dirty: {str(report['dirty']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"latest_implemented_tool: {report['latest_implemented_tool']}",
        f"selected_capability: {report['selected_capability']}",
        f"validation_mode: {report['validation_mode']}",
        f"release_or_handoff_required: {str(report['release_or_handoff_required']).lower()}",
        f"technical_mvp_state: {report['technical_mvp_state']}",
        f"operator_trial_ready: {str(report['operator_trial_ready']).lower()}",
        f"operator_trial_observed: {str(report['operator_trial_observed']).lower()}",
        f"enterprise_next_action: {report['enterprise_next_action']}",
        f"enterprise_send_ready: {str(report['enterprise_send_ready']).lower()}",
        "enterprise_send_artifacts:",
        "- commits_match_current: "
        f"{str(report['enterprise_send_artifact_commits_match_current']).lower()}",
        "- payloads_clean: "
        f"{str(report['enterprise_send_artifact_payloads_clean']).lower()}",
        "- hashes_match_files: "
        f"{str(report['enterprise_send_artifact_hashes_match_files']).lower()}",
        "review_candidate_artifacts:",
        "- v1_rc_packet_exists: "
        f"{str(report['v1_rc_packet_exists']).lower()}",
        "- v1_rc_packet_commit_matches_current: "
        f"{str(report['v1_rc_packet_commit_matches_current']).lower()}",
        "- release_check_transcript_exists: "
        f"{str(report['review_candidate_release_transcript_exists']).lower()}",
        "- release_check_transcript_commit_matches_current: "
        f"{str(report['review_candidate_release_transcript_commit_matches_current']).lower()}",
        "- release_check_transcript_passed: "
        f"{str(report['review_candidate_release_transcript_passed']).lower()}",
        f"response_present_count: {report['response_present_count']}",
        f"closure_ready_count: {report['closure_ready_count']}",
        "recommended_now_commands:",
    ]
    lines.extend(f"- {command}" for command in report["recommended_now_commands"])
    lines.append("recommended_handoff_commands:")
    lines.extend(f"- {command}" for command in report["recommended_handoff_commands"])
    lines.append("release_check_heaviest_categories:")
    lines.extend(
        f"- {row['category']}: {row['target_count']}"
        for row in report["release_check_heaviest_categories"][:5]
    )
    lines.append("boundary_flags:")
    for key in [
        "runtime_changes_allowed",
        "capability_expansion_allowed",
        "new_power_classes_allowed",
        "sandbox_orchestration_allowed",
        "mission_control_execution_allowed",
        "public_security_product_positioning_allowed",
    ]:
        lines.append(f"- {key}: {str(report[key]).lower()}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    if report["readiness_warnings"]:
        warning_count = report["readiness_warning_count"]
        lines.append(f"readiness_warnings: {warning_count}")
        rendered_warnings = report["readiness_warnings"][
            :MAX_RENDERED_READINESS_WARNINGS
        ]
        lines.extend(f"- {warning}" for warning in rendered_warnings)
        omitted_count = warning_count - len(rendered_warnings)
        if omitted_count > 0:
            lines.append(
                f"- ... {omitted_count} more readiness warning(s); use --json for full detail"
            )
    return "\n".join(lines)


def _wiring_failures(repo_root: Path) -> list[str]:
    failures: list[str] = []
    doc_path = repo_root / DOC_REL
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("development efficiency status doc is missing")
    else:
        doc = doc_path.read_text(encoding="utf-8")
        lowered = doc.lower()
        for phrase in REQUIRED_DOC_PHRASES:
            if phrase not in doc:
                failures.append(
                    f"development efficiency status doc is missing phrase: {phrase}"
                )
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    f"development efficiency status doc contains forbidden phrase: {phrase}"
                )
        for stale_phrase in [
            "current ERG-003/ERG-002 handoff artifact freshness",
            "current ERG-003/ERG-002 send action",
        ]:
            if stale_phrase in doc:
                failures.append(
                    "development efficiency status doc contains stale active-route phrase: "
                    f"{stale_phrase}"
                )

    if "development-efficiency-status:" not in makefile:
        failures.append("Make target is missing: development-efficiency-status")
    if (
        "development-efficiency-status" not in release_check_body
        and "release-check: development-efficiency-status" not in makefile
    ):
        failures.append("development-efficiency-status is missing from release-check")
    if "make development-efficiency-status" not in readme:
        failures.append("README is missing development-efficiency-status command")
    if DOC_REL not in readme:
        failures.append("README is missing development efficiency status doc")
    if DOC_REL not in docs_site:
        failures.append("development efficiency status doc is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("development efficiency status doc is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review docs index is missing development efficiency status")
    if "development-efficiency-status" not in release_guardrails:
        failures.append("release guardrails do not require development efficiency status")
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


def _handoff_artifact_status(repo_root: Path, *, current_commit: str) -> dict[str, Any]:
    v1_packet_index = repo_root / V1_RC_PACKET_INDEX
    release_transcript = repo_root / REVIEW_CANDIDATE_RELEASE_TRANSCRIPT
    v1_packet_text = _read(v1_packet_index)
    release_transcript_text = _read(release_transcript)
    v1_packet_commit = _extract_prefixed_backtick_value(v1_packet_text, "- Commit:")
    transcript_commit = _extract_prefixed_value(release_transcript_text, "git_commit=")
    transcript_returncode = _extract_prefixed_value(release_transcript_text, "returncode=")
    return {
        "v1_rc_packet_path": V1_RC_PACKET_INDEX.as_posix(),
        "v1_rc_packet_exists": v1_packet_index.exists(),
        "v1_rc_packet_commit": v1_packet_commit,
        "v1_rc_packet_commit_matches_current": v1_packet_commit == current_commit,
        "review_candidate_release_transcript_path": (
            REVIEW_CANDIDATE_RELEASE_TRANSCRIPT.as_posix()
        ),
        "review_candidate_release_transcript_exists": release_transcript.exists(),
        "review_candidate_release_transcript_commit": transcript_commit,
        "review_candidate_release_transcript_commit_matches_current": (
            transcript_commit == current_commit
        ),
        "review_candidate_release_transcript_passed": transcript_returncode == "0",
    }


def _extract_prefixed_value(text: str, prefix: str) -> str | None:
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip()
    return None


def _extract_prefixed_backtick_value(text: str, prefix: str) -> str | None:
    for line in text.splitlines():
        if not line.startswith(prefix):
            continue
        parts = line.split("`")
        if len(parts) >= 2:
            return parts[1]
    return None


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())
