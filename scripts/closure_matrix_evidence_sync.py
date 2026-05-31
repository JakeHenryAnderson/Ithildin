"""Validate that v0.5 completed tasks are represented in the closure matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs/codex/v0.5-milestone-manifest.json"
MATRIX_PATH = ROOT / "docs/codex/source-review-closure-matrix.md"
VALID_CLOSURE_STATES = {
    "not_started",
    "internal_reviewed",
    "external_pending",
    "external_reviewed",
    "blocked",
    "fixed_pending_verify",
    "closed_local_preview",
    "accepted_deferred",
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
    return 1 if report["failures"] else 0


def build_report(repo_root: Path) -> dict[str, Any]:
    manifest = json.loads((repo_root / MANIFEST_PATH.relative_to(ROOT)).read_text(encoding="utf-8"))
    matrix_text = (repo_root / MATRIX_PATH.relative_to(ROOT)).read_text(encoding="utf-8")
    rows = _parse_v3_rows(matrix_text)

    failures: list[str] = []
    done_tasks = [
        milestone["id"]
        for milestone in manifest["milestones"]
        if milestone.get("status") == "done"
    ]
    missing_task_refs = [
        task_id for task_id in done_tasks if f"Task {int(task_id)}" not in matrix_text
    ]
    if missing_task_refs:
        failures.append(f"closure matrix missing done task references: {missing_task_refs}")

    row_failures: list[str] = []
    for row in rows:
        area = row.get("Area", "<unknown>")
        if not row.get("Verification command"):
            row_failures.append(f"{area} missing verification command")
        closure_state = row.get("Closure state", "")
        if closure_state not in VALID_CLOSURE_STATES:
            row_failures.append(f"{area} has invalid closure state {closure_state!r}")
        if (
            "pending external review" in row.get("External status", "").lower()
            and closure_state in {"external_reviewed", "closed_local_preview"}
        ):
            row_failures.append(f"{area} claims external closure while pending review")
    failures.extend(row_failures)

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "done_task_count": len(done_tasks),
        "done_task_ids": done_tasks,
        "matrix_v3_row_count": len(rows),
        "missing_done_task_refs": missing_task_refs,
        "row_failures": row_failures,
    }


def _parse_v3_rows(matrix_text: str) -> list[dict[str, str]]:
    try:
        v3 = matrix_text.split("## v3 Closure State", maxsplit=1)[1]
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
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells, strict=True)))
    return rows


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin closure matrix evidence sync",
        f"valid: {str(report['valid']).lower()}",
        f"done_task_count: {report['done_task_count']}",
        f"matrix_v3_row_count: {report['matrix_v3_row_count']}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
