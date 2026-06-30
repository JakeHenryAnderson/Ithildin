"""Copy the enterprise send receipt template to an operator-editable receipt."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (  # noqa: E402
    enterprise_review_send_receipt_template,
    enterprise_review_send_receipt_validate,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path(
    "var/review-runs/enterprise-review-send-receipts/"
    "enterprise-review-send-receipt-copy.json"
)
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


class EnterpriseReviewSendReceiptCopyError(RuntimeError):
    """Raised when the operator receipt copy cannot be prepared."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    if args.check:
        report = build_check_report(ROOT)
        _print_report(report, json_output=args.json_output)
        return 0 if report["valid"] else 1

    try:
        report = build_copy_report(ROOT, args.output, force=args.force)
    except EnterpriseReviewSendReceiptCopyError as exc:
        print(f"enterprise review send receipt copy failed: {exc}", file=sys.stderr)
        return 1
    _print_report(report, json_output=args.json_output)
    return 0 if report["valid"] else 1


def build_copy_report(repo_root: Path, output: Path, *, force: bool) -> dict[str, Any]:
    output_path = output if output.is_absolute() else repo_root / output
    existed_before = output_path.exists()
    if existed_before and not force:
        raise EnterpriseReviewSendReceiptCopyError(
            f"receipt copy already exists; use --force to overwrite: {output}"
        )

    template_dir = enterprise_review_send_receipt_template.build_template(
        repo_root, enterprise_review_send_receipt_template.DEFAULT_OUTPUT_DIR
    )
    template_path = template_dir / enterprise_review_send_receipt_template.JSON_NAME
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template_path, output_path)

    validation = enterprise_review_send_receipt_validate.build_report(
        repo_root, _repo_rel_path(repo_root, output_path)
    )
    failures: list[str] = []
    if validation.get("valid") is not True:
        failures.append("copied receipt template failed validation")
    if validation.get("ready_for_response_intake") is not False:
        failures.append("copied unsent receipt must not be response-intake ready")
    if validation.get("next_operator_action") != (
        "copy_template_fill_send_receipt_then_rerun_validation"
    ):
        failures.append("copied unsent receipt has unexpected next operator action")

    payload = _read_json(output_path)
    if payload.get("sent") is not False:
        failures.append("copied receipt must remain unsent until the operator edits it")
    if payload.get("tool_count") != 24:
        failures.append("copied receipt tool_count must remain 24")
    if payload.get("selected_capability") != "not selected":
        failures.append("copied receipt selected_capability must remain not selected")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output": _repo_rel_path(repo_root, output_path).as_posix(),
        "template": _repo_rel_path(repo_root, template_path).as_posix(),
        "ready_for_response_intake": validation.get("ready_for_response_intake"),
        "next_operator_action": validation.get("next_operator_action"),
        "overwrote_existing": existed_before and force,
        "tool_count": 24,
        **BOUNDARY_FLAGS,
    }


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="ithildin-send-receipt-copy-") as temp_dir:
        temp_output = Path(temp_dir) / "enterprise-review-send-receipt-copy.json"
        try:
            copy_report = build_copy_report(repo_root, temp_output, force=False)
        except EnterpriseReviewSendReceiptCopyError as exc:
            copy_report = {"valid": False, "failures": [str(exc)]}
            failures.append(str(exc))
        if copy_report.get("valid") is not True:
            failures.extend(
                f"copy report: {failure}"
                for failure in copy_report.get("failures", [])
            )

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    receipt_doc = _read(
        repo_root / "docs/codex/enterprise-review-send-receipt-template.md"
    )
    validation_doc = _read(
        repo_root / "docs/codex/enterprise-review-send-receipt-validation.md"
    )
    required = {
        "Make target": ("enterprise-review-send-receipt-copy:", makefile),
        "Check target": ("enterprise-review-send-receipt-copy-check:", makefile),
        "README command": ("make enterprise-review-send-receipt-copy", readme),
        "Template doc command": (
            "make enterprise-review-send-receipt-copy",
            receipt_doc,
        ),
        "Validation doc pointer": (
            "enterprise-review-send-receipt-copy",
            validation_doc,
        ),
    }
    for label, (needle, haystack) in required.items():
        if needle not in haystack:
            failures.append(f"{label} is missing {needle}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "default_output": DEFAULT_OUTPUT.as_posix(),
        "copy_report_valid": copy_report.get("valid") is True,
        "tool_count": 24,
        **BOUNDARY_FLAGS,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise review send receipt copy",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report['tool_count']}",
    ]
    if "output" in report:
        lines.append(f"output: {report['output']}")
    if "default_output" in report:
        lines.append(f"default_output: {report['default_output']}")
    if "ready_for_response_intake" in report:
        lines.append(
            "ready_for_response_intake: "
            f"{str(report['ready_for_response_intake']).lower()}"
        )
    if "next_operator_action" in report:
        lines.append(f"next_operator_action: {report['next_operator_action']}")
    lines.extend(f"{key}: {str(value).lower()}" for key, value in BOUNDARY_FLAGS.items())
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _print_report(report: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _repo_rel_path(repo_root: Path, path: Path) -> Path:
    resolved = path.resolve()
    try:
        return resolved.relative_to(repo_root.resolve())
    except ValueError:
        return resolved


if __name__ == "__main__":
    raise SystemExit(main())
