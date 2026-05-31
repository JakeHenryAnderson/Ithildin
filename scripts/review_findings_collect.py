"""Collect structured reviewer findings into v0.4 summary artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import reviewer_findings

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FINDINGS_DIR = ROOT / "docs/codex/findings"
DEFAULT_DOC_OUTPUT = ROOT / "docs/codex/v0.3-review-findings-summary.md"
DEFAULT_JSON_OUTPUT = ROOT / "var/review-runs/findings-summary.json"
SEVERITIES = ("critical", "high", "medium", "low", "informational")


class ReviewFindingSummaryError(RuntimeError):
    """Raised when finding summary generation fails."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--findings-dir", default=str(DEFAULT_FINDINGS_DIR))
    parser.add_argument("--output-doc", default=str(DEFAULT_DOC_OUTPUT))
    parser.add_argument("--output-json", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--check", action="store_true", help="validate without rewriting outputs")
    args = parser.parse_args()

    try:
        summary = collect_findings_summary(Path(args.findings_dir), ROOT)
        if not args.check:
            write_summary_outputs(
                summary,
                output_doc=Path(args.output_doc),
                output_json=Path(args.output_json),
            )
    except (reviewer_findings.FindingValidationError, ReviewFindingSummaryError) as exc:
        print(f"review findings summary failed: {exc}", file=sys.stderr)
        return 1

    print(
        "Review findings summary passed: "
        f"{summary['total']} finding(s), "
        f"open critical/high={summary['open_critical_high']}"
    )
    return 0


def collect_findings_summary(findings_dir: Path, repo_root: Path) -> dict[str, Any]:
    records = reviewer_findings.validate_findings(findings_dir=findings_dir, repo_root=repo_root)
    findings: list[dict[str, str]] = []
    by_severity: Counter[str] = Counter()
    by_disposition: Counter[str] = Counter()
    by_blocking_status: Counter[str] = Counter()
    by_area: defaultdict[str, int] = defaultdict(int)
    open_critical_high = 0

    for record in records:
        fields = record.fields
        severity = fields["Severity"]
        disposition = fields["Disposition"]
        blocking_status = fields["Blocking status"]
        area = fields["Area"]
        if severity in {"critical", "high"} and disposition == "open":
            open_critical_high += 1
        by_severity[severity] += 1
        by_disposition[disposition] += 1
        by_blocking_status[blocking_status] += 1
        by_area[area] += 1
        findings.append(
            {
                "finding_id": fields["Finding ID"],
                "severity": severity,
                "area": area,
                "blocking_status": blocking_status,
                "disposition": disposition,
                "path": record.summary(repo_root)["path"],
            }
        )

    if open_critical_high:
        raise ReviewFindingSummaryError("open critical/high findings must be resolved first")

    return {
        "schema_version": "1",
        "total": len(findings),
        "open_critical_high": open_critical_high,
        "by_severity": {severity: by_severity[severity] for severity in SEVERITIES},
        "by_disposition": dict(sorted(by_disposition.items())),
        "by_blocking_status": dict(sorted(by_blocking_status.items())),
        "by_area": dict(sorted(by_area.items())),
        "findings": findings,
    }


def write_summary_outputs(
    summary: dict[str, Any],
    *,
    output_doc: Path,
    output_json: Path,
) -> None:
    output_doc.parent.mkdir(parents=True, exist_ok=True)
    output_doc.write_text(_summary_markdown(summary), encoding="utf-8")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# v0.3 Review Findings Summary",
        "",
        "This summary is generated from structured finding records under `docs/codex/findings/`.",
        "It is v0.4 planning input and does not close external/source review by itself.",
        "",
        "## Totals",
        "",
        f"- Total findings: {summary['total']}",
        f"- Open critical/high findings: {summary['open_critical_high']}",
        "",
        "## By Severity",
        "",
    ]
    for severity, count in summary["by_severity"].items():
        lines.append(f"- {severity}: {count}")
    lines.extend(["", "## Findings", ""])
    if not summary["findings"]:
        lines.append("No structured findings are currently recorded.")
    else:
        for finding in summary["findings"]:
            lines.append(
                "- "
                f"{finding['finding_id']} "
                f"({finding['severity']}, {finding['blocking_status']}, "
                f"{finding['disposition']}): {finding['area']} "
                f"[{finding['path']}]"
            )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
