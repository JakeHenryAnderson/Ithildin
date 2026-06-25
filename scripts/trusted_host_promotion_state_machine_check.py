"""Validate the trusted-host promotion state-machine contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/trusted-host-promotion-state-machine.md"
DOC_NAME = "trusted-host-promotion-state-machine.md"

REQUIRED_STATES = [
    "not_promoted",
    "promotion_requested",
    "promotion_reviewing",
    "promotion_approved",
    "promotion_in_progress",
    "promotion_completed",
    "promotion_rejected",
    "promotion_expired",
    "promotion_conflicted",
    "promotion_stale",
    "promotion_replay_denied",
    "promotion_recovery_required",
]

REQUIRED_PHRASES = [
    "Status: design-only state-machine contract for `ERG-005` and `PRD-TRUSTED-HOST-001`.",
    "Current governed tool count: `24`.",
    "Current `ERG-005` status: `blocked`.",
    "Current selected capability: `not selected`.",
    "make trusted-host-promotion-state-machine-check",
    "Only `not_promoted` is valid in current runtime/demo evidence.",
    "Allowed Transition Sketch",
    "Stable Evidence Fields",
    "Transition Denials",
    "No transition may skip approval evidence",
    "hash binding",
    "policy/manifest evidence",
    "one-time scope evidence",
    "runtime_promotion_performed",
    "auto_promotion_performed",
    "decision record required: `true`",
    "implementation approved: `false`",
    "runtime changes allowed: `false`",
    "trusted-host promotion allowed: `false`",
    "direct host writes allowed: `false`",
    "overwrite/delete/move allowed: `false`",
    "broad archive extraction allowed: `false`",
    "automatic promotion allowed: `false`",
    "promotion without exact artifact hash binding allowed: `false`",
    "promotion without approval evidence allowed: `false`",
    "Mission Control runtime allowed: `false`",
    "local model invocation allowed: `false`",
    "sandbox orchestration allowed: `false`",
    "SIEM adapter allowed: `false`",
    "new power classes allowed: `false`",
    "public/security-product positioning allowed: `false`",
]

REQUIRED_TRANSITIONS = [
    "`not_promoted` | `promotion_requested`",
    "`promotion_requested` | `promotion_reviewing`",
    "`promotion_reviewing` | `promotion_approved`",
    "`promotion_requested` | `promotion_rejected`",
    "`promotion_reviewing` | `promotion_rejected`",
    "`promotion_approved` | `promotion_in_progress`",
    "`promotion_in_progress` | `promotion_completed`",
    "`promotion_requested` | `promotion_expired`",
    "`promotion_reviewing` | `promotion_expired`",
    "`promotion_approved` | `promotion_expired`",
    "`promotion_requested` | `promotion_conflicted`",
    "`promotion_reviewing` | `promotion_conflicted`",
    "`promotion_approved` | `promotion_stale`",
    "`promotion_approved` | `promotion_replay_denied`",
    "`promotion_in_progress` | `promotion_recovery_required`",
]

FORBIDDEN_PHRASES = [
    "trusted-host promotion is implemented",
    "trusted-host promotion is approved",
    "host writes are approved",
    "automatic promotion is approved",
    "overwrite is approved",
    "delete is approved",
    "archive extraction is approved",
    "promotion implementation is approved",
    "production-ready",
    "secure sandbox",
    "compliance-grade",
]


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_path = repo_root / DOC_REL
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_guardrails = (repo_root / "scripts/release_guardrails.py").read_text(
        encoding="utf-8"
    )
    enterprise = (repo_root / "docs/codex/enterprise-readiness-runway.md").read_text(
        encoding="utf-8"
    )
    gap_matrix = (repo_root / "docs/codex/enterprise-readiness-gap-matrix.md").read_text(
        encoding="utf-8"
    )
    decision_register = (repo_root / "docs/codex/post-rc-decision-register.md").read_text(
        encoding="utf-8"
    )
    intake = (repo_root / "docs/codex/trusted-host-promotion-decision-intake.md").read_text(
        encoding="utf-8"
    )
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("trusted-host promotion state-machine doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for state in REQUIRED_STATES:
            if f"`{state}`" not in text:
                failures.append(f"trusted-host promotion state-machine is missing state: {state}")
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(
                    f"trusted-host promotion state-machine is missing phrase: {phrase}"
                )
        for transition in REQUIRED_TRANSITIONS:
            if transition not in text:
                failures.append(
                    "trusted-host promotion state-machine is missing transition: "
                    f"{transition}"
                )
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    "trusted-host promotion state-machine contains forbidden phrase: "
                    f"{phrase}"
                )

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("trusted-host promotion state-machine is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("trusted-host promotion state-machine is missing from docs-site inputs")
    if DOC_NAME not in readme:
        failures.append("README is missing trusted-host promotion state-machine doc")
    if "make trusted-host-promotion-state-machine-check" not in readme:
        failures.append("README is missing trusted-host promotion state-machine command")
    if "trusted-host-promotion-state-machine-check:" not in makefile:
        failures.append("Make target is missing: trusted-host-promotion-state-machine-check")
    if "trusted-host-promotion-state-machine-check" not in release_check_body:
        failures.append("trusted-host-promotion-state-machine-check missing from release-check")
    if "trusted-host-promotion-state-machine-check" not in release_guardrails:
        failures.append("release guardrails do not require trusted-host promotion state machine")
    if DOC_NAME not in enterprise:
        failures.append("enterprise runway is missing trusted-host promotion state-machine pointer")
    if DOC_NAME not in gap_matrix:
        failures.append(
            "enterprise gap matrix is missing trusted-host promotion state-machine pointer"
        )
    if DOC_NAME not in decision_register:
        failures.append(
            "post-RC decision register is missing trusted-host promotion state-machine pointer"
        )
    if DOC_NAME not in intake:
        failures.append("trusted-host promotion decision intake is missing state-machine pointer")
    if "Trusted-Host Promotion State Machine" not in review_index:
        failures.append("review docs index is missing trusted-host promotion state-machine entry")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "state_machine_doc": DOC_REL,
        "tool_count": 24,
        "erg_005_status": "blocked",
        "prd_id": "PRD-TRUSTED-HOST-001",
        "state_count": len(REQUIRED_STATES),
        "transition_count": len(REQUIRED_TRANSITIONS),
        "current_runtime_state": "not_promoted",
        "decision_record_required": True,
        "implementation_approved": False,
        "runtime_changes_allowed": False,
        "trusted_host_promotion_allowed": False,
        "direct_host_writes_allowed": False,
        "overwrite_delete_move_allowed": False,
        "broad_archive_extraction_allowed": False,
        "automatic_promotion_allowed": False,
        "promotion_without_exact_artifact_hash_binding_allowed": False,
        "promotion_without_approval_evidence_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin trusted-host promotion state-machine check",
        f"valid: {str(report['valid']).lower()}",
        f"state_machine_doc: {report['state_machine_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_005_status: {report['erg_005_status']}",
        f"prd_id: {report['prd_id']}",
        f"state_count: {report['state_count']}",
        f"transition_count: {report['transition_count']}",
        f"current_runtime_state: {report['current_runtime_state']}",
        f"decision_record_required: {str(report['decision_record_required']).lower()}",
        f"implementation_approved: {str(report['implementation_approved']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "trusted_host_promotion_allowed: "
        f"{str(report['trusted_host_promotion_allowed']).lower()}",
        f"direct_host_writes_allowed: {str(report['direct_host_writes_allowed']).lower()}",
        "overwrite_delete_move_allowed: "
        f"{str(report['overwrite_delete_move_allowed']).lower()}",
        "broad_archive_extraction_allowed: "
        f"{str(report['broad_archive_extraction_allowed']).lower()}",
        f"automatic_promotion_allowed: {str(report['automatic_promotion_allowed']).lower()}",
        "promotion_without_exact_artifact_hash_binding_allowed: "
        f"{str(report['promotion_without_exact_artifact_hash_binding_allowed']).lower()}",
        "promotion_without_approval_evidence_allowed: "
        f"{str(report['promotion_without_approval_evidence_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


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


if __name__ == "__main__":
    raise SystemExit(main())
