"""Validate the Mission Control importer acceptance matrix."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import mission_control_handoff_fixture_pack, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/mission-control-importer-acceptance-matrix.md"
DOC = ROOT / DOC_REL
VALID_ID = "MC-HANDOFF-VALID-001"
NEGATIVE_IDS = [f"MC-HANDOFF-NEG-{number:03d}" for number in range(1, 15)]

REQUIRED_DOC_PHRASES = [
    "Status: acceptance matrix for future Mission Control display/import tests.",
    "make mission-control-importer-acceptance-matrix-check",
    "make mission-control-handoff-fixture-pack",
    "accepted_metadata_only",
    "rejected_safe_reason",
    VALID_ID,
    "MC-HANDOFF-NEG-001",
    "MC-HANDOFF-NEG-014",
    "Ithildin remains the",
    "execution, policy, approval, and audit authority",
    "does not approve Mission Control importer implementation",
]

FORBIDDEN_DOC_PHRASES = [
    "Mission Control may execute",
    "Mission Control may approve",
    "Mission Control may call Ithildin APIs",
    "runtime importer behavior is approved",
    "trusted-host promotion is implemented",
    "production-ready",
    "compliance-grade",
    "secure sandbox",
]

BOUNDARY_FLAGS = {
    "runtime_changes_allowed": False,
    "mission_control_runtime_allowed": False,
    "mission_control_execution_allowed": False,
    "mission_control_policy_authority_allowed": False,
    "mission_control_approval_authority_allowed": False,
    "mission_control_audit_authority_allowed": False,
    "local_model_invocation_allowed": False,
    "sandbox_orchestration_allowed": False,
    "trusted_host_promotion_allowed": False,
    "new_power_classes_allowed": False,
}


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
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    implementation_ticket = _read(
        repo_root / "docs/codex/mission-control-integration-implementation-ticket.md"
    )
    fixture_doc = _read(repo_root / mission_control_handoff_fixture_pack.DOC_REL)
    doc = _read(repo_root / DOC_REL)
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    if not doc:
        failures.append("Mission Control importer acceptance matrix doc is missing")
    else:
        lowered = doc.lower()
        for phrase in REQUIRED_DOC_PHRASES:
            if phrase not in doc:
                failures.append(f"acceptance matrix is missing phrase: {phrase}")
        for phrase in FORBIDDEN_DOC_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"acceptance matrix contains forbidden phrase: {phrase}")
        if doc.count(VALID_ID) < 1:
            failures.append(f"acceptance matrix is missing valid fixture ID: {VALID_ID}")
        for case_id in NEGATIVE_IDS:
            if doc.count(case_id) < 1:
                failures.append(f"acceptance matrix is missing negative fixture ID: {case_id}")

    try:
        fixture_pack_dir = mission_control_handoff_fixture_pack.build_fixture_pack(
            repo_root,
            mission_control_handoff_fixture_pack.DEFAULT_OUTPUT_DIR,
        )
        summary = json.loads(
            fixture_pack_dir.joinpath(mission_control_handoff_fixture_pack.SUMMARY_NAME).read_text(
                encoding="utf-8"
            )
        )
    except Exception as exc:  # pragma: no cover - surfaced in report.
        failures.append(f"fixture pack could not be generated: {exc}")
        summary = {}

    valid_payload = summary.get("valid_payload", {})
    if valid_payload.get("expected_accept") is not True:
        failures.append("valid fixture must be expected to import as metadata-only")
    negative_cases = summary.get("negative_cases", [])
    if len(negative_cases) != 14:
        failures.append("fixture pack must expose 14 negative cases")
    for case in negative_cases:
        case_id = case.get("id")
        if case_id not in NEGATIVE_IDS:
            failures.append(f"fixture pack has unexpected negative case: {case_id}")
            continue
        if case.get("expected_accept") is not False:
            failures.append(f"negative fixture must be rejected: {case_id}")
        if not case.get("expected_reasons"):
            failures.append(f"negative fixture must have safe reason labels: {case_id}")
        if case_id and case_id not in doc:
            failures.append(f"acceptance matrix does not map generated case: {case_id}")

    if "mission-control-importer-acceptance-matrix-check:" not in makefile:
        failures.append("Make target is missing: mission-control-importer-acceptance-matrix-check")
    if "mission-control-importer-acceptance-matrix-check" not in release_check_body:
        failures.append("acceptance matrix check is missing from release-check")
    if "$(MAKE) mission-control-importer-acceptance-matrix-check" not in review_candidate_body:
        failures.append("acceptance matrix check is missing from review-candidate")
    if "make mission-control-importer-acceptance-matrix-check" not in readme:
        failures.append("README is missing acceptance matrix command")
    if DOC_REL not in docs_site:
        failures.append("acceptance matrix doc is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("acceptance matrix doc is missing from review docs")
    if "Mission Control Importer Acceptance Matrix" not in review_index:
        failures.append("review-docs index is missing acceptance matrix doc")
    if "mission-control-importer-acceptance-matrix-check" not in release_guardrails:
        failures.append("release guardrails do not require acceptance matrix check")
    if "mission-control-importer-acceptance-matrix" not in implementation_ticket:
        failures.append("implementation ticket is missing acceptance matrix pointer")
    if "mission-control-importer-acceptance-matrix" not in fixture_doc:
        failures.append("fixture pack doc is missing acceptance matrix pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "matrix_doc": DOC_REL,
        "valid_fixture_id": VALID_ID,
        "negative_case_count": len(negative_cases),
        "tool_count": 24,
        **BOUNDARY_FLAGS,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Mission Control importer acceptance matrix check",
        f"valid: {str(report['valid']).lower()}",
        f"matrix_doc: {report['matrix_doc']}",
        f"valid_fixture_id: {report['valid_fixture_id']}",
        f"negative_case_count: {report['negative_case_count']}",
        f"tool_count: {report['tool_count']}",
    ]
    lines.extend(f"{key}: {str(value).lower()}" for key, value in BOUNDARY_FLAGS.items())
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
