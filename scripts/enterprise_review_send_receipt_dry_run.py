"""Dry-run copied enterprise send receipts without recording review."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_review_send_receipt_template,
    enterprise_review_send_receipt_validate,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-review-send-receipt-dry-run.md"
DOC_NAME = "enterprise-review-send-receipt-dry-run.md"
BOUNDARY_FLAGS = {
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    report = build_report(ROOT)
    if args.json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    try:
        template_dir = enterprise_review_send_receipt_template.build_template(
            repo_root,
            enterprise_review_send_receipt_template.DEFAULT_OUTPUT_DIR,
        )
        template_payload = json.loads(
            (template_dir / enterprise_review_send_receipt_template.JSON_NAME).read_text(
                encoding="utf-8"
            )
        )
    except Exception as exc:  # pragma: no cover - exercised through failure report
        failures.append(f"could not build receipt template: {exc}")
        template_payload = {}

    with tempfile.TemporaryDirectory(prefix="ithildin-receipt-dry-run-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        filled_receipt_path = tmp_path / "filled-send-receipt.json"
        malformed_receipt_path = tmp_path / "malformed-send-receipt.json"

        filled_payload = _filled_receipt_payload(template_payload)
        malformed_payload = _malformed_receipt_payload(filled_payload)
        filled_receipt_path.write_text(
            json.dumps(filled_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        malformed_receipt_path.write_text(
            json.dumps(malformed_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        filled_report = enterprise_review_send_receipt_validate.build_report(
            repo_root,
            filled_receipt_path,
        )
        malformed_report = enterprise_review_send_receipt_validate.build_report(
            repo_root,
            malformed_receipt_path,
        )

    _validate_repo_wiring(repo_root, failures)

    filled_ready = (
        filled_report.get("valid") is True
        and filled_report.get("ready_for_response_intake") is True
        and filled_report.get("next_operator_action")
        == "wait_for_responses_then_run_enterprise_response_paste_preflight"
    )
    malformed_rejected = (
        malformed_report.get("valid") is False
        and malformed_report.get("ready_for_response_intake") is False
        and malformed_report.get("next_operator_action") == "fix_receipt_validation_failures"
    )
    if not filled_ready:
        failures.append("filled copied receipt did not become response-intake ready")
    if not malformed_rejected:
        failures.append("malformed copied receipt was not rejected fail-closed")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "dry_run_doc": DOC_REL,
        "tool_count": 24,
        "selected_capability": "not selected",
        "filled_receipt_ready": filled_ready,
        "malformed_receipt_rejected": malformed_rejected,
        "filled_next_operator_action": filled_report.get("next_operator_action"),
        "malformed_next_operator_action": malformed_report.get("next_operator_action"),
        "temp_files_only": True,
        **BOUNDARY_FLAGS,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise review send receipt dry run",
        f"valid: {str(report['valid']).lower()}",
        f"dry_run_doc: {report['dry_run_doc']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report['selected_capability']}",
        f"filled_receipt_ready: {str(report['filled_receipt_ready']).lower()}",
        f"malformed_receipt_rejected: {str(report['malformed_receipt_rejected']).lower()}",
        f"filled_next_operator_action: {report['filled_next_operator_action']}",
        f"malformed_next_operator_action: {report['malformed_next_operator_action']}",
        f"temp_files_only: {str(report['temp_files_only']).lower()}",
    ]
    lines.extend(f"{key}: {str(value).lower()}" for key, value in BOUNDARY_FLAGS.items())
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _filled_receipt_payload(template_payload: dict[str, Any]) -> dict[str, Any]:
    payload = cast(dict[str, Any], json.loads(json.dumps(template_payload)))
    payload["dirty"] = False
    payload["sent"] = True
    for receipt in payload.get("receipts", []):
        if not isinstance(receipt, dict):
            continue
        gap = str(receipt.get("gap", "UNKNOWN"))
        receipt["sent"] = True
        receipt["sent_at"] = "2026-06-30T00:00:00Z"
        receipt["channel"] = "manual-review"
        receipt["reviewer_label"] = f"fixture-reviewer-{gap.lower()}"
        receipt["thread_or_message_url"] = f"https://example.test/{gap.lower()}"
        receipt["message_id"] = ""
    return payload


def _malformed_receipt_payload(filled_payload: dict[str, Any]) -> dict[str, Any]:
    payload = cast(dict[str, Any], json.loads(json.dumps(filled_payload)))
    receipts = payload.get("receipts", [])
    if receipts and isinstance(receipts[0], dict):
        receipts[0]["thread_or_message_url"] = ""
        receipts[0]["message_id"] = ""
    return payload


def _validate_repo_wiring(repo_root: Path, failures: list[str]) -> None:
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    receipt_template_doc = _read(
        repo_root / "docs/codex/enterprise-review-send-receipt-template.md"
    )
    receipt_validation_doc = _read(
        repo_root / "docs/codex/enterprise-review-send-receipt-validation.md"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    checks = {
        "Make target": ("enterprise-review-send-receipt-dry-run:", makefile),
        "Release check": (
            "enterprise-review-send-receipt-dry-run",
            release_check_body + makefile,
        ),
        "Review candidate": (
            "$(MAKE) enterprise-review-send-receipt-dry-run",
            review_candidate_body,
        ),
        "README command": ("make enterprise-review-send-receipt-dry-run", readme),
        "Docs site": (DOC_REL, docs_site),
        "Review docs": (DOC_REL, "\n".join(review_docs.REVIEW_DOCS)),
        "Review index": (DOC_NAME, review_index),
        "Release guardrails": ("enterprise-review-send-receipt-dry-run", release_guardrails),
        "Receipt template pointer": (
            "enterprise-review-send-receipt-dry-run",
            receipt_template_doc,
        ),
        "Receipt validation pointer": (
            "enterprise-review-send-receipt-dry-run",
            receipt_validation_doc,
        ),
    }
    for label, (needle, haystack) in checks.items():
        if needle not in haystack:
            failures.append(f"{label} is missing {needle}")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
