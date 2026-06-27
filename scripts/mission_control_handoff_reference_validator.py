"""Reference-validate Mission Control handoff fixtures as display-only evidence."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    mission_control_handoff_fixture_pack,
    mission_control_handoff_negative_fixtures_check,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/mission-control-handoff-reference-validator.md"

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
    parser.add_argument(
        "--fixture-dir",
        type=Path,
        help="Validate an existing generated fixture directory instead of a temporary pack.",
    )
    args = parser.parse_args()

    report = build_report(ROOT, args.fixture_dir)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path, fixture_dir: Path | None = None) -> dict[str, Any]:
    failures: list[str] = []
    if fixture_dir is None:
        with tempfile.TemporaryDirectory() as tmp:
            generated = mission_control_handoff_fixture_pack.build_fixture_pack(
                repo_root, Path(tmp) / "mission-control-handoff-fixtures"
            )
            fixture_report = _validate_fixture_dir(generated)
    else:
        fixture_report = _validate_fixture_dir(fixture_dir)
    failures.extend(fixture_report["failures"])

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    v1_packet = _read(repo_root / "scripts/v1_rc_packet.py")
    fixture_doc = _read(repo_root / mission_control_handoff_fixture_pack.DOC_REL)
    matrix_doc = _read(repo_root / "docs/codex/mission-control-importer-acceptance-matrix.md")
    ticket_doc = _read(
        repo_root / "docs/codex/mission-control-integration-implementation-ticket.md"
    )
    doc = _read(repo_root / DOC_REL)
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    for phrase in [
        "Status: reference validator for Mission Control handoff display/import fixtures.",
        "make mission-control-handoff-reference-validator",
        "display-only validation oracle",
        "does not approve Mission Control runtime importer behavior",
        "does not call Mission Control",
        "MC-HANDOFF-VALID-001",
        "MC-HANDOFF-NEG-014",
    ]:
        if phrase not in doc:
            failures.append(f"reference validator doc is missing phrase: {phrase}")
    if "mission-control-handoff-reference-validator:" not in makefile:
        failures.append("Make target is missing: mission-control-handoff-reference-validator")
    if (
        "mission-control-handoff-reference-validator" not in release_check_body
        and "release-check: mission-control-handoff-reference-validator" not in makefile
    ):
        failures.append("reference validator is missing from release-check")
    if "$(MAKE) mission-control-handoff-reference-validator" not in review_candidate_body:
        failures.append("reference validator is missing from review-candidate")
    if "make mission-control-handoff-reference-validator" not in readme:
        failures.append("README is missing reference validator command")
    if DOC_REL not in docs_site:
        failures.append("reference validator doc is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("reference validator doc is missing from review docs")
    if DOC_REL not in v1_packet:
        failures.append("reference validator doc is missing from v1 RC packet")
    if "Mission Control Handoff Reference Validator" not in review_index:
        failures.append("review-docs index is missing reference validator doc")
    if "mission-control-handoff-reference-validator" not in release_guardrails:
        failures.append("release guardrails do not require reference validator")
    if "mission-control-handoff-reference-validator" not in fixture_doc:
        failures.append("fixture pack doc is missing reference validator pointer")
    if "mission-control-handoff-reference-validator" not in matrix_doc:
        failures.append("acceptance matrix is missing reference validator pointer")
    if "mission-control-handoff-reference-validator" not in ticket_doc:
        failures.append("implementation ticket is missing reference validator pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "validator_doc": DOC_REL,
        "fixture_source": fixture_report["fixture_source"],
        "valid_fixture_id": fixture_report["valid_fixture_id"],
        "valid_fixture_accepted": fixture_report["valid_fixture_accepted"],
        "negative_case_count": fixture_report["negative_case_count"],
        "negative_cases_rejected": fixture_report["negative_cases_rejected"],
        "safe_reason_labels_only": True,
        "tool_count": 24,
        **BOUNDARY_FLAGS,
    }


def _validate_fixture_dir(fixture_dir: Path) -> dict[str, Any]:
    failures: list[str] = []
    summary_path = fixture_dir / mission_control_handoff_fixture_pack.SUMMARY_NAME
    valid_path = fixture_dir / mission_control_handoff_fixture_pack.VALID_NAME
    if not summary_path.exists():
        failures.append("fixture summary is missing")
        summary: dict[str, Any] = {}
    else:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if not valid_path.exists():
        failures.append("valid fixture payload is missing")
        valid_payload: dict[str, Any] = {}
    else:
        valid_payload = json.loads(valid_path.read_text(encoding="utf-8"))

    valid_reasons = mission_control_handoff_negative_fixtures_check._validate_for_display_import(
        valid_payload
    )
    if valid_reasons:
        failures.append("valid fixture was rejected: " + ", ".join(valid_reasons))

    negative_cases = summary.get("negative_cases", [])
    if len(negative_cases) != 14:
        failures.append("reference validator expects 14 negative fixtures")

    rejected = 0
    case_rows = []
    for case in negative_cases:
        case_id = case.get("id", "unknown")
        rel_path = case.get("path")
        if not isinstance(rel_path, str):
            failures.append(f"{case_id} fixture path is invalid")
            continue
        payload_path = fixture_dir / rel_path
        if not payload_path.exists():
            failures.append(f"{case_id} fixture payload is missing")
            continue
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        reasons = mission_control_handoff_negative_fixtures_check._validate_for_display_import(
            payload
        )
        expected = sorted(case.get("expected_reasons", []))
        if not reasons:
            failures.append(f"{case_id} negative fixture was accepted")
        else:
            rejected += 1
        if reasons != expected:
            failures.append(
                f"{case_id} safe reason mismatch: expected {expected}, observed {reasons}"
            )
        case_rows.append(
            {
                "id": case_id,
                "accepted": not reasons,
                "observed_reasons": reasons,
                "expected_reasons": expected,
            }
        )

    return {
        "failures": failures,
        "fixture_source": fixture_dir.as_posix(),
        "valid_fixture_id": "MC-HANDOFF-VALID-001",
        "valid_fixture_accepted": not valid_reasons,
        "negative_case_count": len(negative_cases),
        "negative_cases_rejected": rejected,
        "cases": case_rows,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Mission Control handoff reference validator",
        f"valid: {str(report['valid']).lower()}",
        f"validator_doc: {report['validator_doc']}",
        f"fixture_source: {report['fixture_source']}",
        f"valid_fixture_id: {report['valid_fixture_id']}",
        f"valid_fixture_accepted: {str(report['valid_fixture_accepted']).lower()}",
        f"negative_case_count: {report['negative_case_count']}",
        f"negative_cases_rejected: {report['negative_cases_rejected']}",
        f"safe_reason_labels_only: {str(report['safe_reason_labels_only']).lower()}",
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
