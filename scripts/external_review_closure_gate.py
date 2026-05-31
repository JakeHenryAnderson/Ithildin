"""Report whether external source-review closure is complete and honestly represented."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CLOSURE_MATRIX = ROOT / "docs/codex/source-review-closure-matrix.md"
FALSE_CLOSURE_PHRASES = [
    "external source review is complete",
    "external review complete",
    "source review closed",
    "capability expansion allowed",
    "ready for new tool powers",
]
FALSE_CLOSURE_DOCS = [
    ROOT / "README.md",
    ROOT / "docs/codex/v0.5-roadmap-from-v0.4-review.md",
    ROOT / "docs/codex/v0.5-milestone-manifest.md",
    ROOT / "docs/codex/v0.4-capability-decision-seed.md",
    ROOT / "docs/codex/v0.3-boundary-decision.md",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--require-closed",
        action="store_true",
        help="exit nonzero unless external closure is complete",
    )
    args = parser.parse_args()

    report = build_report(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    if report["hard_failures"]:
        return 1
    if args.require_closed and not report["external_closure_complete"]:
        return 1
    return 0


def build_report(repo_root: Path) -> dict[str, Any]:
    matrix_path = repo_root / CLOSURE_MATRIX.relative_to(ROOT)
    rows = _parse_v3_rows(matrix_path)
    hard_failures: list[str] = []

    if not rows:
        hard_failures.append("source-review closure matrix has no v3 rows")

    pending_rows = [
        row["Area"]
        for row in rows
        if "pending external review" in row["External status"].lower()
        or row["Closure state"] == "external_pending"
    ]
    closed_rows = [
        row["Area"]
        for row in rows
        if row["Closure state"] in {"external_reviewed", "closed_local_preview"}
    ]
    open_critical_high = [
        row["Area"]
        for row in rows
        if row["Highest open severity"].lower() in {"critical", "high"}
    ]

    for row in rows:
        external_status = row["External status"].lower()
        closure_state = row["Closure state"]
        if "pending external review" in external_status and closure_state in {
            "external_reviewed",
            "closed_local_preview",
        }:
            hard_failures.append(
                f"{row['Area']} claims closure state {closure_state} "
                "while external review is pending"
            )
        if closure_state == "closed_local_preview" and row["Fixed commit"] == "pending":
            hard_failures.append(f"{row['Area']} is closed without fixed commit evidence")

    false_claims = _false_closure_claims(repo_root)
    if false_claims:
        hard_failures.append("docs contain false external-closure or capability-expansion claims")

    blockers = []
    if pending_rows:
        blockers.append(f"external review rows still pending: {len(pending_rows)}")
    if open_critical_high:
        blockers.append(f"open critical/high rows: {', '.join(open_critical_high)}")

    return {
        "schema_version": "1",
        "valid": not hard_failures,
        "hard_failures": hard_failures,
        "external_closure_complete": not pending_rows and not open_critical_high,
        "blockers": blockers,
        "row_count": len(rows),
        "pending_external_review_rows": pending_rows,
        "externally_closed_rows": closed_rows,
        "false_closure_claims": false_claims,
    }


def _parse_v3_rows(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    try:
        v3 = text.split("## v3 Closure State", maxsplit=1)[1]
    except IndexError:
        return []

    rows: list[dict[str, str]] = []
    headers: list[str] = []
    for line in v3.splitlines():
        if not line.startswith("|"):
            if rows and line.startswith("## "):
                break
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not headers:
            headers = cells
            continue
        if cells and set(cells[0]) == {"-"}:
            continue
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells, strict=True)))
    return rows


def _false_closure_claims(repo_root: Path) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for path in FALSE_CLOSURE_DOCS:
        real_path = repo_root / path.relative_to(ROOT)
        if not real_path.exists():
            continue
        for line_number, line in enumerate(
            real_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            normalized = line.lower()
            for phrase in FALSE_CLOSURE_PHRASES:
                if phrase in normalized and "not " not in normalized:
                    claims.append(
                        {
                            "path": real_path.relative_to(repo_root).as_posix(),
                            "line": line_number,
                            "phrase": phrase,
                            "text": line.strip(),
                        }
                    )
    return claims


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin external-review closure gate",
        f"valid: {str(report['valid']).lower()}",
        f"external_closure_complete: {str(report['external_closure_complete']).lower()}",
        f"row_count: {report['row_count']}",
        f"pending_external_review_rows: {len(report['pending_external_review_rows'])}",
        f"externally_closed_rows: {len(report['externally_closed_rows'])}",
    ]
    if report["blockers"]:
        lines.append("blockers:")
        lines.extend(f"- {blocker}" for blocker in report["blockers"])
    if report["hard_failures"]:
        lines.append("hard_failures:")
        lines.extend(f"- {failure}" for failure in report["hard_failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
