"""Validate an enterprise review send receipt JSON without recording review."""

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
DOC_REL = "docs/codex/enterprise-review-send-receipt-validation.md"
DOC_NAME = "enterprise-review-send-receipt-validation.md"
DEFAULT_RECEIPT = Path(
    "var/review-packets/v3/enterprise-review-send-receipt-template/"
    "enterprise-review-send-receipt-template.json"
)
EXPECTED_GAPS = {"ERG-003", "ERG-002"}
EXPECTED_RAW_RESPONSE_PATHS = {
    "ERG-003": "var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-003.md",
    "ERG-002": "var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-002.md",
}
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
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    report = build_report(ROOT, args.receipt)
    if args.json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path, receipt_path: Path) -> dict[str, Any]:
    failures: list[str] = []
    resolved_receipt_path = (
        receipt_path if receipt_path.is_absolute() else repo_root / receipt_path
    )
    payload = _load_payload(resolved_receipt_path)
    if payload is None:
        failures.append(f"receipt JSON does not exist or cannot be parsed: {receipt_path}")
        payload = {}

    _validate_receipt_payload(payload, failures)
    _validate_repo_wiring(repo_root, failures)

    receipts = payload.get("receipts", [])
    sent_receipts = [
        receipt for receipt in receipts if isinstance(receipt, dict) and receipt.get("sent") is True
    ]
    receipt_gaps = {
        receipt.get("gap") for receipt in receipts if isinstance(receipt, dict)
    }
    all_sent = bool(receipts) and len(sent_receipts) == len(receipts)
    filled = _operator_fields_filled(payload, receipts)

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "receipt_validation_doc": DOC_REL,
        "receipt_path": receipt_path.as_posix(),
        "tool_count": 24,
        "expected_gaps": sorted(EXPECTED_GAPS),
        "receipt_gaps": sorted(str(gap) for gap in receipt_gaps if gap),
        "sent": payload.get("sent") is True,
        "all_receipts_sent": all_sent,
        "operator_fields_filled": filled,
        "ready_for_response_intake": bool(
            not failures and payload.get("sent") is True and all_sent and filled
        ),
        **BOUNDARY_FLAGS,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise review send receipt validation",
        f"valid: {str(report['valid']).lower()}",
        f"receipt_validation_doc: {report['receipt_validation_doc']}",
        f"receipt_path: {report['receipt_path']}",
        f"tool_count: {report['tool_count']}",
        "expected_gaps: " + ", ".join(report["expected_gaps"]),
        "receipt_gaps: " + ", ".join(report["receipt_gaps"]),
        f"sent: {str(report['sent']).lower()}",
        f"all_receipts_sent: {str(report['all_receipts_sent']).lower()}",
        f"operator_fields_filled: {str(report['operator_fields_filled']).lower()}",
        f"ready_for_response_intake: {str(report['ready_for_response_intake']).lower()}",
    ]
    lines.extend(f"{key}: {str(value).lower()}" for key, value in BOUNDARY_FLAGS.items())
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _load_payload(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _validate_receipt_payload(payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("template_type") != "ithildin.enterprise_review_send_receipt_template":
        failures.append("receipt template_type is not recognized")
    if payload.get("tool_count") != 24:
        failures.append("receipt tool_count must be 24")
    if payload.get("selected_capability") != "not selected":
        failures.append("receipt selected_capability must be not selected")
    if not isinstance(payload.get("commit"), str) or not payload.get("commit"):
        failures.append("receipt commit is missing")
    if payload.get("dirty") is not False and payload.get("sent") is True:
        failures.append("sent receipt must be generated from a clean tree")

    blocked = payload.get("blocked_boundaries")
    if not isinstance(blocked, dict):
        failures.append("receipt blocked_boundaries must be an object")
        blocked = {}
    for key, expected in BOUNDARY_FLAGS.items():
        if blocked.get(key) is not expected:
            failures.append(f"receipt boundary flag drifted: {key}")

    receipts = payload.get("receipts")
    if not isinstance(receipts, list):
        failures.append("receipt rows must be a list")
        return
    receipt_by_gap = {
        receipt.get("gap"): receipt
        for receipt in receipts
        if isinstance(receipt, dict) and isinstance(receipt.get("gap"), str)
    }
    if set(receipt_by_gap) != EXPECTED_GAPS:
        failures.append("receipt rows must contain exactly ERG-003 and ERG-002")
    for gap, expected_path in EXPECTED_RAW_RESPONSE_PATHS.items():
        receipt = receipt_by_gap.get(gap)
        if receipt is None:
            continue
        if receipt.get("raw_response_path") != expected_path:
            failures.append(f"{gap} raw_response_path drifted")
        if not isinstance(receipt.get("finding_namespace"), str):
            failures.append(f"{gap} finding_namespace is missing")
        if not isinstance(receipt.get("prompt"), str) or not receipt.get("prompt"):
            failures.append(f"{gap} prompt is missing")
        if receipt.get("sent") is True:
            _validate_filled_receipt(gap, receipt, failures)


def _validate_filled_receipt(
    gap: str,
    receipt: dict[str, Any],
    failures: list[str],
) -> None:
    for key in ["sent_at", "channel", "reviewer_label"]:
        if not isinstance(receipt.get(key), str) or not receipt.get(key, "").strip():
            failures.append(f"{gap} sent receipt is missing {key}")
    thread_or_message = (
        isinstance(receipt.get("thread_or_message_url"), str)
        and bool(receipt.get("thread_or_message_url", "").strip())
    )
    message_id = (
        isinstance(receipt.get("message_id"), str)
        and bool(receipt.get("message_id", "").strip())
    )
    if not (thread_or_message or message_id):
        failures.append(f"{gap} sent receipt needs thread_or_message_url or message_id")


def _operator_fields_filled(payload: dict[str, Any], receipts: list[Any]) -> bool:
    if payload.get("sent") is not True:
        return False
    if not all(isinstance(receipt, dict) and receipt.get("sent") is True for receipt in receipts):
        return False
    for receipt in receipts:
        if not isinstance(receipt, dict):
            return False
        required = ["sent_at", "channel", "reviewer_label"]
        if any(
            not isinstance(receipt.get(key), str) or not receipt.get(key, "").strip()
            for key in required
        ):
            return False
        if not (
            isinstance(receipt.get("thread_or_message_url"), str)
            and receipt.get("thread_or_message_url", "").strip()
        ) and not (
            isinstance(receipt.get("message_id"), str) and receipt.get("message_id", "").strip()
        ):
            return False
    return True


def _validate_repo_wiring(repo_root: Path, failures: list[str]) -> None:
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    receipt_template_doc = _read(
        repo_root / "docs/codex/enterprise-review-send-receipt-template.md"
    )
    response_quickstart = _read(repo_root / "docs/codex/enterprise-response-intake-quickstart.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    release_check_wired = (
        "enterprise-review-send-receipt-validate" in release_check_body
        or "release-check: enterprise-review-send-receipt-validate" in makefile
    )
    checks = {
        "Make target": ("enterprise-review-send-receipt-validate:", makefile),
        "Review candidate": (
            "$(MAKE) enterprise-review-send-receipt-validate",
            review_candidate_body,
        ),
        "README command": ("make enterprise-review-send-receipt-validate", readme),
        "Docs site": (DOC_REL, docs_site),
        "Review docs": (DOC_REL, "\n".join(review_docs.REVIEW_DOCS)),
        "Review index": (DOC_NAME, review_index),
        "Release guardrails": ("enterprise-review-send-receipt-validate", release_guardrails),
        "Receipt template pointer": (
            "enterprise-review-send-receipt-validate",
            receipt_template_doc,
        ),
        "Response quickstart pointer": (
            "enterprise-review-send-receipt-validate",
            response_quickstart,
        ),
    }
    if not release_check_wired:
        failures.append("Release check is missing enterprise-review-send-receipt-validate")
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
