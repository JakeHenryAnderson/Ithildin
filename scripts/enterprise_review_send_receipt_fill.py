"""Fill the ignored enterprise send receipt after the human send step."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (  # noqa: E402
    enterprise_review_send_receipt_copy,
    enterprise_review_send_receipt_validate,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = enterprise_review_send_receipt_copy.DEFAULT_OUTPUT
BOUNDARY_FLAGS = enterprise_review_send_receipt_copy.BOUNDARY_FLAGS
LANES = ("ERG-003", "ERG-002")


class EnterpriseReviewSendReceiptFillError(RuntimeError):
    """Raised when the send receipt cannot be filled safely."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--sent-at", default="")
    parser.add_argument("--channel", default="")
    parser.add_argument("--reviewer-label", default="")
    parser.add_argument("--erg-003-thread-or-message-url", default="")
    parser.add_argument("--erg-002-thread-or-message-url", default="")
    parser.add_argument("--erg-003-message-id", default="")
    parser.add_argument("--erg-002-message-id", default="")
    parser.add_argument("--operator-notes", default="")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    if args.check:
        report = build_check_report(ROOT)
        _print_report(report, json_output=args.json_output)
        return 0 if report["valid"] else 1

    try:
        report = build_fill_report(
            ROOT,
            output=args.output,
            sent_at=args.sent_at,
            channel=args.channel,
            reviewer_label=args.reviewer_label,
            lane_links={
                "ERG-003": args.erg_003_thread_or_message_url,
                "ERG-002": args.erg_002_thread_or_message_url,
            },
            lane_message_ids={
                "ERG-003": args.erg_003_message_id,
                "ERG-002": args.erg_002_message_id,
            },
            operator_notes=args.operator_notes,
            force=args.force,
        )
    except EnterpriseReviewSendReceiptFillError as exc:
        print(f"enterprise review send receipt fill failed: {exc}", file=sys.stderr)
        return 1
    _print_report(report, json_output=args.json_output)
    return 0 if report["valid"] else 1


def build_fill_report(
    repo_root: Path,
    *,
    output: Path,
    sent_at: str,
    channel: str,
    reviewer_label: str,
    lane_links: dict[str, str],
    lane_message_ids: dict[str, str],
    operator_notes: str,
    force: bool,
) -> dict[str, Any]:
    failures = _input_failures(
        sent_at=sent_at,
        channel=channel,
        reviewer_label=reviewer_label,
        lane_links=lane_links,
        lane_message_ids=lane_message_ids,
    )
    if failures:
        raise EnterpriseReviewSendReceiptFillError("; ".join(failures))

    output_path = output if output.is_absolute() else repo_root / output
    if output_path.exists() and force:
        output_path.unlink()
    if not output_path.exists():
        enterprise_review_send_receipt_copy.build_copy_report(
            repo_root,
            output_path,
            force=False,
        )

    payload = _read_json(output_path)
    if payload.get("sent") is True and not force:
        raise EnterpriseReviewSendReceiptFillError(
            f"receipt already appears sent; use --force to overwrite: {output}"
        )
    _fill_payload(
        payload,
        sent_at=sent_at,
        channel=channel,
        reviewer_label=reviewer_label,
        lane_links=lane_links,
        lane_message_ids=lane_message_ids,
        operator_notes=operator_notes,
    )
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    validation = enterprise_review_send_receipt_validate.build_report(
        repo_root,
        _repo_rel_path(repo_root, output_path),
    )
    fill_failures = list(validation.get("failures", []))
    if validation.get("ready_for_response_intake") is not True:
        fill_failures.append("filled receipt is not ready for response intake")

    return {
        "schema_version": "1",
        "valid": not fill_failures,
        "failures": fill_failures,
        "output": _repo_rel_path(repo_root, output_path).as_posix(),
        "ready_for_response_intake": validation.get("ready_for_response_intake"),
        "next_operator_action": validation.get("next_operator_action"),
        "receipt_gaps": validation.get("receipt_gaps", []),
        "tool_count": 24,
        "records_send_receipt": True,
        **BOUNDARY_FLAGS,
    }


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="ithildin-send-receipt-fill-") as temp_dir:
        temp_output = Path(temp_dir) / "enterprise-review-send-receipt-copy.json"
        try:
            fixture_report = build_fill_report(
                repo_root,
                output=temp_output,
                sent_at="2026-06-30T00:00:00Z",
                channel="fixture-channel",
                reviewer_label="fixture-reviewer",
                lane_links={
                    "ERG-003": "https://example.test/erg-003",
                    "ERG-002": "https://example.test/erg-002",
                },
                lane_message_ids={"ERG-003": "", "ERG-002": ""},
                operator_notes="fixture only",
                force=True,
            )
        except EnterpriseReviewSendReceiptFillError as exc:
            fixture_report = {"valid": False, "failures": [str(exc)]}
            failures.append(str(exc))
        fixture_failures = set(fixture_report.get("failures", []))
        allowed_dirty_failures = {
            "sent receipt must be generated from a clean tree",
            "filled receipt is not ready for response intake",
        }
        if fixture_report.get("valid") is not True and not fixture_failures.issubset(
            allowed_dirty_failures
        ):
            failures.extend(f"fixture fill: {failure}" for failure in fixture_failures)

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    template_doc = _read(repo_root / "docs/codex/enterprise-review-send-receipt-template.md")
    validation_doc = _read(repo_root / "docs/codex/enterprise-review-send-receipt-validation.md")
    required = {
        "Make target": ("enterprise-review-send-receipt-fill:", makefile),
        "Check target": ("enterprise-review-send-receipt-fill-check:", makefile),
        "README command": ("make enterprise-review-send-receipt-fill", readme),
        "Template doc command": ("make enterprise-review-send-receipt-fill", template_doc),
        "Validation doc command": ("make enterprise-review-send-receipt-fill", validation_doc),
    }
    for label, (needle, haystack) in required.items():
        if needle not in haystack:
            failures.append(f"{label} is missing {needle}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "default_output": DEFAULT_OUTPUT.as_posix(),
        "fixture_report_valid": fixture_report.get("valid") is True,
        "fixture_failures": sorted(fixture_failures),
        "tool_count": 24,
        "records_send_receipt": False,
        **BOUNDARY_FLAGS,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise review send receipt fill",
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
    if "fixture_report_valid" in report:
        lines.append(f"fixture_report_valid: {str(report['fixture_report_valid']).lower()}")
    lines.append(f"records_send_receipt: {str(report['records_send_receipt']).lower()}")
    lines.extend(f"{key}: {str(value).lower()}" for key, value in BOUNDARY_FLAGS.items())
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _fill_payload(
    payload: dict[str, Any],
    *,
    sent_at: str,
    channel: str,
    reviewer_label: str,
    lane_links: dict[str, str],
    lane_message_ids: dict[str, str],
    operator_notes: str,
) -> None:
    payload["sent"] = True
    operator_fill = payload.setdefault("operator_fill_in", {})
    if isinstance(operator_fill, dict):
        operator_fill.update(
            {
                "sent_at": sent_at,
                "channel": channel,
                "reviewer_label": reviewer_label,
                "thread_or_message_url": ", ".join(
                    link for link in lane_links.values() if link.strip()
                ),
                "operator_notes": operator_notes,
            }
        )
    for receipt in payload.get("receipts", []):
        if not isinstance(receipt, dict):
            continue
        gap = receipt.get("gap")
        if gap not in LANES:
            continue
        receipt.update(
            {
                "sent": True,
                "sent_at": sent_at,
                "channel": channel,
                "reviewer_label": reviewer_label,
                "thread_or_message_url": lane_links.get(str(gap), ""),
                "message_id": lane_message_ids.get(str(gap), ""),
            }
        )


def _input_failures(
    *,
    sent_at: str,
    channel: str,
    reviewer_label: str,
    lane_links: dict[str, str],
    lane_message_ids: dict[str, str],
) -> list[str]:
    failures: list[str] = []
    for label, value in {
        "sent_at": sent_at,
        "channel": channel,
        "reviewer_label": reviewer_label,
    }.items():
        if not value.strip():
            failures.append(f"{label} is required")
    for gap in LANES:
        if not lane_links.get(gap, "").strip() and not lane_message_ids.get(gap, "").strip():
            failures.append(f"{gap} requires thread/message URL or message ID")
    return failures


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EnterpriseReviewSendReceiptFillError(f"receipt copy missing: {path}") from exc
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


def _print_report(report: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))


if __name__ == "__main__":
    raise SystemExit(main())
