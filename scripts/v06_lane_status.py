"""Generate the v0.6 lane-status board from closure matrix and findings."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import reviewer_findings

ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "docs/codex/source-review-closure-matrix.md"
FINDINGS_DIR = ROOT / "docs/codex/findings"
DEFAULT_DOC_OUTPUT = ROOT / "docs/codex/v0.6-lane-status-board.md"
DEFAULT_JSON_OUTPUT = ROOT / "docs/codex/v0.6-lane-status-board.json"


@dataclass(frozen=True)
class Lane:
    slug: str
    title: str
    matrix_areas: tuple[str, ...]
    finding_prefixes: tuple[str, ...]
    next_external_packet: str


LANES: tuple[Lane, ...] = (
    Lane(
        slug="patch-apply",
        title="Patch Apply",
        matrix_areas=("Patch apply",),
        finding_prefixes=("EXT-PA-",),
        next_external_packet="minimal patch-apply recheck packet",
    ),
    Lane(
        slug="filesystem",
        title="Filesystem and Platform",
        matrix_areas=("Filesystem", "CI/platform claims", "Filesystem source review checklist"),
        finding_prefixes=("EXT-FS-",),
        next_external_packet="filesystem dispatch packet",
    ),
    Lane(
        slug="http-fetch",
        title="HTTP Fetch",
        matrix_areas=("HTTP fetch", "HTTP fetch source review checklist"),
        finding_prefixes=("EXT-HTTP-",),
        next_external_packet="`make http-fetch-source-review-bundle` output",
    ),
    Lane(
        slug="signed-evidence-audit",
        title="Signed Evidence and Audit",
        matrix_areas=("Signed evidence", "Audit integrity", "Manifest-lock verification"),
        finding_prefixes=("EXT-SE-",),
        next_external_packet="`make signed-evidence-source-review-bundle` output",
    ),
    Lane(
        slug="policy-registry",
        title="Policy and Registry",
        matrix_areas=(
            "Policy parity",
            "Registry fail-closed",
            "Policy parity source review checklist",
        ),
        finding_prefixes=("EXT-PR-",),
        next_external_packet="`make policy-registry-source-review-bundle` output",
    ),
    Lane(
        slug="mcp-ingress",
        title="MCP Ingress",
        matrix_areas=("MCP ingress", "MCP ingress source review checklist"),
        finding_prefixes=("EXT-MCP-",),
        next_external_packet="`make mcp-ingress-source-review-bundle` output",
    ),
    Lane(
        slug="review-console",
        title="Review Console",
        matrix_areas=("Review console evidence", "Local admin auth"),
        finding_prefixes=("EXT-UI-",),
        next_external_packet="review console dispatch packet",
    ),
    Lane(
        slug="release-automation",
        title="Release Automation",
        matrix_areas=("Release evidence", "v0.6 external review dispatch packets"),
        finding_prefixes=("EXT-REL-",),
        next_external_packet="release automation dispatch packet",
    ),
)


class LaneStatusError(RuntimeError):
    """Raised when the lane-status board cannot be built or is stale."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print JSON to stdout")
    parser.add_argument("--check", action="store_true", help="validate committed outputs")
    parser.add_argument("--output-doc", default=str(DEFAULT_DOC_OUTPUT))
    parser.add_argument("--output-json", default=str(DEFAULT_JSON_OUTPUT))
    args = parser.parse_args()

    try:
        board = build_lane_status(ROOT)
        if args.json:
            print(json.dumps(board, indent=2, sort_keys=True))
        elif args.check:
            check_outputs(
                board,
                output_doc=Path(args.output_doc),
                output_json=Path(args.output_json),
            )
            print("v0.6 lane status board check passed.")
        else:
            write_outputs(
                board,
                output_doc=Path(args.output_doc),
                output_json=Path(args.output_json),
            )
            print(f"Wrote v0.6 lane status board to {args.output_doc}")
    except (LaneStatusError, reviewer_findings.FindingValidationError) as exc:
        print(f"v0.6 lane status failed: {exc}", file=sys.stderr)
        return 1
    return 0


def build_lane_status(repo_root: Path) -> dict[str, Any]:
    matrix_rows = {
        row["Area"]: row
        for row in _parse_v3_rows(repo_root / MATRIX_PATH.relative_to(ROOT))
    }
    findings = reviewer_findings.validate_findings(
        findings_dir=repo_root / FINDINGS_DIR.relative_to(ROOT),
        repo_root=repo_root,
    )

    lanes: list[dict[str, Any]] = []
    for lane in LANES:
        rows = [matrix_rows[area] for area in lane.matrix_areas if area in matrix_rows]
        if not rows:
            raise LaneStatusError(f"closure matrix has no rows for lane: {lane.slug}")
        lane_findings = _findings_for_lane(findings, lane.finding_prefixes)
        external_received = any(
            "review received" in row["External status"].lower()
            or "source-level review received" in row["External status"].lower()
            or "recheck received" in row["External status"].lower()
            for row in rows
        )
        closure_states = sorted({row["Closure state"] for row in rows})
        open_critical_high = [
            record.finding_id
            for record in lane_findings
            if record.fields["Disposition"] == "open"
            and record.fields["Severity"] in {"critical", "high"}
        ]
        lanes.append(
            {
                "slug": lane.slug,
                "lane": lane.title,
                "matrix_areas": lane.matrix_areas,
                "external_review_received": external_received,
                "ext_findings_count": len(lane_findings),
                "critical_high_open_count": len(open_critical_high),
                "critical_high_open_findings": open_critical_high,
                "fixed_commits": _collect_values(rows, "Fixed commit"),
                "verification_commands": _collect_values(rows, "Verification command"),
                "reviewer_recheck_required": _reviewer_recheck_required(
                    external_received,
                    closure_states,
                    open_critical_high,
                ),
                "closure_state": _summarize_closure_states(closure_states),
                "next_action": _next_action(
                    lane,
                    external_received=external_received,
                    closure_states=closure_states,
                    open_critical_high=open_critical_high,
                ),
            }
        )

    return {
        "schema_version": "1",
        "track": "v0.6 external/source-review closure",
        "runtime_boundary": "v0.1 local-preview",
        "lanes": lanes,
        "summary": {
            "lane_count": len(lanes),
            "external_review_received": sum(
                1 for lane in lanes if lane["external_review_received"]
            ),
            "external_review_closed": sum(
                1
                for lane in lanes
                if lane["closure_state"]
                in {"external_reviewed", "closed_local_preview", "accepted_deferred"}
            ),
            "critical_high_open_count": sum(
                int(lane["critical_high_open_count"]) for lane in lanes
            ),
            "capability_expansion_allowed": False,
        },
        "does_not_prove": [
            "complete external/source-review closure",
            "capability expansion approval",
            "production readiness",
            "public/security-product positioning",
        ],
    }


def write_outputs(
    board: dict[str, Any],
    *,
    output_doc: Path,
    output_json: Path,
) -> None:
    output_doc.parent.mkdir(parents=True, exist_ok=True)
    output_doc.write_text(render_markdown(board), encoding="utf-8")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(board, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check_outputs(
    board: dict[str, Any],
    *,
    output_doc: Path,
    output_json: Path,
) -> None:
    expected_doc = render_markdown(board)
    expected_json = json.dumps(board, indent=2, sort_keys=True) + "\n"
    if not output_doc.exists():
        raise LaneStatusError(f"lane status doc is missing: {output_doc}")
    if output_doc.read_text(encoding="utf-8") != expected_doc:
        raise LaneStatusError("lane status doc is stale; run make v06-lane-status-write")
    if not output_json.exists():
        raise LaneStatusError(f"lane status JSON is missing: {output_json}")
    if output_json.read_text(encoding="utf-8") != expected_json:
        raise LaneStatusError("lane status JSON is stale; run make v06-lane-status-write")


def render_markdown(board: dict[str, Any]) -> str:
    lines = [
        "# v0.6 Lane Status Board",
        "",
        "This generated board summarizes source-review lane state for v0.6. It is a",
        "navigation aid only: it reports lane state but does not itself close review, approve",
        "capability expansion, or change the v0.1 local-preview runtime boundary.",
        "",
        "## Summary",
        "",
        f"- Lane count: {board['summary']['lane_count']}",
        f"- External review received: {board['summary']['external_review_received']}",
        f"- External review closed: {board['summary']['external_review_closed']}",
        f"- Critical/high open findings: {board['summary']['critical_high_open_count']}",
        "- Capability expansion allowed: false",
        "",
        "## Lanes",
        "",
        "| Lane | External review received | EXT findings | Critical/high open | "
        "Reviewer recheck required | Closure state | Next action |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for lane in board["lanes"]:
        lines.append(
            "| "
            f"{lane['lane']} | "
            f"{_yes_no(lane['external_review_received'])} | "
            f"{lane['ext_findings_count']} | "
            f"{lane['critical_high_open_count']} | "
            f"{_yes_no(lane['reviewer_recheck_required'])} | "
            f"{lane['closure_state']} | "
            f"{lane['next_action']} |"
        )
    lines.extend(
        [
            "",
            "## Verification Commands",
            "",
        ]
    )
    for lane in board["lanes"]:
        lines.append(f"### {lane['lane']}")
        lines.append("")
        lines.append(f"- Matrix areas: {', '.join(lane['matrix_areas'])}")
        lines.append(f"- Fixed commits: {', '.join(lane['fixed_commits']) or 'none'}")
        lines.append("- Verification commands:")
        for command in lane["verification_commands"]:
            lines.append(f"  - `{command}`")
        lines.append("")
    lines.extend(
        [
            "## What This Board Does Not Prove",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in board["does_not_prove"])
    lines.append("")
    return "\n".join(lines)


def _parse_v3_rows(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    try:
        v3 = text.split("## v3 Closure State", maxsplit=1)[1]
    except IndexError as exc:
        raise LaneStatusError("source-review closure matrix is missing v3 table") from exc

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
    if not rows:
        raise LaneStatusError("source-review closure matrix has no v3 rows")
    return rows


def _findings_for_lane(
    findings: list[reviewer_findings.FindingRecord],
    prefixes: tuple[str, ...],
) -> list[reviewer_findings.FindingRecord]:
    return [
        record
        for record in findings
        if any(record.finding_id.startswith(prefix) for prefix in prefixes)
    ]


def _collect_values(rows: list[dict[str, str]], column: str) -> list[str]:
    values: list[str] = []
    for row in rows:
        for value in re.split(r";\s*", row[column]):
            clean = value.strip().strip("`")
            if clean and clean != "pending" and clean not in values:
                values.append(clean)
    return values


def _reviewer_recheck_required(
    external_received: bool,
    closure_states: list[str],
    open_critical_high: list[str],
) -> bool:
    if open_critical_high:
        return True
    return external_received and any(state == "external_pending" for state in closure_states)


def _summarize_closure_states(states: list[str]) -> str:
    if len(states) == 1:
        return states[0]
    return ", ".join(states)


def _next_action(
    lane: Lane,
    *,
    external_received: bool,
    closure_states: list[str],
    open_critical_high: list[str],
) -> str:
    if open_critical_high:
        return "stop and fix or consult before lane progression"
    if external_received and any(state == "external_pending" for state in closure_states):
        return "run verification commands and send recheck before closure"
    if not external_received:
        return f"send {lane.next_external_packet} for source review"
    return "lane closed for local preview; continue remaining external/source-review lanes"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


if __name__ == "__main__":
    raise SystemExit(main())
