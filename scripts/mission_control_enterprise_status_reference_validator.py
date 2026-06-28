"""Reference-validate Mission Control enterprise status fixtures."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import mission_control_enterprise_status_fixtures, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/mission-control-enterprise-status-reference-validator.md"
VALID_ID = "MC-STATUS-VALID-001"
NEGATIVE_COUNT = 10
SAFE_REASON_RE = re.compile(r"^[a-z0-9_:-]+$")
STATUS_PHRASE = (
    "Status: reference validator for Mission Control enterprise status display/import fixtures."
)

BOUNDARY_FLAGS = {
    "runtime_changes_allowed": False,
    "mission_control_runtime_allowed": False,
    "mission_control_execution_allowed": False,
    "mission_control_policy_authority_allowed": False,
    "mission_control_approval_authority_allowed": False,
    "mission_control_audit_authority_allowed": False,
    "polling_or_mutating_ithildin_apis_allowed": False,
    "local_model_invocation_allowed": False,
    "live_vm_inspection_allowed": False,
    "sandbox_orchestration_allowed": False,
    "trusted_host_promotion_allowed": False,
    "siem_adapter_allowed": False,
    "compliance_automation_allowed": False,
    "public_security_product_positioning_allowed": False,
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
            generated = mission_control_enterprise_status_fixtures.build_fixture_pack(
                repo_root, Path(tmp) / "mission-control-enterprise-status-fixtures"
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
    fixture_doc = _read(repo_root / mission_control_enterprise_status_fixtures.DOC_REL)
    matrix_doc = _read(
        repo_root / "docs/codex/mission-control-enterprise-status-acceptance-matrix.md"
    )
    import_contract = _read(
        repo_root / "docs/codex/mission-control-enterprise-status-import-contract.md"
    )
    ticket_doc = _read(
        repo_root / "docs/codex/mission-control-integration-implementation-ticket.md"
    )
    doc = _read(repo_root / DOC_REL)
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    for phrase in [
        STATUS_PHRASE,
        "make mission-control-enterprise-status-reference-validator",
        "display-only validation oracle",
        "does not approve Mission Control enterprise status importer implementation",
        "does not call Mission Control",
        VALID_ID,
        "MC-STATUS-NEG-010",
    ]:
        if phrase not in doc:
            failures.append(
                "enterprise status reference validator doc is missing phrase: "
                f"{phrase}"
            )
    if "mission-control-enterprise-status-reference-validator:" not in makefile:
        failures.append(
            "Make target is missing: mission-control-enterprise-status-reference-validator"
        )
    if (
        "mission-control-enterprise-status-reference-validator" not in release_check_body
        and "release-check: mission-control-enterprise-status-reference-validator" not in makefile
    ):
        failures.append("enterprise status reference validator is missing from release-check")
    if "$(MAKE) mission-control-enterprise-status-reference-validator" not in review_candidate_body:
        failures.append("enterprise status reference validator is missing from review-candidate")
    if "make mission-control-enterprise-status-reference-validator" not in readme:
        failures.append("README is missing enterprise status reference validator command")
    if DOC_REL not in docs_site:
        failures.append(
            "enterprise status reference validator doc is missing from docs-site inputs"
        )
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise status reference validator doc is missing from review docs")
    if DOC_REL not in v1_packet:
        failures.append("enterprise status reference validator doc is missing from v1 RC packet")
    if "Mission Control Enterprise Status Reference Validator" not in review_index:
        failures.append("review-docs index is missing enterprise status reference validator doc")
    if "mission-control-enterprise-status-reference-validator" not in release_guardrails:
        failures.append("release guardrails do not require enterprise status reference validator")
    if "mission-control-enterprise-status-reference-validator" not in fixture_doc:
        failures.append("enterprise status fixture doc is missing reference validator pointer")
    if "mission-control-enterprise-status-reference-validator" not in matrix_doc:
        failures.append(
            "enterprise status acceptance matrix is missing reference validator pointer"
        )
    if "mission-control-enterprise-status-reference-validator" not in import_contract:
        failures.append("enterprise status import contract is missing reference validator pointer")
    if "mission-control-enterprise-status-reference-validator" not in ticket_doc:
        failures.append(
            "implementation ticket is missing enterprise status reference validator pointer"
        )

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
        "safe_reason_labels_only": fixture_report["safe_reason_labels_only"],
        "forbidden_payload_key_cases_rejected": fixture_report[
            "forbidden_payload_key_cases_rejected"
        ],
        "tool_count": 24,
        **BOUNDARY_FLAGS,
    }


def _validate_fixture_dir(fixture_dir: Path) -> dict[str, Any]:
    failures: list[str] = []
    summary_path = fixture_dir / mission_control_enterprise_status_fixtures.SUMMARY_NAME
    valid_path = fixture_dir / mission_control_enterprise_status_fixtures.VALID_NAME
    if not summary_path.exists():
        failures.append("enterprise status fixture summary is missing")
        summary: dict[str, Any] = {}
    else:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if not valid_path.exists():
        failures.append("valid enterprise status fixture payload is missing")
        valid_payload: dict[str, Any] = {}
    else:
        valid_payload = json.loads(valid_path.read_text(encoding="utf-8"))

    valid_reasons = mission_control_enterprise_status_fixtures._validate_for_display_import(
        valid_payload
    )
    if valid_reasons:
        failures.append("valid enterprise status fixture was rejected: " + ", ".join(valid_reasons))

    negative_cases = summary.get("negative_cases", [])
    if len(negative_cases) != NEGATIVE_COUNT:
        failures.append(f"reference validator expects {NEGATIVE_COUNT} negative fixtures")

    rejected = 0
    all_reason_labels: list[str] = []
    forbidden_payload_key_cases_rejected = True
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
        reasons = mission_control_enterprise_status_fixtures._validate_for_display_import(payload)
        expected = sorted(case.get("expected_reasons", []))
        all_reason_labels.extend(reasons)
        if not reasons:
            failures.append(f"{case_id} negative enterprise status fixture was accepted")
        else:
            rejected += 1
        if reasons != expected:
            failures.append(
                f"{case_id} safe reason mismatch: expected {expected}, observed {reasons}"
            )
        if _contains_forbidden_key(payload):
            if "forbidden_payload_field" not in reasons:
                forbidden_payload_key_cases_rejected = False
                failures.append(f"{case_id} contains forbidden keys without safe rejection reason")

    safe_reason_labels_only = all(SAFE_REASON_RE.match(reason) for reason in all_reason_labels)
    if not safe_reason_labels_only:
        failures.append("enterprise status reference validator observed unsafe reason labels")

    return {
        "failures": failures,
        "fixture_source": fixture_dir.as_posix(),
        "valid_fixture_id": VALID_ID,
        "valid_fixture_accepted": not valid_reasons,
        "negative_case_count": len(negative_cases),
        "negative_cases_rejected": rejected,
        "safe_reason_labels_only": safe_reason_labels_only,
        "forbidden_payload_key_cases_rejected": forbidden_payload_key_cases_rejected,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Mission Control enterprise status reference validator",
        f"valid: {str(report['valid']).lower()}",
        f"validator_doc: {report['validator_doc']}",
        f"fixture_source: {report['fixture_source']}",
        f"valid_fixture_id: {report['valid_fixture_id']}",
        f"valid_fixture_accepted: {str(report['valid_fixture_accepted']).lower()}",
        f"negative_case_count: {report['negative_case_count']}",
        f"negative_cases_rejected: {report['negative_cases_rejected']}",
        f"safe_reason_labels_only: {str(report['safe_reason_labels_only']).lower()}",
        "forbidden_payload_key_cases_rejected: "
        f"{str(report['forbidden_payload_key_cases_rejected']).lower()}",
        f"tool_count: {report['tool_count']}",
    ]
    lines.extend(f"{key}: {str(value).lower()}" for key, value in BOUNDARY_FLAGS.items())
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _contains_forbidden_key(value: Any) -> bool:
    return mission_control_enterprise_status_fixtures._contains_forbidden_key(value)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
