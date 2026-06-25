"""Validate the trusted-host promotion source/destination zone contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/trusted-host-promotion-zone-contract.md"
DOC_NAME = "trusted-host-promotion-zone-contract.md"

REQUIRED_PREFIXES = [
    "sandbox://",
    "host-staging://",
    "approved://",
    "evidence://",
]

REQUIRED_PHRASES = [
    (
        "Status: design-only source/destination zone contract for `ERG-005` "
        "and `PRD-TRUSTED-HOST-001`."
    ),
    "Current governed tool count: `24`.",
    "Current `ERG-005` status: `blocked`.",
    "Current selected capability: `not selected`.",
    "make trusted-host-promotion-zone-contract-check",
    "Zone Vocabulary",
    "Zone Movement Rules",
    "Label Shape",
    "Required Future Evidence",
    "Current Implementation Boundary",
    "future evidence identifiers, not filesystem authority",
    "Raw filesystem paths are forbidden in promotion evidence.",
    "sandbox://artifact -> host-staging://artifact -> approved://artifact",
    "one artifact, one approval, and one bounded destination label",
    "source artifact hash, staging hash, and approved-output hash must match",
    "promotion_status",
    "not_promoted",
    "runtime_promotion_performed",
    "trusted_host_write_performed",
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

REQUIRED_FORBIDDEN_MOVEMENTS = [
    "arbitrary host path",
    "without staging evidence",
    "overwrite",
    "delete",
    "move",
    "chmod",
    "archive extraction",
    "directory merge",
    ".git",
    "hidden",
    "symlink",
    "hardlink",
    "absolute paths",
    "parent traversal",
    "encoded traversal",
    "URL-shaped destinations",
    "Unicode ambiguity",
    "control characters",
    "raw host paths",
    "raw sandbox-internal paths",
    "automatic promotion",
    "batch promotion",
    "wildcard promotion",
    "recursive promotion",
    "without operator acknowledgement",
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

LABEL_PATTERN = re.compile(r"^(sandbox|host-staging|approved|evidence)://[a-z0-9][a-z0-9._/-]*$")


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
    state_machine = (repo_root / "docs/codex/trusted-host-promotion-state-machine.md").read_text(
        encoding="utf-8"
    )
    negative_fixtures = (
        repo_root / "docs/codex/trusted-host-promotion-negative-fixtures.md"
    ).read_text(encoding="utf-8")
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("trusted-host promotion zone contract doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for prefix in REQUIRED_PREFIXES:
            if prefix not in text:
                failures.append(f"trusted-host promotion zone contract missing prefix: {prefix}")
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"trusted-host promotion zone contract missing phrase: {phrase}")
        for phrase in REQUIRED_FORBIDDEN_MOVEMENTS:
            if phrase not in text:
                failures.append(
                    f"trusted-host promotion zone contract missing forbidden movement: {phrase}"
                )
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    "trusted-host promotion zone contract contains forbidden phrase: "
                    f"{phrase}"
                )

    sample_labels = [
        "sandbox://demo/output.txt",
        "host-staging://demo/output.txt",
        "approved://demo/output.txt",
        "evidence://promotion/promotion_fixture",
    ]
    unsafe_labels = [
        "/Users/demo/output.txt",
        "sandbox://../escape",
        "host-staging://demo/.git/config",
        "approved://demo/output\x00.txt",
    ]
    for label in sample_labels:
        if not _is_safe_label(label):
            failures.append(f"sample promotion zone label failed validation: {label}")
    for label in unsafe_labels:
        if _is_safe_label(label):
            failures.append(f"unsafe promotion zone label was accepted: {label!r}")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("trusted-host promotion zone contract missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("trusted-host promotion zone contract missing from docs-site inputs")
    if DOC_NAME not in readme:
        failures.append("README is missing trusted-host promotion zone contract doc")
    if "make trusted-host-promotion-zone-contract-check" not in readme:
        failures.append("README is missing trusted-host promotion zone contract command")
    if "trusted-host-promotion-zone-contract-check:" not in makefile:
        failures.append("Make target is missing: trusted-host-promotion-zone-contract-check")
    if "trusted-host-promotion-zone-contract-check" not in release_check_body:
        failures.append("trusted-host promotion zone contract check missing from release-check")
    if "trusted-host-promotion-zone-contract-check" not in release_guardrails:
        failures.append("release guardrails do not require trusted-host zone contract")
    if DOC_NAME not in enterprise:
        failures.append("enterprise runway is missing trusted-host zone contract pointer")
    if DOC_NAME not in gap_matrix:
        failures.append("enterprise gap matrix is missing trusted-host zone contract pointer")
    if DOC_NAME not in decision_register:
        failures.append("post-RC decision register is missing trusted-host zone contract pointer")
    if DOC_NAME not in intake:
        failures.append("trusted-host decision intake is missing zone contract pointer")
    if DOC_NAME not in state_machine:
        failures.append("trusted-host state machine is missing zone contract pointer")
    if DOC_NAME not in negative_fixtures:
        failures.append("trusted-host negative fixtures are missing zone contract pointer")
    if "Trusted-Host Promotion Zone Contract" not in review_index:
        failures.append("review docs index is missing trusted-host zone contract entry")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "zone_contract_doc": DOC_REL,
        "tool_count": 24,
        "erg_005_status": "blocked",
        "prd_id": "PRD-TRUSTED-HOST-001",
        "zone_prefixes": REQUIRED_PREFIXES,
        "sample_label_count": len(sample_labels),
        "unsafe_label_count": len(unsafe_labels),
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


def _is_safe_label(label: str) -> bool:
    if not LABEL_PATTERN.match(label):
        return False
    path = label.split("://", 1)[1]
    if "\x00" in path:
        return False
    segments = [segment for segment in path.split("/") if segment]
    if any(segment in {".", "..", ".git"} for segment in segments):
        return False
    if any(segment.startswith(".") for segment in segments):
        return False
    return True


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin trusted-host promotion zone contract check",
        f"valid: {str(report['valid']).lower()}",
        f"zone_contract_doc: {report['zone_contract_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_005_status: {report['erg_005_status']}",
        f"prd_id: {report['prd_id']}",
        "zone_prefixes: " + ", ".join(report["zone_prefixes"]),
        f"sample_label_count: {report['sample_label_count']}",
        f"unsafe_label_count: {report['unsafe_label_count']}",
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
        lines.append("")
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
